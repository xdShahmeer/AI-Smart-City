from collections import deque
import random


# default hop limits
RESIDENTIAL_MAX_HOPS = 3
POWERPLANT_MAX_HOPS  = 2

# industrial adjacency rule
INDUSTRIAL_ADJACENCY_RULE = True

# lcv sample size
LCV_SAMPLE = 8

# placement order
PLACEMENT_PRIORITY = {
    "Hospital":       0,
    "Industrial":     1,
    "AmbulanceDepot": 2,
    "School":         3,
    "PowerPlant":     4,
    "Residential":    5,
}


# bfs helper

def bfsHops(graph, startNode, targetType, maxHops):
    # check hops to target type
    visited = {startNode}
    queue   = deque()
    queue.append((startNode, 0))

    while queue:
        current, hops = queue.popleft()

        # target found
        if graph.nodes[current]["type"] == targetType and current != startNode:
            return True

        if hops >= maxHops:
            continue

        for neighbour in graph.getNeighbours(current):
            if neighbour not in visited:
                visited.add(neighbour)
                queue.append((neighbour, hops + 1))

    return False


# constraint checks

def isAdjacentConstraintOk(graph, node, buildingType):
    if not INDUSTRIAL_ADJACENCY_RULE:
        return True

    if buildingType == "Industrial":
        for neighbour in graph.getNeighbours(node):
            neighbourType = graph.nodes[neighbour]["type"]
            if neighbourType == "School" or neighbourType == "Hospital":
                return False
        return True

    if buildingType == "School" or buildingType == "Hospital":
        for neighbour in graph.getNeighbours(node):
            if graph.nodes[neighbour]["type"] == "Industrial":
                return False
        return True

    return True


def isResidentialOk(graph, node):
    # residential needs hospital nearby
    return bfsHops(graph, node, "Hospital", RESIDENTIAL_MAX_HOPS)


def isPowerPlantOk(graph, node):
    # power plant needs industrial nearby
    return bfsHops(graph, node, "Industrial", POWERPLANT_MAX_HOPS)


# domain helpers

def getValidCells(graph, buildingType):
    # get open cells for this type
    hospitalsExist   = len(graph.getNodesByType("Hospital"))   > 0
    industrialsExist = len(graph.getNodesByType("Industrial")) > 0

    validCells = []
    for node in graph.getAllNodes():
        if graph.nodes[node]["type"] != "Empty":
            continue
        if not isAdjacentConstraintOk(graph, node, buildingType):
            continue

        if buildingType == "Residential" and hospitalsExist:
            if not isResidentialOk(graph, node):
                continue

        if buildingType == "PowerPlant" and industrialsExist:
            if not isPowerPlantOk(graph, node):
                continue

        validCells.append(node)
    return validCells


# mrv helper

def pickMRV(unplaced, graph):
    typesToConsider = sorted(set(unplaced))

    bestType  = None
    bestCount = float('inf')

    for buildingType in typesToConsider:
        validCells = getValidCells(graph, buildingType)
        if len(validCells) < bestCount:
            bestCount = len(validCells)
            bestType  = buildingType

    return bestType


# lcv helper

def lcvOrder(graph, buildingType, unplaced):
    candidates = getValidCells(graph, buildingType)

    if len(candidates) <= LCV_SAMPLE:
        toScore   = candidates
        leftovers = []
    else:
        random.shuffle(candidates)
        toScore   = candidates[:LCV_SAMPLE]
        leftovers = candidates[LCV_SAMPLE:]

    otherTypes = []
    for placedType in unplaced:
        if placedType != buildingType and placedType not in otherTypes:
            otherTypes.append(placedType)

    # score each candidate
    scored = []
    for cell in toScore:
        graph.setNodeType(cell, buildingType)

        remainingOptions = 0
        for otherType in otherTypes:
            remainingOptions += len(getValidCells(graph, otherType))

        graph.setNodeType(cell, "Empty")
        scored.append((remainingOptions, cell))

    scored.sort(reverse=True)
    sortedCells = []
    for remainingOptions, cell in scored:
        sortedCells.append(cell)

    return sortedCells + leftovers


# forward check

def forwardCheck(graph, unplaced):
    seenTypes = set()
    for buildingType in unplaced:
        if buildingType in seenTypes:
            continue
        seenTypes.add(buildingType)
        if len(getValidCells(graph, buildingType)) == 0:
            return False
    return True


# final check

def validateProximity(graph):
    violations = []

    for node in graph.getNodesByType("Residential"):
        if not isResidentialOk(graph, node):
            violations.append((node, "Residential-Hospital proximity"))

    for node in graph.getNodesByType("PowerPlant"):
        if not isPowerPlantOk(graph, node):
            violations.append((node, "PowerPlant-Industrial proximity"))

    return violations


# backtracking search

def backtrack(graph, unplaced, assignment):
    if len(unplaced) == 0:
        return len(validateProximity(graph)) == 0

    nextType = pickMRV(unplaced, graph)
    cells    = lcvOrder(graph, nextType, unplaced)

    remaining = list(unplaced)
    remaining.remove(nextType)

    for cell in cells:
        graph.setNodeType(cell, nextType)
        assignment[cell] = nextType

        if forwardCheck(graph, remaining):
            if backtrack(graph, remaining, assignment):
                return True

        # undo the placement
        graph.setNodeType(cell, "Empty")
        del assignment[cell]

    return False


# fallback helpers

def greedyPlace(graph, buildingList):
    assignment = {}

    emptyCells = []
    for node in graph.getAllNodes():
        if graph.nodes[node]["type"] == "Empty":
            emptyCells.append(node)

    for buildingType in buildingList:
        for cell in emptyCells:
            if graph.nodes[cell]["type"] == "Empty":
                graph.setNodeType(cell, buildingType)
                assignment[cell] = buildingType
                break

    return assignment


def identifyWorstConstraint(graph):
    adjacencyViolations = 0
    for node in graph.getNodesByType("Industrial"):
        for neighbour in graph.getNeighbours(node):
            neighbourType = graph.nodes[neighbour]["type"]
            if neighbourType == "School" or neighbourType == "Hospital":
                adjacencyViolations += 1

    residentialViolations = 0
    for node in graph.getNodesByType("Residential"):
        if not isResidentialOk(graph, node):
            residentialViolations += 1

    powerPlantViolations = 0
    for node in graph.getNodesByType("PowerPlant"):
        if not isPowerPlantOk(graph, node):
            powerPlantViolations += 1

    counts = {
        "Industrial adjacency (Industrial cannot be next to School or Hospital)":
            adjacencyViolations,
        "Residential-Hospital proximity (every Residential within 3 hops of a Hospital)":
            residentialViolations,
        "PowerPlant-Industrial proximity (every PowerPlant within 2 hops of an Industrial)":
            powerPlantViolations,
    }

    worstName  = None
    worstCount = -1
    for name in counts:
        if counts[name] > worstCount:
            worstCount = counts[name]
            worstName  = name
    return worstName


# building order helpers

def getPlacementPriority(buildingType):
    if buildingType in PLACEMENT_PRIORITY:
        return PLACEMENT_PRIORITY[buildingType]
    return 3


def sortByPlacementPriority(buildingList):
    buildingList.sort(key=getPlacementPriority)


# public entry point

def runCSP(graph, buildingCounts, residentialHops=None, powerplantHops=None,
           industrialAdjacencyRule=None):
    # place buildings with csp
    # save globals so overrides do not leak across runs
    global RESIDENTIAL_MAX_HOPS, POWERPLANT_MAX_HOPS, INDUSTRIAL_ADJACENCY_RULE
    savedResidential = RESIDENTIAL_MAX_HOPS
    savedPowerplant  = POWERPLANT_MAX_HOPS
    savedIndustrial  = INDUSTRIAL_ADJACENCY_RULE
    if residentialHops is not None:
        RESIDENTIAL_MAX_HOPS = residentialHops
    if powerplantHops is not None:
        POWERPLANT_MAX_HOPS = powerplantHops
    if industrialAdjacencyRule is not None:
        INDUSTRIAL_ADJACENCY_RULE = industrialAdjacencyRule

    # flatten counts
    buildingList = []
    for buildingType in buildingCounts:
        count = buildingCounts[buildingType]
        for _ in range(count):
            buildingList.append(buildingType)

    sortByPlacementPriority(buildingList)

    assignment = {}
    success    = backtrack(graph, buildingList, assignment)

    # restore globals so defaults work on next run
    RESIDENTIAL_MAX_HOPS = savedResidential
    POWERPLANT_MAX_HOPS  = savedPowerplant
    INDUSTRIAL_ADJACENCY_RULE = savedIndustrial

    if success:
        return (True, None)

    # fallback layout
    for node in graph.getAllNodes():
        graph.setNodeType(node, "Empty")

    greedyPlace(graph, buildingList)
    worstConstraint = identifyWorstConstraint(graph)

    conflictInfo = (
        f"Constraint failed: {worstConstraint}. "
        f"A minimum-conflict layout has been placed. "
        f"Adjust the building counts and retry to find a valid solution."
    )

    return (False, conflictInfo)
