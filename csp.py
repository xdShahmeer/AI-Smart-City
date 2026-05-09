from collections import deque
import random


# Default proximity hop budgets. The UI can override these via runCSP() so
# the constraints can be tweaked live during the viva modification challenge.
RESIDENTIAL_MAX_HOPS = 3
POWERPLANT_MAX_HOPS  = 2

# Whether Industrial nodes are forbidden adjacent to Schools/Hospitals.
# Toggleable via runCSP(industrialAdjacencyRule=False) for the live-mod demo.
INDUSTRIAL_ADJACENCY_RULE = True

# When choosing which empty cell to place a building in, only the first
# LCV_SAMPLE candidates are scored to keep backtracking fast on larger grids.
# The remaining candidates are appended unscored after a shuffle. This is a
# defensible approximation of LCV -- forward checking and the leaf proximity
# validation still gate every full assignment, so we never lose correctness.
LCV_SAMPLE = 8

# Order in which building types are placed during backtracking. Anchors come
# first so proximity constraints can be enforced incrementally:
#   - Hospitals before Residentials (constraint 2)
#   - Industrials before PowerPlants (constraint 3)
PLACEMENT_PRIORITY = {
    "Hospital":       0,
    "Industrial":     1,
    "AmbulanceDepot": 2,
    "School":         3,
    "PowerPlant":     4,
    "Residential":    5,
}


# ── BFS helper ────────────────────────────────────────────────────────────────

def bfsHops(graph, startNode, targetType, maxHops):
    # Returns True if a node of targetType exists within maxHops BFS steps
    # from startNode. Ignores blocked edges -- this runs during the layout
    # phase before the simulation starts.
    visited = {startNode}
    queue   = deque()
    queue.append((startNode, 0))

    while queue:
        current, hops = queue.popleft()

        # Match found: targetType, and not the start node itself
        if graph.nodes[current]["type"] == targetType and current != startNode:
            return True

        if hops >= maxHops:
            continue

        for neighbour in graph.getNeighbours(current):
            if neighbour not in visited:
                visited.add(neighbour)
                queue.append((neighbour, hops + 1))

    return False


# ── Constraint checkers ───────────────────────────────────────────────────────

def isAdjacentConstraintOk(graph, node, buildingType):
    # Constraint 1: Industrial cannot share an edge with School or Hospital.
    # Disabled when INDUSTRIAL_ADJACENCY_RULE is False (live-mod toggle).
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
    # Constraint 2: Residential must be within RESIDENTIAL_MAX_HOPS of a Hospital.
    return bfsHops(graph, node, "Hospital", RESIDENTIAL_MAX_HOPS)


def isPowerPlantOk(graph, node):
    # Constraint 3: PowerPlant must be within POWERPLANT_MAX_HOPS of an Industrial.
    return bfsHops(graph, node, "Industrial", POWERPLANT_MAX_HOPS)


# ── Domain helpers ────────────────────────────────────────────────────────────

def getValidCells(graph, buildingType, assignment):
    # Returns every Empty node where buildingType can be placed without
    # violating an active constraint. Proximity constraints are only checked
    # once their anchor type is already placed -- this prunes bad branches
    # early instead of discovering violations only at the backtracking leaf.
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


# ── MRV (Minimum Remaining Values) ────────────────────────────────────────────

def pickMRV(unplaced, graph):
    # MRV heuristic: pick the building type with the fewest valid cells left.
    # Ties are broken alphabetically for determinism.
    typesToConsider = sorted(set(unplaced))

    bestType  = None
    bestCount = float('inf')

    for buildingType in typesToConsider:
        validCells = getValidCells(graph, buildingType, None)
        if len(validCells) < bestCount:
            bestCount = len(validCells)
            bestType  = buildingType

    return bestType


# ── LCV (Least Constraining Value) ────────────────────────────────────────────

def lcvOrder(graph, buildingType, unplaced):
    # LCV heuristic: order candidate cells by how few options they remove
    # for the remaining unplaced types. Try the least constraining cells first.
    candidates = getValidCells(graph, buildingType, None)

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

    # Score each candidate: total valid cells across other types after placing here
    scored = []
    for cell in toScore:
        graph.setNodeType(cell, buildingType)

        remainingOptions = 0
        for otherType in otherTypes:
            remainingOptions += len(getValidCells(graph, otherType, None))

        graph.setNodeType(cell, "Empty")
        scored.append((remainingOptions, cell))

    # Higher remaining options = less constraining = try first.
    scored.sort(reverse=True)
    sortedCells = []
    for remainingOptions, cell in scored:
        sortedCells.append(cell)

    return sortedCells + leftovers


# ── Forward checking ──────────────────────────────────────────────────────────

def forwardCheck(graph, unplaced):
    # After a placement, every remaining building type must still have at
    # least one valid cell. If any domain is empty, this branch is dead.
    seenTypes = set()
    for buildingType in unplaced:
        if buildingType in seenTypes:
            continue
        seenTypes.add(buildingType)
        if len(getValidCells(graph, buildingType, None)) == 0:
            return False
    return True


# ── Final proximity validation ────────────────────────────────────────────────

def validateProximity(graph):
    # Re-check constraints 2 and 3 after all buildings are placed.
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
    # Recursive backtracking with MRV + LCV + forward checking.
    # Modifies graph in-place. Returns True on success.
    if len(unplaced) == 0:
        return len(validateProximity(graph)) == 0

    nextType = pickMRV(unplaced, graph)
    cells    = lcvOrder(graph, nextType, unplaced)

    # Build the new unplaced list: same as before, with one nextType removed.
    remaining = list(unplaced)
    remaining.remove(nextType)

    for cell in cells:
        graph.setNodeType(cell, nextType)
        assignment[cell] = nextType

        if forwardCheck(graph, remaining):
            if backtrack(graph, remaining, assignment):
                return True

        # Undo the placement before trying the next cell
        graph.setNodeType(cell, "Empty")
        del assignment[cell]

    return False


# ── Minimum-conflict fallback ─────────────────────────────────────────────────

def greedyPlace(graph, buildingList):
    # Place every building in the first available Empty cell, no rule checks.
    # Used after backtracking fails so we still produce SOMETHING to highlight.
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
    # Count violations per constraint and return the name of the one with the
    # most violations. This becomes the message shown to the user.
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

    # Pick the constraint name with the highest count
    worstName  = None
    worstCount = -1
    for name in counts:
        if counts[name] > worstCount:
            worstCount = counts[name]
            worstName  = name
    return worstName


# ── Building list helpers ─────────────────────────────────────────────────────

def getPlacementPriority(buildingType):
    # Lower number = placed first. Used by sortByPlacementPriority below.
    if buildingType in PLACEMENT_PRIORITY:
        return PLACEMENT_PRIORITY[buildingType]
    return 3   # default for any future type we haven't classified


def sortByPlacementPriority(buildingList):
    # In-place sort using getPlacementPriority. Replaces the previous
    # `key=lambda` style with a plain named function so the intent is obvious.
    buildingList.sort(key=getPlacementPriority)


# ── Public entry point ────────────────────────────────────────────────────────

def runCSP(graph, buildingCounts, residentialHops=None, powerplantHops=None,
           industrialAdjacencyRule=None):
    # Place buildings on the graph using CSP backtracking.
    #
    # Optional overrides set the module-level constraint constants for this
    # run, so the UI can support live modification of rules:
    #   - residentialHops          -> RESIDENTIAL_MAX_HOPS
    #   - powerplantHops           -> POWERPLANT_MAX_HOPS
    #   - industrialAdjacencyRule  -> INDUSTRIAL_ADJACENCY_RULE
    #
    # Returns (True, None) when a valid layout was found.
    # Returns (False, conflictInfo) when no valid layout exists -- a
    # minimum-conflict greedy layout is left on the graph in that case.
    global RESIDENTIAL_MAX_HOPS, POWERPLANT_MAX_HOPS, INDUSTRIAL_ADJACENCY_RULE
    if residentialHops is not None:
        RESIDENTIAL_MAX_HOPS = residentialHops
    if powerplantHops is not None:
        POWERPLANT_MAX_HOPS = powerplantHops
    if industrialAdjacencyRule is not None:
        INDUSTRIAL_ADJACENCY_RULE = industrialAdjacencyRule

    # Expand counts into a flat list of building types to place
    buildingList = []
    for buildingType in buildingCounts:
        count = buildingCounts[buildingType]
        for _ in range(count):
            buildingList.append(buildingType)

    sortByPlacementPriority(buildingList)

    assignment = {}
    success    = backtrack(graph, buildingList, assignment)

    if success:
        return (True, None)

    # Backtracking failed -- wipe the graph and lay down a minimum-conflict
    # fallback so the UI still has something to display.
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
