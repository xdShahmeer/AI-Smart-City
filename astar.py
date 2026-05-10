import heapq
import random


# Number of civilians spawned at the start of the simulation. The user can
# add more later through the Emergency tool.
NUM_INITIAL_CIVILIANS = 5


# ── Helpers ───────────────────────────────────────────────────────────────────

def manhattanDistance(nodeA, nodeB):
    # Manhattan distance is the admissible heuristic on a 4-direction grid:
    # the absolute row + column difference is the minimum number of steps.
    return abs(nodeA[0] - nodeB[0]) + abs(nodeA[1] - nodeB[1])


def reconstructPath(cameFrom, current):
    # Walk back through the cameFrom map to build the full path in order.
    path = [current]
    while current in cameFrom:
        current = cameFrom[current]
        path.append(current)
    path.reverse()
    return path


# ── A* search with weighted edges ─────────────────────────────────────────────

def findPath(graph, start, goal):
    # A* from start to goal using Manhattan distance as the heuristic.
    # Returns the ordered list [start, ..., goal], or [] if unreachable.

    # Open set entries: (fScore, node)
    openSet = []
    heapq.heappush(openSet, (manhattanDistance(start, goal), start))

    cameFrom = {}
    gScore   = {start: 0.0}

    while openSet:
        currentF, current = heapq.heappop(openSet)

        if current == goal:
            return reconstructPath(cameFrom, current)

        for neighbour in graph.getAccessibleNeighbours(current, builtOnly=True):
            edgeCost = graph.getWeightedCost(current, neighbour)
            if edgeCost == float('inf'):
                continue

            nextCost = gScore[current] + edgeCost

            knownBest = gScore.get(neighbour, float('inf'))
            if nextCost < knownBest:
                cameFrom[neighbour] = current
                gScore[neighbour]   = nextCost
                fScore              = nextCost + manhattanDistance(neighbour, goal)
                heapq.heappush(openSet, (fScore, neighbour))

    return []


# ── Router state for the medical team ─────────────────────────────────────────

class RouterState:
    def __init__(self, graph):
        self.currentPos    = graph.primaryHospital
        self.civilians     = self._generateCivilians(graph)
        self.currentPath   = []   # remaining cells on the way to the current civilian
        self.currentTarget = 0    # index of the civilian we are heading to
        self.skipped       = []   # civilians the team could not reach
        self.reached       = []   # civilians the team has reached

    def _generateCivilians(self, graph):
        # Pick up to NUM_INITIAL_CIVILIANS accessible nodes that are not the
        # primary hospital itself.
        candidates = []
        for node in graph.getAccessibleNodes():
            if node != graph.primaryHospital:
                candidates.append(node)

        howMany = min(NUM_INITIAL_CIVILIANS, len(candidates))
        return random.sample(candidates, howMany)


def initRouter(graph):
    return RouterState(graph)


# ── Per-step routing logic ────────────────────────────────────────────────────

def stepRouter(state, graph):
    # Advance the medical team one cell toward the current civilian target.
    # Returns an event description on notable events, None on a plain move.

    if state.currentTarget >= len(state.civilians):
        return "Medical team has reached all civilians."

    goal = state.civilians[state.currentTarget]

    # Compute a path if we don't have one yet for this civilian
    if not state.currentPath:
        path = findPath(graph, state.currentPos, goal)

        if not path:
            state.skipped.append(goal)
            state.currentTarget += 1
            state.currentPath    = []
            return f"Civilian at {goal} is unreachable -- all paths flooded. Skipping."

        # Drop the start node; the team is already there
        state.currentPath = path[1:]

    # Make sure the next cell is still reachable before we step into it
    nextCell    = state.currentPath[0]
    edgeBlocked = graph.isEdgeBlocked(state.currentPos, nextCell)
    nodeBlocked = not graph.nodes[nextCell]["accessible"]

    if edgeBlocked or nodeBlocked:
        # The route went bad mid-journey -- recompute from the current position
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

    return None
