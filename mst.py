import heapq
import math

from cityGraph import edgeKey


# union find helpers

def findRoot(parent, node):
    # path compression keeps the root direct
    if parent[node] != node:
        parent[node] = findRoot(parent, parent[node])
    return parent[node]


def unionByRank(parent, rank, nodeA, nodeB):
    rootA = findRoot(parent, nodeA)
    rootB = findRoot(parent, nodeB)

    if rootA == rootB:
        return False

    # keep the bigger tree as root
    if rank[rootA] < rank[rootB]:
        rootA, rootB = rootB, rootA

    parent[rootB] = rootA
    if rank[rootA] == rank[rootB]:
        rank[rootA] += 1
    return True


# a star search

def manhattanDistance(nodeA, nodeB):
    return abs(nodeA[0] - nodeB[0]) + abs(nodeA[1] - nodeB[1])


def astarPath(graph, start, goal, builtOnly=True):
    # return nodes from start to goal
    # skip blocked edges
    # built only uses built edges
    if start == goal:
        return [start]

    # queue items fscore gscore node path
    openSet = []
    heapq.heappush(openSet, (manhattanDistance(start, goal), 0, start, [start]))

    # best g score per node
    bestG = {}

    while openSet:
        fScore, gScore, current, path = heapq.heappop(openSet)

        if current == goal:
            return path

        # skip if a better route was seen
        if current in bestG and bestG[current] <= gScore:
            continue
        bestG[current] = gScore

        for neighbour in graph.getNeighbours(current, builtOnly=builtOnly):
            if graph.isEdgeBlocked(current, neighbour):
                continue
            edgeCost = graph.getEdgeCost(current, neighbour)
            newG     = gScore + edgeCost

            knownBest = bestG.get(neighbour, float('inf'))
            if newG < knownBest:
                newF        = newG + manhattanDistance(neighbour, goal)
                newPath     = path + [neighbour]
                heapq.heappush(openSet, (newF, newG, neighbour, newPath))

    return []


# primary node selection

def pickCentreNode(nodeList, rows, cols):
    # pick the node nearest to the grid centre
    centreRow = rows / 2.0
    centreCol = cols / 2.0

    bestNode     = None
    bestDistance = float('inf')
    bestRow      = None
    bestCol      = None

    for node in nodeList:
        nodeRow, nodeCol = node
        distance = math.sqrt(
            (nodeRow - centreRow) ** 2 + (nodeCol - centreCol) ** 2
        )

        # pick closer nodes first
        replace = False
        if distance < bestDistance:
            replace = True
        elif distance == bestDistance:
            if nodeRow < bestRow:
                replace = True
            elif nodeRow == bestRow and nodeCol < bestCol:
                replace = True

        if replace:
            bestNode     = node
            bestDistance = distance
            bestRow      = nodeRow
            bestCol      = nodeCol

    return bestNode


# kruskals mst

def buildMST(graph):
    allNodes = graph.getAllNodes()
    allEdges = graph.getAllEdges()

    # sort edges by cost
    sortedEdges = list(allEdges)
    sortByEdgeCost(sortedEdges, graph)

    parent = {}
    rank   = {}
    for node in allNodes:
        parent[node] = node
        rank[node]   = 0

    mstEdges       = []
    targetEdgeCount = len(allNodes) - 1

    for edge in sortedEdges:
        nodeA, nodeB = edge
        if unionByRank(parent, rank, nodeA, nodeB):
            mstEdges.append(edge)
        if len(mstEdges) == targetEdgeCount:
            break

    return mstEdges


def sortByEdgeCost(edgeList, graph):
    # use a small named key helper
    def keyFor(edge):
        return graph.edges[edge]["cost"]
    edgeList.sort(key=keyFor)


# public entry point

def buildRoadNetwork(graph):
    # pick main nodes then build mst and routes
    # return routea routeb and events
    events = []

    # pick main hospital and depot
    hospitals = graph.getNodesByType("Hospital")
    depots    = graph.getNodesByType("AmbulanceDepot")

    if len(hospitals) > 0:
        graph.primaryHospital = pickCentreNode(hospitals, graph.rows, graph.cols)
    else:
        graph.primaryHospital = None

    if len(depots) > 0:
        graph.primaryDepot = pickCentreNode(depots, graph.rows, graph.cols)
    else:
        graph.primaryDepot = None

    if graph.primaryHospital is None or graph.primaryDepot is None:
        events.append("[MST] Missing hospital or depot -- skipping emergency route construction.")
        return ([], [], events)

    events.append(f"[MST] Primary Hospital: {graph.primaryHospital}")
    events.append(f"[MST] Primary Depot:    {graph.primaryDepot}")

    # build the mst and mark built edges
    mstEdges = buildMST(graph)
    graph.setBuiltEdges(mstEdges)
    events.append(
        f"[MST] Kruskal's MST built: {len(mstEdges)} edges spanning "
        f"{len(graph.getAllNodes())} nodes."
    )

    # find route a on built edges
    pathA = astarPath(graph, graph.primaryHospital, graph.primaryDepot)
    if len(pathA) == 0:
        events.append("[MST] A* could not find Route A.")
        return ([], [], events)

    routeA = []
    for i in range(len(pathA) - 1):
        routeA.append(edgeKey(pathA[i], pathA[i + 1]))
    events.append(f"[MST] Route A: {len(routeA)} edges, path length {len(pathA)} nodes.")

    # add route a to the built set
    allBuilt = list(mstEdges)
    for edge in routeA:
        if edge not in allBuilt:
            allBuilt.append(edge)
    graph.setBuiltEdges(allBuilt)

    # block route a for route b search
    for nodeA, nodeB in routeA:
        graph.floodEdge(nodeA, nodeB)

    # find route b on all edges
    pathB  = astarPath(graph, graph.primaryHospital, graph.primaryDepot, builtOnly=False)
    routeB = []
    if len(pathB) > 0:
        for i in range(len(pathB) - 1):
            routeB.append(edgeKey(pathB[i], pathB[i + 1]))
        events.append(
            f"[MST] Route B: {len(routeB)} edges, path length {len(pathB)} nodes."
        )
    else:
        events.append("[MST] No independent Route B found -- city topology may be too constrained.")

    # restore route a edges
    for nodeA, nodeB in routeA:
        graph.unfloodEdge(nodeA, nodeB)

    # final built set
    for edge in routeB:
        if edge not in allBuilt:
            allBuilt.append(edge)
    graph.setBuiltEdges(allBuilt)

    return (routeA, routeB, events)
