import heapq
import random


# ga params
POPULATION_SIZE = 30
NUM_GENERATIONS = 60
MUTATION_RATE   = 0.10
NUM_AMBULANCES  = 3
NUM_PARENTS     = POPULATION_SIZE // 2


# dijkstra helper

def dijkstra(graph, source):
    distance = {}
    for node in graph.nodes:
        distance[node] = float('inf')
    distance[source] = 0.0

    heap = []
    heapq.heappush(heap, (0.0, source))

    while heap:
        currentDist, node = heapq.heappop(heap)

        # skip stale entries
        if currentDist > distance[node]:
            continue

        for neighbour in graph.getAccessibleNeighbours(node, builtOnly=True):
            edgeCost = graph.getWeightedCost(node, neighbour)
            newDist  = currentDist + edgeCost
            if newDist < distance[neighbour]:
                distance[neighbour] = newDist
                heapq.heappush(heap, (newDist, neighbour))

    return distance


# fitness helper

def computeFitness(chromosome, graph):
    accessibleNodes = graph.getAccessibleNodes()

    # one dijkstra map per ambulance
    distanceMaps = []
    for ambulancePos in chromosome:
        distanceMaps.append(dijkstra(graph, ambulancePos))

    worstCase = 0.0
    for node in accessibleNodes:
        # nearest ambulance wins
        nearestDist = float('inf')
        for distanceMap in distanceMaps:
            if distanceMap[node] < nearestDist:
                nearestDist = distanceMap[node]

        if nearestDist > worstCase:
            worstCase = nearestDist

    return worstCase


# population helpers

def randomChromosome(graph):
    accessibleNodes = graph.getAccessibleNodes()
    return random.sample(accessibleNodes, NUM_AMBULANCES)


def crossover(parentA, parentB):
    splitPoint = random.randint(1, NUM_AMBULANCES - 1)
    child = parentA[:splitPoint] + parentB[splitPoint:]
    return child


def fixDuplicates(chromosome, graph):
    accessibleNodes = graph.getAccessibleNodes()
    alreadyUsed     = set(chromosome)
    seen            = set()
    fixed           = []

    for position in chromosome:
        if position not in seen:
            seen.add(position)
            fixed.append(position)
            continue

        # replace duplicate
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


# sorting helper

def fitnessOf(scoredEntry):
    return scoredEntry[0]


# main ga loop

def runGA(graph):
    accessibleNodes = graph.getAccessibleNodes()

    if len(accessibleNodes) < NUM_AMBULANCES:
        graph.ambulancePositions = list(accessibleNodes)
        return graph.ambulancePositions

    # build initial population
    population = []
    for _ in range(POPULATION_SIZE):
        population.append(randomChromosome(graph))

    bestChromosome = None
    bestFitness    = float('inf')

    # cache fitness results
    fitnessCache = {}

    for generation in range(NUM_GENERATIONS):
        # score population
        scored = []
        for chromosome in population:
            cacheKey = tuple(sorted(chromosome))
            if cacheKey not in fitnessCache:
                fitnessCache[cacheKey] = computeFitness(chromosome, graph)
            scored.append((fitnessCache[cacheKey], chromosome))

        scored.sort(key=fitnessOf)

        # keep best so far
        if scored[0][0] < bestFitness:
            bestFitness    = scored[0][0]
            bestChromosome = scored[0][1]

        # keep top half
        parents = []
        for fitnessValue, chromosome in scored[:NUM_PARENTS]:
            parents.append(chromosome)

        # make children
        children = []
        for i in range(NUM_PARENTS):
            parentA = parents[i % NUM_PARENTS]
            parentB = parents[(i + 1) % NUM_PARENTS]
            child = crossover(parentA, parentB)
            child = fixDuplicates(child, graph)
            children.append(child)

        # mutate children
        mutatedChildren = []
        for child in children:
            mutatedChildren.append(mutate(child, graph))

        # next gen
        population = parents + mutatedChildren

    graph.ambulancePositions = bestChromosome
    return graph.ambulancePositions
