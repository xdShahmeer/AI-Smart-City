import heapq
import random

# minimum edge cost used by the heuristic to keep it admissible
from cityGraph import RESIDENTIAL_COST


# civilians at start
NUM_INITIAL_CIVILIANS = 5


# helpers

def manhattanDistance(nodeA, nodeB):
    # scaled by the cheapest edge cost so the heuristic never overestimates.
    # without this, 0.8-cost residential edges would break admissibility.
    return RESIDENTIAL_COST * (abs(nodeA[0] - nodeB[0]) + abs(nodeA[1] - nodeB[1]))


def reconstructPath(cameFrom, current):
    path = [current]
    while current in cameFrom:
        current = cameFrom[current]
        path.append(current)
    path.reverse()
    return path


# a star search

def findPath(graph, start, goal):
    # find a path with a star
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


# router state

class RouterState:
    def __init__(self, graph):
        self.currentPos    = graph.primaryHospital
        self.civilians     = self._generateCivilians(graph)
        self.currentPath   = []   # remaining cells
        self.currentTarget = 0    # current civilian index
        self.skipped       = []   # skipped civilians
        self.reached       = []   # reached civilians

    def _generateCivilians(self, graph):
        # pick civilians only on nodes reachable through the built road network.
        # using getAccessibleNodes() without a connectivity check would place
        # civilians on nodes the medical team can never reach.
        candidates = []
        for node in graph.getAccessibleNodes():
            if node == graph.primaryHospital:
                continue
            path = findPath(graph, graph.primaryHospital, node)
            if len(path) > 0:
                candidates.append(node)

        howMany = min(NUM_INITIAL_CIVILIANS, len(candidates))
        if howMany == 0:
            return []
        return random.sample(candidates, howMany)


def initRouter(graph):
    return RouterState(graph)


# step routing

def stepRouter(state, graph):
    if state.currentTarget >= len(state.civilians):
        return "Medical team has reached all civilians."

    goal = state.civilians[state.currentTarget]

    # build path if needed
    if not state.currentPath:
        path = findPath(graph, state.currentPos, goal)

        if not path:
            state.skipped.append(goal)
            state.currentTarget += 1
            state.currentPath    = []
            return f"Civilian at {goal} is unreachable -- all paths flooded. Skipping."

        # drop the start cell
        state.currentPath = path[1:]

    # check next cell
    nextCell    = state.currentPath[0]
    edgeBlocked = graph.isEdgeBlocked(state.currentPos, nextCell)
    nodeBlocked = not graph.nodes[nextCell]["accessible"]

    if edgeBlocked or nodeBlocked:
        # reroute from here
        newPath = findPath(graph, state.currentPos, goal)

        if not newPath:
            state.skipped.append(goal)
            state.currentTarget += 1
            state.currentPath    = []
            return f"Civilian at {goal} is unreachable -- all paths flooded. Skipping."

        state.currentPath = newPath[1:]
        return f"Medical team rerouted. New path length: {len(newPath)} hops."

    # move one step
    state.currentPos = state.currentPath.pop(0)

    if state.currentPos == goal:
        state.reached.append(goal)
        state.currentTarget += 1
        state.currentPath    = []
        return f"Medical team reached civilian at {goal}."

    return None
