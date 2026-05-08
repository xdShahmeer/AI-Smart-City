import heapq
import random


def findPath(graph, start, goal):
    # A* from start to goal using Manhattan distance as the heuristic.
    # Returns an ordered list of nodes [start, ..., goal], or [] if unreachable.

    def heuristic(node):
        return abs(node[0] - goal[0]) + abs(node[1] - goal[1])

    # openSet entries: (fScore, node)
    openSet = []
    heapq.heappush(openSet, (heuristic(start), start))

    cameFrom = {}
    gScore   = {start: 0.0}

    while openSet:
        _, current = heapq.heappop(openSet)

        if current == goal:
            return _reconstructPath(cameFrom, current)

        for neighbour in graph.getAccessibleNeighbours(current):
            edgeCost = graph.getWeightedCost(current, neighbour)
            if edgeCost == float('inf'):
                continue

            tentativeG = gScore[current] + edgeCost

            if tentativeG < gScore.get(neighbour, float('inf')):
                cameFrom[neighbour] = current
                gScore[neighbour]   = tentativeG
                fScore              = tentativeG + heuristic(neighbour)
                heapq.heappush(openSet, (fScore, neighbour))

    return []  # no path found


def _reconstructPath(cameFrom, current):
    # Walk back through cameFrom to build the path in order.
    path = [current]
    while current in cameFrom:
        current = cameFrom[current]
        path.append(current)
    path.reverse()
    return path


class RouterState:
    def __init__(self, graph):
        self.currentPos    = graph.primaryHospital
        self.civilians     = self._generateCivilians(graph)
        self.currentPath   = []   # remaining steps to the current civilian
        self.currentTarget = 0    # index of the civilian we are heading to
        self.skipped       = []   # civilians that could not be reached
        self.reached       = []   # civilians successfully reached

    def _generateCivilians(self, graph):
        # Pick up to 5 accessible nodes that are not the primary hospital.
        candidates = [
            n for n in graph.getAccessibleNodes()
            if n != graph.primaryHospital
        ]
        return random.sample(candidates, min(5, len(candidates)))


def initRouter(graph):
    # Build and return the initial router state for the medical team.
    return RouterState(graph)


def stepRouter(state, graph, eventLog):
    # Advance the medical team one cell toward the current civilian target.
    # Returns an event description string on notable events, None on a plain move.

    # All civilians handled
    if state.currentTarget >= len(state.civilians):
        return "Medical team has reached all civilians."

    goal = state.civilians[state.currentTarget]

    # No path yet for this civilian -- compute one now
    if not state.currentPath:
        path = findPath(graph, state.currentPos, goal)

        if not path:
            # Civilian is completely cut off
            state.skipped.append(goal)
            state.currentTarget += 1
            state.currentPath    = []
            return f"Civilian at {goal} is unreachable -- all paths flooded. Skipping."

        # Drop the start node; the team is already there
        state.currentPath = path[1:]

    # Check whether the next cell is still reachable before moving
    nextCell = state.currentPath[0]
    edgeBlocked  = graph.isEdgeBlocked(state.currentPos, nextCell)
    nodeBlocked  = not graph.nodes[nextCell]["accessible"]

    if edgeBlocked or nodeBlocked:
        # Something is now blocking the route -- reroute
        newPath = findPath(graph, state.currentPos, goal)

        if not newPath:
            state.skipped.append(goal)
            state.currentTarget += 1
            state.currentPath    = []
            return f"Civilian at {goal} is unreachable -- all paths flooded. Skipping."

        state.currentPath = newPath[1:]
        return f"Medical team rerouted. New path length: {len(newPath)} hops."

    # Move one step forward
    state.currentPos = state.currentPath.pop(0)

    if state.currentPos == goal:
        state.reached.append(goal)
        state.currentTarget += 1
        state.currentPath    = []
        return f"Medical team reached civilian at {goal}."

    return None  # normal move, nothing to log
