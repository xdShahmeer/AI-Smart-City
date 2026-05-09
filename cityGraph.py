import random
from collections import defaultdict


# Population ranges for each building type
POPULATION_RANGES = {
    "Residential":    (50,  200),
    "School":         (100, 400),
    "Industrial":     (80,  300),
    "Hospital":       (30,  150),
    "PowerPlant":     (20,  80),
    "AmbulanceDepot": (10,  40),
    "Empty":          (0,   0),
}

# Standard road cost and discounted cost for residential endpoints
STANDARD_COST    = 1.0
RESIDENTIAL_COST = 0.8


def edgeKey(nodeA, nodeB):
    # Canonical key so each edge is stored once regardless of direction
    return (min(nodeA, nodeB), max(nodeA, nodeB))


class CityGraph:
    def __init__(self, rows=10, cols=10):
        self.rows = rows
        self.cols = cols

        # Placeholders set by other modules
        self.primaryHospital    = None
        self.primaryDepot       = None
        self.ambulancePositions = []

        self._buildGrid()

    def _buildGrid(self):
        # Create all nodes and edges from scratch
        self.nodes   = {}
        self.edges   = {}
        self.adjList = defaultdict(list)

        for r in range(self.rows):
            for c in range(self.cols):
                node = (r, c)
                self.nodes[node] = {
                    "type":       "Empty",
                    "population": 0,
                    "riskIndex":  1.0,
                    "accessible": True,
                }

        # Connect each node to its 4-directional neighbours
        directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        for r in range(self.rows):
            for c in range(self.cols):
                node = (r, c)
                for dr, dc in directions:
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < self.rows and 0 <= nc < self.cols:
                        neighbour = (nr, nc)
                        key = edgeKey(node, neighbour)

                        if key not in self.edges:
                            self.edges[key] = {
                                "cost":    self._calcCost(node, neighbour),
                                "blocked": False,
                            }

                        if neighbour not in self.adjList[node]:
                            self.adjList[node].append(neighbour)

    def _calcCost(self, nodeA, nodeB):
        # 0.8 if either endpoint is Residential, otherwise 1.0
        typeA = self.nodes[nodeA]["type"]
        typeB = self.nodes[nodeB]["type"]
        if typeA == "Residential" or typeB == "Residential":
            return RESIDENTIAL_COST
        return STANDARD_COST

    def floodEdge(self, nodeA, nodeB):
        key = edgeKey(nodeA, nodeB)
        self.edges[key]["blocked"] = True

    def unfloodEdge(self, nodeA, nodeB):
        key = edgeKey(nodeA, nodeB)
        self.edges[key]["blocked"] = False

    def reset(self, rows=None, cols=None):
        if rows is not None:
            self.rows = rows
        if cols is not None:
            self.cols = cols

        self.primaryHospital    = None
        self.primaryDepot       = None
        self.ambulancePositions = []

        self._buildGrid()

    # ------------------------------------------------------------------ #
    #  Setters                                                             #
    # ------------------------------------------------------------------ #

    def setNodeType(self, node, buildingType):
        lo, hi = POPULATION_RANGES[buildingType]
        pop = random.randint(lo, hi) if lo != hi else 0

        self.nodes[node]["type"]       = buildingType
        self.nodes[node]["population"] = pop

        # Recalculate costs for all edges touching this node
        for neighbour in self.adjList[node]:
            key = edgeKey(node, neighbour)
            self.edges[key]["cost"] = self._calcCost(node, neighbour)

    def setRiskIndex(self, node, riskIndex):
        self.nodes[node]["riskIndex"] = riskIndex

    def setAccessible(self, node, accessible):
        self.nodes[node]["accessible"] = accessible

    # ------------------------------------------------------------------ #
    #  Getters                                                             #
    # ------------------------------------------------------------------ #

    def getNeighbours(self, node):
        # All 4-directional neighbours, no accessibility checks
        return list(self.adjList[node])

    def getAccessibleNeighbours(self, node):
        # Only neighbours reachable by an unblocked edge AND whose node is accessible
        result = []
        for neighbour in self.adjList[node]:
            key = edgeKey(node, neighbour)
            edgeBlocked = self.edges[key]["blocked"]
            nodeOk      = self.nodes[neighbour]["accessible"]
            if not edgeBlocked and nodeOk:
                result.append(neighbour)
        return result

    def getEdgeCost(self, nodeA, nodeB):
        key = edgeKey(nodeA, nodeB)
        edge = self.edges[key]
        if edge["blocked"]:
            return float('inf')
        return edge["cost"]

    def getWeightedCost(self, nodeA, nodeB):
        # Base cost multiplied by the destination node's crime risk index
        baseCost = self.getEdgeCost(nodeA, nodeB)
        if baseCost == float('inf'):
            return float('inf')
        return baseCost * self.nodes[nodeB]["riskIndex"]

    def isEdgeBlocked(self, nodeA, nodeB):
        key = edgeKey(nodeA, nodeB)
        return self.edges[key]["blocked"]

    def getAllNodes(self):
        return list(self.nodes.keys())

    def getAccessibleNodes(self):
        return [node for node, data in self.nodes.items() if data["accessible"]]

    def getNodesByType(self, buildingType):
        return [node for node, data in self.nodes.items() if data["type"] == buildingType]

    def getAllEdges(self):
        # Returns (nodeA, nodeB) using canonical ordering
        return list(self.edges.keys())
