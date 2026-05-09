from collections import deque

import numpy as np
from sklearn.cluster import KMeans
from sklearn.neighbors import KNeighborsClassifier


# Predicted risk level -> riskIndex multiplier written into the graph.
RISK_INDEX_MAP = {
    "High":   2.5,
    "Medium": 1.75,
    "Low":    1.25,
}

# Risk tiers in the order we want them displayed.
RISK_TIERS = ("High", "Medium", "Low")


# ── Feature extraction ───────────────────────────────────────────────────────

def getProximityToIndustrial(graph, node):
    # BFS from this node, count hops to the nearest Industrial node.
    # Uses getNeighbours (no accessibility filter) because this runs during
    # the layout phase, before any flooding takes place.
    industrialSet = set(graph.getNodesByType("Industrial"))

    # No industrial zones exist -- return a large default distance.
    if len(industrialSet) == 0:
        return graph.rows + graph.cols

    visited = {node}
    queue   = deque()
    queue.append((node, 0))

    while queue:
        current, hops = queue.popleft()

        if current in industrialSet:
            return hops

        for neighbour in graph.getNeighbours(current):
            if neighbour not in visited:
                visited.add(neighbour)
                queue.append((neighbour, hops + 1))

    # Industrial zones exist but are somehow unreachable from this node.
    return graph.rows + graph.cols


def extractFeatures(graph):
    # Returns the ordered list of nodes and a numpy array of features.
    # Each row is [population, proximityToIndustrial].
    allNodes = graph.getAllNodes()

    featureRows = []
    for node in allNodes:
        population = graph.nodes[node]["population"]
        proximity  = getProximityToIndustrial(graph, node)
        featureRows.append([population, proximity])

    return allNodes, np.array(featureRows, dtype=float)


# ── Stage 1: K-Means clustering (unsupervised) ────────────────────────────────

def runKMeans(featureMatrix):
    # Fit K-Means with k = 3 (one per risk tier).
    model = KMeans(n_clusters=3, random_state=42, n_init=10)
    model.fit(featureMatrix)
    return model.labels_, model.cluster_centers_


def assignClusterRiskLabels(clusterCentres):
    # Decide which cluster id maps to High / Medium / Low. The cluster with
    # the highest average population density is High, the lowest is Low,
    # the remaining one is Medium.

    # Build a list of (clusterId, populationDensity) so we can sort it.
    populationByCluster = []
    for clusterId in range(len(clusterCentres)):
        populationDensity = clusterCentres[clusterId][0]
        populationByCluster.append((clusterId, populationDensity))

    # Sort highest-population first (descending).
    populationByCluster.sort(key=getClusterPopulation, reverse=True)

    highCluster   = populationByCluster[0][0]
    mediumCluster = populationByCluster[1][0]
    lowCluster    = populationByCluster[2][0]

    clusterToLabel = {
        highCluster:   "High",
        mediumCluster: "Medium",
        lowCluster:    "Low",
    }
    return clusterToLabel


def getClusterPopulation(clusterEntry):
    # Helper used by sort() above; replaces a lambda for clarity.
    return clusterEntry[1]


# ── Stage 2: synthetic dataset generation ─────────────────────────────────────

def generateSyntheticLabels(featureMatrix):
    # Score each node with the formula, normalise to [0, 1], apply thresholds.
    # score = (population * 0.6) + (proximityWeight * 0.4)
    # where proximityWeight = 1 / (proximityToIndustrial + 1) so closer-to-
    # Industrial nodes score higher.
    populationColumn = featureMatrix[:, 0]
    proximityColumn  = featureMatrix[:, 1]

    proximityWeight = 1.0 / (proximityColumn + 1.0)
    rawScores       = (populationColumn * 0.6) + (proximityWeight * 0.4)

    maxScore = rawScores.max()
    if maxScore == 0:
        # Degenerate case -- everything is zero, label everything Low.
        normalisedScores = rawScores
    else:
        normalisedScores = rawScores / maxScore

    labels = []
    for score in normalisedScores:
        if score > 0.66:
            labels.append("High")
        elif score > 0.33:
            labels.append("Medium")
        else:
            labels.append("Low")

    return labels


# ── Stage 3: KNN classifier (supervised) ──────────────────────────────────────

def trainKNN(featureMatrix, labels):
    model = KNeighborsClassifier(n_neighbors=5)
    model.fit(featureMatrix, labels)
    return model


# ── Cross-validation between Stage 1 and Stage 2 ──────────────────────────────

def countAgreement(kmeansLabels, syntheticLabels):
    # How many positions have the same label in both lists?
    agreeCount = 0
    for index in range(len(kmeansLabels)):
        if kmeansLabels[index] == syntheticLabels[index]:
            agreeCount += 1
    return agreeCount


def countByTier(labelList):
    # Plain loop in place of a dict comprehension. Returns counts in
    # tier order: High first, then Medium, then Low.
    counts = {}
    for tier in RISK_TIERS:
        counts[tier] = 0
    for label in labelList:
        if label in counts:
            counts[label] += 1
    return counts


# ── Pipeline entry point ──────────────────────────────────────────────────────

def runCrime(graph):
    # Stage 1 -> Stage 2 -> Stage 3 pipeline:
    #   Stage 1 (unsupervised)  -- K-Means discovers natural risk clusters.
    #   Stage 2 (synthetic data) -- formula assigns High/Medium/Low per node.
    #   Stage 3 (supervised)    -- KNN trains on Stage 2 labels and predicts.
    # K-Means is then cross-checked against the formula labels and the result
    # is logged so the unsupervised step has a visible role.
    # Returns a list of event strings for the caller to forward to the UI.
    events = []

    allNodes, featureMatrix = extractFeatures(graph)

    # Stage 1
    clusterLabels, clusterCentres = runKMeans(featureMatrix)
    clusterToLabel                = assignClusterRiskLabels(clusterCentres)

    kmeansLabels = []
    for clusterId in clusterLabels:
        kmeansLabels.append(clusterToLabel[clusterId])

    # Stage 2
    syntheticLabels = generateSyntheticLabels(featureMatrix)

    # Cross-validation log entries
    if len(kmeansLabels) > 0:
        agreeCount = countAgreement(kmeansLabels, syntheticLabels)
        percentage = agreeCount / len(kmeansLabels) * 100
        events.append(
            f"[Crime] K-Means agrees with formula labels on {percentage:.1f}% of nodes."
        )

        clusterCounts = countByTier(kmeansLabels)
        events.append(
            f"[Crime] K-Means clusters: "
            f"High={clusterCounts['High']}, "
            f"Medium={clusterCounts['Medium']}, "
            f"Low={clusterCounts['Low']}."
        )

    # Stage 3
    knn         = trainKNN(featureMatrix, syntheticLabels)
    predictions = knn.predict(featureMatrix)

    # Write the predicted risk index back into the graph for every node
    for index in range(len(allNodes)):
        node           = allNodes[index]
        predictedLabel = predictions[index]
        graph.setRiskIndex(node, RISK_INDEX_MAP[predictedLabel])

    return events


# ── Police officer deployment ─────────────────────────────────────────────────

def riskIndexFor(graph, node):
    # Helper used by sort() to replace a lambda.
    return graph.nodes[node]["riskIndex"]


def deployPoliceOfficers(graph, count=10):
    # Greedy top-`count` placement: highest predicted risk goes first.
    # Reflects the project statement framing of allocating 10 officers to the
    # neighborhoods most likely to need them.

    # We need a partial sort by riskIndex descending. The standard library
    # sort with a small named helper is the simplest readable approach.
    allNodes = graph.getAllNodes()
    sortedByRisk = list(allNodes)

    def riskKey(node):
        return graph.nodes[node]["riskIndex"]

    sortedByRisk.sort(key=riskKey, reverse=True)

    return sortedByRisk[:count]
