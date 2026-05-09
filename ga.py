import heapq
import random


# GA parameters. Sized to converge well on grids up to 30x30 while still
# completing setup in well under a second on small grids. The fitness cache
# means elitism does not pay the Dijkstra cost twice across generations.
POPULATION_SIZE = 30
NUM_GENERATIONS = 60
MUTATION_RATE   = 0.10
NUM_AMBULANCES  = 3
NUM_PARENTS     = POPULATION_SIZE // 2     # top half kept each generation


# ── Dijkstra (weighted shortest paths) ────────────────────────────────────────

def dijkstra(graph, source):
    # Shortest weighted distances from the source to every other node.
    # Uses graph.getAccessibleNeighbours and graph.getWeightedCost. Nodes
    # that cannot be reached stay at infinity.
    distance = {}
    for node in graph.nodes:
        distance[node] = float('inf')
    distance[source] = 0.0

    heap = []
    heapq.heappush(heap, (0.0, source))

    while heap:
        currentDist, node = heapq.heappop(heap)

        # Skip stale entries -- a better path was already processed
        if currentDist > distance[node]:
            continue

        for neighbour in graph.getAccessibleNeighbours(node):
            edgeCost = graph.getWeightedCost(node, neighbour)
            newDist  = currentDist + edgeCost
            if newDist < distance[neighbour]:
                distance[neighbour] = newDist
                heapq.heappush(heap, (newDist, neighbour))

    return distance


# ── Fitness ───────────────────────────────────────────────────────────────────

def computeFitness(chromosome, graph):
    # Worst-case response time: the maximum distance from any accessible node
    # to its nearest ambulance. Lower fitness is better.
    accessibleNodes = graph.getAccessibleNodes()

    # One Dijkstra run per ambulance position, collected into a list
    distanceMaps = []
    for ambulancePos in chromosome:
        distanceMaps.append(dijkstra(graph, ambulancePos))

    worstCase = 0.0
    for node in accessibleNodes:
        # The team that reaches this node fastest is the nearest ambulance
        nearestDist = float('inf')
        for distanceMap in distanceMaps:
            if distanceMap[node] < nearestDist:
                nearestDist = distanceMap[node]

        if nearestDist > worstCase:
            worstCase = nearestDist

    return worstCase


# ── Population helpers ────────────────────────────────────────────────────────

def randomChromosome(graph):
    # Pick NUM_AMBULANCES distinct accessible nodes at random.
    accessibleNodes = graph.getAccessibleNodes()
    return random.sample(accessibleNodes, NUM_AMBULANCES)


def crossover(parentA, parentB):
    # Single-point crossover: take the first part of parentA and the rest
    # from parentB. Always at least one position from each parent.
    splitPoint = random.randint(1, NUM_AMBULANCES - 1)
    child = parentA[:splitPoint] + parentB[splitPoint:]
    return child


def fixDuplicates(chromosome, graph):
    # Replace duplicate positions with fresh accessible nodes. Falls back to
    # keeping a duplicate if the graph has run out of unique candidates.
    accessibleNodes = graph.getAccessibleNodes()
    alreadyUsed     = set(chromosome)
    seen            = set()
    fixed           = []

    for position in chromosome:
        if position not in seen:
            seen.add(position)
            fixed.append(position)
            continue

        # Duplicate -- look for any accessible node we have not used yet
        replacement = None
        for candidate in accessibleNodes:
            if candidate not in alreadyUsed:
                replacement = candidate
                break

        if replacement is not None:
            alreadyUsed.add(replacement)
            seen.add(replacement)
            fixed.append(replacement)
        else:
            fixed.append(position)

    return fixed


def mutate(chromosome, graph):
    # With MUTATION_RATE probability, swap one position for a fresh random
    # accessible node not currently in the chromosome.
    if random.random() >= MUTATION_RATE:
        return chromosome

    accessibleNodes = graph.getAccessibleNodes()
    indexToMutate   = random.randrange(NUM_AMBULANCES)
    currentSet      = set(chromosome)

    candidates = []
    for node in accessibleNodes:
        if node not in currentSet:
            candidates.append(node)

    if len(candidates) > 0:
        chromosome[indexToMutate] = random.choice(candidates)

    return chromosome


# ── Sorting helper (replaces a lambda) ────────────────────────────────────────

def fitnessOf(scoredEntry):
    # `scored` holds (fitnessValue, chromosome) tuples; sort by the first item.
    return scoredEntry[0]


# ── Main GA loop ──────────────────────────────────────────────────────────────

def runGA(graph):
    # Runs the genetic algorithm and writes the best ambulance positions back
    # to graph.ambulancePositions. Returns the same list for convenience.
    accessibleNodes = graph.getAccessibleNodes()

    if len(accessibleNodes) < NUM_AMBULANCES:
        graph.ambulancePositions = list(accessibleNodes)
        return graph.ambulancePositions

    # Step 1: build the initial random population
    population = []
    for _ in range(POPULATION_SIZE):
        population.append(randomChromosome(graph))

    bestChromosome = None
    bestFitness    = float('inf')

    # Fitness cache: elitism keeps top parents across generations, so without
    # caching we would re-run Dijkstra on the same chromosome repeatedly. The
    # key is the sorted tuple of positions so [(2,3),(7,1)] and [(7,1),(2,3)]
    # share an entry.
    fitnessCache = {}

    for generation in range(NUM_GENERATIONS):
        # Step 2: score every chromosome (with caching)
        scored = []
        for chromosome in population:
            cacheKey = tuple(sorted(chromosome))
            if cacheKey not in fitnessCache:
                fitnessCache[cacheKey] = computeFitness(chromosome, graph)
            scored.append((fitnessCache[cacheKey], chromosome))

        scored.sort(key=fitnessOf)

        # Track the best-of-all-generations chromosome
        if scored[0][0] < bestFitness:
            bestFitness    = scored[0][0]
            bestChromosome = scored[0][1]

        # Step 3: elitism -- keep the top half as parents
        parents = []
        for fitnessValue, chromosome in scored[:NUM_PARENTS]:
            parents.append(chromosome)

        # Step 4: pair parents to produce children
        children = []
        for i in range(NUM_PARENTS):
            parentA = parents[i % NUM_PARENTS]
            parentB = parents[(i + 1) % NUM_PARENTS]
            child = crossover(parentA, parentB)
            child = fixDuplicates(child, graph)
            children.append(child)

        # Step 5: mutate the children
        mutatedChildren = []
        for child in children:
            mutatedChildren.append(mutate(child, graph))

        # Step 6: new generation = parents + mutated children
        population = parents + mutatedChildren

    graph.ambulancePositions = bestChromosome
    return graph.ambulancePositions
