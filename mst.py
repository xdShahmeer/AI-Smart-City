import heapq
import math

from cityGraph import edgeKey


# ── Union-Find helpers for Kruskal's algorithm ────────────────────────────────

def findRoot(parent, node):
    # Path compression: every visited node points directly to the root.
    if parent[node] != node:
        parent[node] = findRoot(parent, parent[node])
    return parent[node]


def unionByRank(parent, rank, nodeA, nodeB):
    # Union by rank: attach the smaller tree under the larger root.
    rootA = findRoot(parent, nodeA)
    rootB = findRoot(parent, nodeB)

    if rootA == rootB:
        return False   # already in the same component

    # Make sure rootA is the larger of the two
    if rank[rootA] < rank[rootB]:
        rootA, rootB = rootB, rootA

    parent[rootB] = rootA
    if rank[rootA] == rank[rootB]:
        rank[rootA] += 1
    return True


# ── A* search (base costs only, no crime multiplier) ──────────────────────────

def manhattanDistance(nodeA, nodeB):
    return abs(nodeA[0] - nodeB[0]) + abs(nodeA[1] - nodeB[1])


def astarPath(graph, start, goal, builtOnly=True):
    # Returns the ordered list of nodes from start to goal, or [] if no path.
    # Respects blocked edges so a temporarily blocked Route A is avoided.
    # When builtOnly is True, only edges marked as built are traversable.
    # Route B passes builtOnly=False because it adds new roads beyond the MST.
    if start == goal:
        return [start]

    # Priority queue entries: (fScore, gScore, node, pathSoFar)
    openSet = []
    heapq.heappush(openSet, (manhattanDistance(start, goal), 0, start, [start]))

    # Best gScore seen for each node
    bestG = {}

    while openSet:
        fScore, gScore, current, path = heapq.heappop(openSet)

        if current == goal:
            return path

        # Skip if a cheaper route to this node was already processed
        if current in bestG and bestG[current] <= gScore:
            continue
        bestG[current] = gScore

        for neighbour in graph.getNeighbours(current):
            if graph.isEdgeBlocked(current, neighbour):
                continue
            # Only traverse built edges when requested (Route A uses this;
            # Route B searches the full grid edge set to find an independent path).
            if builtOnly:
                key = edgeKey(current, neighbour)
                if not graph.edges[key].get("built", False):
                    continue
            edgeCost = graph.getEdgeCost(current, neighbour)
            newG     = gScore + edgeCost

            knownBest = bestG.get(neighbour, float('inf'))
            if newG < knownBest:
                newF        = newG + manhattanDistance(neighbour, goal)
                newPath     = path + [neighbour]
                heapq.heappush(openSet, (newF, newG, neighbour, newPath))

    return []


# ── Primary node selection ────────────────────────────────────────────────────

def pickCentreNode(nodeList, rows, cols):
    # Return the node closest to the geometric centre of the grid. Ties are
    # broken by lower row first, then lower col, so the choice is deterministic.
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

        # Pick this node if it is closer, OR equally close but rows/cols smaller
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


# ── Kruskal's MST ─────────────────────────────────────────────────────────────

def buildMST(graph):
    # Returns the list of edge tuples (nodeA, nodeB) that form the MST.
    allNodes = graph.getAllNodes()
    allEdges = graph.getAllEdges()

    # Sort the edges by their cost (ascending). Using a plain helper instead
    # of `key=lambda e: graph.edges[e]["cost"]` keeps the intent explicit.
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
    # Insertion sort would be too slow for a 30x30 grid (~3600 edges), so we
    # build a key list and use the standard sort. Defining `keyFor` as a
    # named function avoids the lambda.
    def keyFor(edge):
        return graph.edges[edge]["cost"]
    edgeList.sort(key=keyFor)


# ── Public entry point ────────────────────────────────────────────────────────

def buildRoadNetwork(graph):
    # Designates Primary Hospital and Primary Depot, builds Kruskal's MST,
    # then adds two independent emergency routes via A*.
    #
    # Returns (routeA, routeB, events). Each route is a list of canonical
    # (nodeA, nodeB) edge tuples. `events` is a list of log strings the
    # caller forwards to the UI event log.
    events = []

    # Step 1: designate the Primary Hospital and Primary Depot
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

    # Step 2: build the MST and mark those edges as the base built road network.
    # The downstream A* route searches will only traverse built edges, so Route A
    # and Route B are guaranteed to stay on the constructed network.
    mstEdges = buildMST(graph)
    graph.setBuiltEdges(mstEdges)
    events.append(
        f"[MST] Kruskal's MST built: {len(mstEdges)} edges spanning "
        f"{len(graph.getAllNodes())} nodes."
    )

    # Step 3a: find Route A via A* (traverses only built MST edges)
    pathA = astarPath(graph, graph.primaryHospital, graph.primaryDepot)
    if len(pathA) == 0:
        events.append("[MST] A* could not find Route A.")
        return ([], [], events)

    routeA = []
    for i in range(len(pathA) - 1):
        routeA.append(edgeKey(pathA[i], pathA[i + 1]))
    events.append(f"[MST] Route A: {len(routeA)} edges, path length {len(pathA)} nodes.")

    # Add Route A edges to the built network
    allBuilt = list(mstEdges)
    for edge in routeA:
        if edge not in allBuilt:
            allBuilt.append(edge)
    graph.setBuiltEdges(allBuilt)

    # Step 3b: temporarily block Route A so Route B is forced down a different path
    for nodeA, nodeB in routeA:
        graph.floodEdge(nodeA, nodeB)

    # Step 3c: find Route B via A* over all grid edges (not just built ones).
    # Route B represents newly-built emergency roads so it can use any edge.
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

    # Step 3d: restore the Route A edges so the rest of the simulation can use them
    for nodeA, nodeB in routeA:
        graph.unfloodEdge(nodeA, nodeB)

    # Final built set = MST + Route A + Route B
    for edge in routeB:
        if edge not in allBuilt:
            allBuilt.append(edge)
    graph.setBuiltEdges(allBuilt)

    return (routeA, routeB, events)
