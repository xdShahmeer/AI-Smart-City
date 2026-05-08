import heapq
import math
from cityGraph import CityGraph, edgeKey


# --- Union-Find helpers for Kruskal's ---

def find(parent, node):
    # Path compression: point directly to root
    if parent[node] != node:
        parent[node] = find(parent, parent[node])
    return parent[node]


def union(parent, rank, a, b):
    # Union by rank: attach smaller tree under larger
    rootA = find(parent, a)
    rootB = find(parent, b)
    if rootA == rootB:
        return False  # already in the same component
    if rank[rootA] < rank[rootB]:
        rootA, rootB = rootB, rootA
    parent[rootB] = rootA
    if rank[rootA] == rank[rootB]:
        rank[rootA] += 1
    return True


# --- A* search (base costs only, no crime multiplier) ---

def astarPath(graph, start, goal):
    # Returns ordered list of nodes from start to goal, or [] if no path exists.
    # Respects blocked edges so temporarily-blocked Route A edges are avoided.

    if start == goal:
        return [start]

    def heuristic(node):
        return abs(node[0] - goal[0]) + abs(node[1] - goal[1])

    # (fScore, gScore, node, path)
    openSet = []
    heapq.heappush(openSet, (heuristic(start), 0, start, [start]))

    # Best gScore seen per node
    visited = {}

    while openSet:
        fScore, gScore, current, path = heapq.heappop(openSet)

        if current == goal:
            return path

        # Skip if we already reached this node cheaper
        if current in visited and visited[current] <= gScore:
            continue
        visited[current] = gScore

        for neighbour in graph.getNeighbours(current):
            if graph.isEdgeBlocked(current, neighbour):
                continue  # skip blocked road
            edgeCost = graph.getEdgeCost(current, neighbour)
            newG = gScore + edgeCost
            if neighbour not in visited or visited[neighbour] > newG:
                newF = newG + heuristic(neighbour)
                heapq.heappush(openSet, (newF, newG, neighbour, path + [neighbour]))

    return []  # no path found


# --- Primary node selection ---

def pickCentreNode(nodeList, rows, cols):
    # Pick the node closest to the geometric centre.
    # Tiebreaker: lower row first, then lower col.
    centreRow = rows / 2
    centreCol = cols / 2

    def distToCentre(node):
        r, c = node
        return math.sqrt((r - centreRow) ** 2 + (c - centreCol) ** 2)

    return min(nodeList, key=lambda n: (distToCentre(n), n[0], n[1]))


# --- Kruskal's MST ---

def buildMST(graph):
    # Returns list of edge tuples (nodeA, nodeB) that form the MST.
    allNodes = graph.getAllNodes()
    allEdges = graph.getAllEdges()

    # Sort edges by cost ascending
    sortedEdges = sorted(allEdges, key=lambda e: graph.edges[e]["cost"])

    parent = {node: node for node in allNodes}
    rank   = {node: 0 for node in allNodes}

    mstEdges = []
    for edgeTuple in sortedEdges:
        nodeA, nodeB = edgeTuple
        if union(parent, rank, nodeA, nodeB):
            mstEdges.append(edgeTuple)
        if len(mstEdges) == len(allNodes) - 1:
            break  # MST is complete

    return mstEdges


# --- Main public function ---

def buildRoadNetwork(graph):
    """
    Designates Primary Hospital and Primary Depot, builds Kruskal's MST,
    then adds two independent emergency routes via A*.

    Returns (routeA, routeB) where each is a list of (nodeA, nodeB) edge tuples.
    Returns ([], []) if no hospital or no depot exists.
    """

    # Step 1: designate primary nodes
    hospitals = graph.getNodesByType("Hospital")
    depots    = graph.getNodesByType("AmbulanceDepot")

    graph.primaryHospital = pickCentreNode(hospitals, graph.rows, graph.cols) if hospitals else None
    graph.primaryDepot    = pickCentreNode(depots,    graph.rows, graph.cols) if depots    else None

    if graph.primaryHospital is None or graph.primaryDepot is None:
        print("[MST] Missing hospital or depot -- skipping emergency route construction.")
        return ([], [])

    print(f"[MST] Primary Hospital: {graph.primaryHospital}")
    print(f"[MST] Primary Depot:    {graph.primaryDepot}")

    # Step 2: build MST (demonstrates the algorithm; all edges remain traversable)
    mstEdges = buildMST(graph)
    print(f"[MST] Kruskal's MST built: {len(mstEdges)} edges spanning {len(graph.getAllNodes())} nodes.")

    # Step 3a: Route A via A*
    pathA = astarPath(graph, graph.primaryHospital, graph.primaryDepot)
    if not pathA:
        print("[MST] A* could not find Route A.")
        return ([], [])

    routeA = [edgeKey(pathA[i], pathA[i + 1]) for i in range(len(pathA) - 1)]
    print(f"[MST] Route A: {len(routeA)} edges, path length {len(pathA)} nodes.")

    # Step 3b: temporarily block Route A edges so Route B must be different
    for nodeA, nodeB in routeA:
        graph.floodEdge(nodeA, nodeB)

    # Step 3c: Route B via A*
    pathB = astarPath(graph, graph.primaryHospital, graph.primaryDepot)
    routeB = []
    if pathB:
        routeB = [edgeKey(pathB[i], pathB[i + 1]) for i in range(len(pathB) - 1)]
        print(f"[MST] Route B: {len(routeB)} edges, path length {len(pathB)} nodes.")
    else:
        print("[MST] No independent Route B found -- city topology may be too constrained.")

    # Step 3d: restore Route A edges
    for nodeA, nodeB in routeA:
        graph.unfloodEdge(nodeA, nodeB)

    return (routeA, routeB)
