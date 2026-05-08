import heapq
import random


# GA parameters
POPULATION_SIZE = 20
NUM_GENERATIONS  = 30
MUTATION_RATE    = 0.10
NUM_AMBULANCES   = 3
NUM_PARENTS      = POPULATION_SIZE // 2  # top 10 kept each generation


def dijkstra(graph, source):
    # Shortest weighted distances from source to all other nodes.
    # Uses graph.getAccessibleNeighbours and graph.getWeightedCost.
    # Nodes that cannot be reached stay at infinity.
    dist = {node: float('inf') for node in graph.nodes}
    dist[source] = 0.0

    heap = [(0.0, source)]

    while heap:
        currentDist, node = heapq.heappop(heap)

        # Skip if we already found a better path
        if currentDist > dist[node]:
            continue

        for neighbour in graph.getAccessibleNeighbours(node):
            cost = graph.getWeightedCost(node, neighbour)
            newDist = currentDist + cost
            if newDist < dist[neighbour]:
                dist[neighbour] = newDist
                heapq.heappush(heap, (newDist, neighbour))

    return dist


def fitness(chromosome, graph):
    # Worst-case response time: the maximum distance from any accessible node
    # to its nearest ambulance. Lower is better.
    accessibleNodes = graph.getAccessibleNodes()

    # Run Dijkstra once from each ambulance position
    distMaps = [dijkstra(graph, pos) for pos in chromosome]

    worstCase = 0.0
    for node in accessibleNodes:
        # Distance from this node to the nearest ambulance
        nearestDist = min(distMap[node] for distMap in distMaps)
        if nearestDist > worstCase:
            worstCase = nearestDist

    return worstCase


def randomChromosome(graph):
    # Pick 3 distinct accessible nodes at random
    accessibleNodes = graph.getAccessibleNodes()
    return random.sample(accessibleNodes, NUM_AMBULANCES)


def crossover(parentA, parentB):
    # Split at a random point and combine the two parents
    splitPoint = random.randint(1, NUM_AMBULANCES - 1)
    child = parentA[:splitPoint] + parentB[splitPoint:]
    return child


def fixDuplicates(chromosome, graph):
    # Replace any duplicate positions with unique random accessible nodes
    accessibleNodes = graph.getAccessibleNodes()
    # Pre-collect all unique positions so we know what's already claimed
    allPositions = set(chromosome)
    seen = set()
    fixed = []

    for pos in chromosome:
        if pos not in seen:
            seen.add(pos)
            fixed.append(pos)
        else:
            # This is a duplicate -- pick a replacement not in allPositions
            candidates = [n for n in accessibleNodes if n not in allPositions]
            if candidates:
                replacement = random.choice(candidates)
                allPositions.add(replacement)
                seen.add(replacement)
                fixed.append(replacement)
            else:
                fixed.append(pos)  # fallback: keep duplicate if no fresh nodes available

    return fixed


def mutate(chromosome, graph):
    # With MUTATION_RATE probability, replace one position with a fresh random node
    if random.random() < MUTATION_RATE:
        accessibleNodes = graph.getAccessibleNodes()
        indexToMutate = random.randrange(NUM_AMBULANCES)

        # Pick a node not already in the chromosome
        current = set(chromosome)
        candidates = [n for n in accessibleNodes if n not in current]

        if candidates:
            chromosome[indexToMutate] = random.choice(candidates)

    return chromosome


def runGA(graph):
    # Runs the genetic algorithm and writes the best ambulance positions to the graph.
    # Returns graph.ambulancePositions.

    accessibleNodes = graph.getAccessibleNodes()

    # Need at least 3 accessible nodes to place ambulances
    if len(accessibleNodes) < NUM_AMBULANCES:
        graph.ambulancePositions = accessibleNodes[:len(accessibleNodes)]
        return graph.ambulancePositions

    # Step 1: generate initial population
    population = [randomChromosome(graph) for _ in range(POPULATION_SIZE)]

    bestChromosome = None
    bestFitness    = float('inf')

    for generation in range(NUM_GENERATIONS):
        # Step 2: evaluate fitness for all chromosomes
        scored = [(fitness(chrom, graph), chrom) for chrom in population]

        # Track the overall best across all generations
        scored.sort(key=lambda x: x[0])
        if scored[0][0] < bestFitness:
            bestFitness    = scored[0][0]
            bestChromosome = scored[0][1]

        # Step 3: elitism -- keep the top half as parents
        parents = [chrom for _, chrom in scored[:NUM_PARENTS]]

        # Step 4: crossover -- pair parents sequentially to produce children.
        # We need NUM_PARENTS children. Wrap around if we run out of pairs.
        children = []
        for i in range(NUM_PARENTS):
            parentA = parents[i % NUM_PARENTS]
            parentB = parents[(i + 1) % NUM_PARENTS]
            child = crossover(parentA, parentB)
            child = fixDuplicates(child, graph)
            children.append(child)

        # Step 5: mutate children
        children = [mutate(child, graph) for child in children]

        # Step 6: new generation = parents + children
        population = parents + children

    # Use the best chromosome found across all generations
    graph.ambulancePositions = bestChromosome
    return graph.ambulancePositions
