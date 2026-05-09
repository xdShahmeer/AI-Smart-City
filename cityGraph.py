import random
from collections import defaultdict


# Population ranges per building type. The graph generator picks a random
# integer inside the range when a node is assigned a type.
POPULATION_RANGES = {
    "Residential":    (50,  200),
    "School":         (100, 400),
    "Industrial":     (80,  300),
    "Hospital":       (30,  150),
    "PowerPlant":     (20,  80),
    "AmbulanceDepot": (10,  40),
    "Empty":          (0,   0),
}

# Standard road cost and the discounted cost when one endpoint is Residential.
STANDARD_COST    = 1.0
RESIDENTIAL_COST = 0.8


def edgeKey(nodeA, nodeB):
    # Canonical (smaller, larger) ordering so each edge is stored once.
    if nodeA < nodeB:
        return (nodeA, nodeB)
    return (nodeB, nodeA)


class CityGraph:
    def __init__(self, rows=10, cols=10):
        self.rows = rows
        self.cols = cols

        # Set by other modules during setup
        self.primaryHospital    = None
        self.primaryDepot       = None
        self.ambulancePositions = []
        self.policeOfficers     = []

        self._buildGrid()

    def _buildGrid(self):
        # Create every node, then connect each one to its 4-direction neighbours.
        self.nodes   = {}
        self.edges   = {}
        self.adjList = defaultdict(list)

        # Step 1: create the node dictionary
        for row in range(self.rows):
            for col in range(self.cols):
                node = (row, col)
                self.nodes[node] = {
                    "type":       "Empty",
                    "population": 0,
                    "riskIndex":  1.0,
                    "accessible": True,
                }

        # Step 2: connect each node to its up/down/left/right neighbour
        for row in range(self.rows):
            for col in range(self.cols):
                node = (row, col)
                self._connectFourDirections(node, row, col)

    def _connectFourDirections(self, node, row, col):
        # The four cardinal directions: up, down, left, right.
        directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]

        for deltaRow, deltaCol in directions:
            newRow = row + deltaRow
            newCol = col + deltaCol

            # Skip directions that fall off the grid
            if newRow < 0 or newRow >= self.rows:
                continue
            if newCol < 0 or newCol >= self.cols:
                continue

            neighbour = (newRow, newCol)
            key       = edgeKey(node, neighbour)

            # Add the edge if we have not already stored it
            if key not in self.edges:
                self.edges[key] = {
                    "cost":    self._calcCost(node, neighbour),
                    "blocked": False,
                }

            # Add the neighbour to the adjacency list (no duplicates)
            if neighbour not in self.adjList[node]:
                self.adjList[node].append(neighbour)

    def _calcCost(self, nodeA, nodeB):
        # Discounted cost if either endpoint is a Residential node.
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
        # Clears every node, every edge, and the per-module placeholders.
        if rows is not None:
            self.rows = rows
        if cols is not None:
            self.cols = cols

        self.primaryHospital    = None
        self.primaryDepot       = None
        self.ambulancePositions = []
        self.policeOfficers     = []

        self._buildGrid()

    # ------------------------------------------------------------------ #
    #  Setters                                                             #
    # ------------------------------------------------------------------ #

    def setNodeType(self, node, buildingType):
        # Assign the node's type, draw a random population from its range, and
        # recalculate the cost of every edge that touches this node.
        lowPop, highPop = POPULATION_RANGES[buildingType]
        if lowPop == highPop:
            populationValue = 0
        else:
            populationValue = random.randint(lowPop, highPop)

        self.nodes[node]["type"]       = buildingType
        self.nodes[node]["population"] = populationValue

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
        # All 4-direction neighbours regardless of accessibility.
        return list(self.adjList[node])

    def getAccessibleNeighbours(self, node):
        # Only neighbours reachable through an unblocked edge whose target
        # node is also still accessible.
        result = []
        for neighbour in self.adjList[node]:
            key         = edgeKey(node, neighbour)
            edgeBlocked = self.edges[key]["blocked"]
            nodeOk      = self.nodes[neighbour]["accessible"]
            if not edgeBlocked and nodeOk:
                result.append(neighbour)
        return result

    def getEdgeCost(self, nodeA, nodeB):
        key  = edgeKey(nodeA, nodeB)
        edge = self.edges[key]
        if edge["blocked"]:
            return float('inf')
        return edge["cost"]

    def getWeightedCost(self, nodeA, nodeB):
        # Base cost multiplied by the destination node's crime risk index.
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
        result = []
        for node in self.nodes:
            if self.nodes[node]["accessible"]:
                result.append(node)
        return result

    def getNodesByType(self, buildingType):
        result = []
        for node in self.nodes:
            if self.nodes[node]["type"] == buildingType:
                result.append(node)
        return result

    def getAllEdges(self):
        return list(self.edges.keys())
