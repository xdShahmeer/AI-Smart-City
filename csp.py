from collections import deque
import random

from cityGraph import CityGraph


# Building types that trigger proximity constraints
PROXIMITY_TYPES = {"Residential", "PowerPlant"}


# ── BFS helpers ──────────────────────────────────────────────────────────────

def bfsHops(graph, startNode, targetType, maxHops):
    """
    Returns True if a node of targetType exists within maxHops BFS steps
    from startNode. Ignores blocked edges -- layout phase only.
    """
    visited = {startNode}
    queue   = deque([(startNode, 0)])

    while queue:
        current, hops = queue.popleft()
        if hops > maxHops:
            break
        if graph.nodes[current]["type"] == targetType and current != startNode:
            return True
        if hops < maxHops:
            for neighbour in graph.getNeighbours(current):
                if neighbour not in visited:
                    visited.add(neighbour)
                    queue.append((neighbour, hops + 1))

    return False


# ── Constraint checkers ───────────────────────────────────────────────────────

def isAdjacentConstraintOk(graph, node, buildingType):
    """
    Constraint 1: Industrial cannot be adjacent to School or Hospital.
    Check both directions: placing Industrial next to an existing School/Hospital
    is a violation, and placing School/Hospital next to an existing Industrial
    is also a violation.
    """
    neighbours = graph.getNeighbours(node)

    if buildingType == "Industrial":
        for nb in neighbours:
            nbType = graph.nodes[nb]["type"]
            if nbType in ("School", "Hospital"):
                return False
    elif buildingType in ("School", "Hospital"):
        for nb in neighbours:
            if graph.nodes[nb]["type"] == "Industrial":
                return False

    return True


def isResidentialOk(graph, node):
    """
    Constraint 2: Residential must be within 3 hops of a Hospital.
    """
    return bfsHops(graph, node, "Hospital", 3)


def isPowerPlantOk(graph, node):
    """
    Constraint 3: PowerPlant must be within 2 hops of an Industrial node.
    """
    return bfsHops(graph, node, "Industrial", 2)


# ── Domain helpers ────────────────────────────────────────────────────────────

def getValidCells(graph, buildingType, assignment):
    """
    Returns all Empty nodes where buildingType can be placed without
    breaking any active constraint.

    Proximity constraints (2 and 3) are checked incrementally once their
    anchor type is already on the board -- this prunes bad branches early
    instead of discovering violations only at the backtracking leaf.
    """
    hospitalsExist   = bool(graph.getNodesByType("Hospital"))
    industrialsExist = bool(graph.getNodesByType("Industrial"))

    validCells = []
    for node in graph.getAllNodes():
        if graph.nodes[node]["type"] != "Empty":
            continue
        if not isAdjacentConstraintOk(graph, node, buildingType):
            continue
        # Constraint 2: Residential must be within 3 hops of a Hospital.
        # Only enforce once at least one Hospital is already placed.
        if buildingType == "Residential" and hospitalsExist:
            if not isResidentialOk(graph, node):
                continue
        # Constraint 3: PowerPlant must be within 2 hops of an Industrial.
        # Only enforce once at least one Industrial is already placed.
        if buildingType == "PowerPlant" and industrialsExist:
            if not isPowerPlantOk(graph, node):
                continue
        validCells.append(node)
    return validCells


# ── MRV ──────────────────────────────────────────────────────────────────────

def pickMRV(unplaced, graph, assignment):
    """
    MRV heuristic: pick the building type with the fewest valid remaining cells.
    Ties broken alphabetically for determinism.
    """
    bestType   = None
    bestCount  = float('inf')

    for buildingType in sorted(set(unplaced)):
        validCells = getValidCells(graph, buildingType, assignment)
        if len(validCells) < bestCount:
            bestCount = len(validCells)
            bestType  = buildingType

    return bestType


# ── LCV ──────────────────────────────────────────────────────────────────────

def lcvOrder(graph, buildingType, unplaced, assignment):
    """
    LCV heuristic: order candidate cells by how many options they eliminate
    for the remaining unplaced buildings. Try least constraining cells first.

    Scores only up to LCV_SAMPLE candidates to keep runtime fast -- LCV is a
    heuristic so an approximate ordering is still far better than random.
    """
    LCV_SAMPLE = 8

    candidates = getValidCells(graph, buildingType, assignment)

    if len(candidates) <= LCV_SAMPLE:
        toScore = candidates
        rest    = []
    else:
        # Shuffle so the sample is random, not always the same grid corner
        random.shuffle(candidates)
        toScore = candidates[:LCV_SAMPLE]
        rest    = candidates[LCV_SAMPLE:]

    otherTypes = list(set(unplaced) - {buildingType})

    def remainingOptions(cell):
        graph.setNodeType(cell, buildingType)
        remaining = sum(len(getValidCells(graph, t, assignment)) for t in otherTypes)
        graph.setNodeType(cell, "Empty")
        return remaining

    toScore.sort(key=remainingOptions, reverse=True)
    return toScore + rest


# ── Forward checking ──────────────────────────────────────────────────────────

def forwardCheck(graph, unplaced, assignment):
    """
    After a placement, check that every remaining building type still has
    at least one valid cell. If any domain is empty, this branch is a dead end.
    """
    for buildingType in set(unplaced):
        if not getValidCells(graph, buildingType, assignment):
            return False
    return True


# ── Final proximity validation ────────────────────────────────────────────────

def validateProximity(graph):
    """
    Check constraints 2 and 3 after all buildings are placed.
    Returns a list of (node, constraintName) pairs for violations.
    """
    violations = []

    for node in graph.getNodesByType("Residential"):
        if not isResidentialOk(graph, node):
            violations.append((node, "Residential-Hospital proximity"))

    for node in graph.getNodesByType("PowerPlant"):
        if not isPowerPlantOk(graph, node):
            violations.append((node, "PowerPlant-Industrial proximity"))

    return violations


# ── Backtracking search ───────────────────────────────────────────────────────

def backtrack(graph, unplaced, assignment):
    """
    Recursive backtracking with MRV + LCV + forward checking.
    Modifies graph in-place. Returns True on success.
    """
    if not unplaced:
        # All placed -- now check proximity constraints
        return len(validateProximity(graph)) == 0

    nextType = pickMRV(unplaced, graph, assignment)
    cells    = lcvOrder(graph, nextType, unplaced, assignment)

    # Remove one instance of nextType from unplaced list
    remaining = list(unplaced)
    remaining.remove(nextType)

    for cell in cells:
        graph.setNodeType(cell, nextType)
        assignment[cell] = nextType

        if forwardCheck(graph, remaining, assignment):
            if backtrack(graph, remaining, assignment):
                return True

        # Undo placement
        graph.setNodeType(cell, "Empty")
        del assignment[cell]

    return False


# ── Minimum conflict fallback ─────────────────────────────────────────────────

def greedyPlace(graph, buildingList):
    """
    Place all buildings greedily (first available empty cell, no checks).
    Returns the assignment dict used.
    """
    assignment = {}
    emptyCells = [n for n in graph.getAllNodes() if graph.nodes[n]["type"] == "Empty"]

    for buildingType in buildingList:
        for cell in emptyCells:
            if graph.nodes[cell]["type"] == "Empty":
                graph.setNodeType(cell, buildingType)
                assignment[cell] = buildingType
                break

    return assignment


def identifyWorstConstraint(graph):
    """
    Count violations per constraint and return the name of the worst one.
    """
    adjViolations = 0
    for node in graph.getNodesByType("Industrial"):
        for nb in graph.getNeighbours(node):
            if graph.nodes[nb]["type"] in ("School", "Hospital"):
                adjViolations += 1

    resViolations = sum(
        1 for node in graph.getNodesByType("Residential")
        if not isResidentialOk(graph, node)
    )

    ppViolations = sum(
        1 for node in graph.getNodesByType("PowerPlant")
        if not isPowerPlantOk(graph, node)
    )

    counts = {
        "Industrial adjacency (Industrial cannot be next to School or Hospital)": adjViolations,
        "Residential-Hospital proximity (every Residential must be within 3 hops of a Hospital)": resViolations,
        "PowerPlant-Industrial proximity (every PowerPlant must be within 2 hops of an Industrial)": ppViolations,
    }

    return max(counts, key=counts.get)


# ── Public entry point ────────────────────────────────────────────────────────

def runCSP(graph, buildingCounts):
    """
    Place buildings on the graph using CSP backtracking.

    Returns (True, None) if a valid layout was found.
    Returns (False, conflictInfo) if no valid layout exists -- a minimum-conflict
    greedy layout is left on the graph and conflictInfo names the blocking constraint.
    """
    # Expand counts into a flat list of building types to place
    buildingList = []
    for buildingType, count in buildingCounts.items():
        buildingList.extend([buildingType] * count)

    # Place anchor types first so incremental proximity checks work correctly:
    # Hospitals must exist before Residentials are placed (constraint 2),
    # Industrials must exist before PowerPlants are placed (constraint 3).
    PRIORITY = {"Hospital": 0, "Industrial": 1, "AmbulanceDepot": 2,
                "School": 3, "PowerPlant": 4, "Residential": 5}
    buildingList.sort(key=lambda t: PRIORITY.get(t, 3))

    assignment = {}
    success    = backtrack(graph, buildingList, assignment)

    if success:
        return (True, None)

    # CSP failed -- reset graph and run greedy fallback
    for node in graph.getAllNodes():
        graph.setNodeType(node, "Empty")

    greedyPlace(graph, buildingList)
    worstConstraint = identifyWorstConstraint(graph)

    conflictInfo = (
        f"Constraint failed: {worstConstraint}. "
        f"A minimum-conflict layout has been placed. "
        f"Adjust building counts and retry to find a valid solution."
    )

    return (False, conflictInfo)
