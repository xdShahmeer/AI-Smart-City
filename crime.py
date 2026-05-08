from collections import deque

import numpy as np
from sklearn.cluster import KMeans
from sklearn.neighbors import KNeighborsClassifier


# Maps predicted risk label to the riskIndex multiplier written into the graph
RISK_INDEX_MAP = {
    "High":   2.5,
    "Medium": 1.75,
    "Low":    1.25,
}


def getProximityToIndustrial(graph, node):
    # BFS from node -- count hops to the nearest Industrial node
    # Uses getNeighbours (all neighbours, no accessibility filter) because
    # this runs during the layout phase before simulation starts
    industrial = set(graph.getNodesByType("Industrial"))

    if not industrial:
        # No industrial zones exist -- return a large default distance
        return graph.rows + graph.cols

    visited = {node}
    queue = deque([(node, 0)])

    while queue:
        current, hops = queue.popleft()
        if current in industrial:
            return hops
        for neighbour in graph.getNeighbours(current):
            if neighbour not in visited:
                visited.add(neighbour)
                queue.append((neighbour, hops + 1))

    # Industrial nodes exist but are somehow unreachable -- return max distance
    return graph.rows + graph.cols


def extractFeatures(graph):
    # Returns ordered list of nodes and matching numpy feature array
    allNodes = graph.getAllNodes()
    features = []

    for node in allNodes:
        pop = graph.nodes[node]["population"]
        proximity = getProximityToIndustrial(graph, node)
        features.append([pop, proximity])

    return allNodes, np.array(features, dtype=float)


def runKMeans(X):
    # Fit K-Means with k=3 and return cluster labels and cluster centres
    model = KMeans(n_clusters=3, random_state=42, n_init=10)
    model.fit(X)
    return model.labels_, model.cluster_centers_


def assignClusterRiskLabels(clusterCentres):
    # Decide which cluster id maps to High / Medium / Low
    # High = highest population density (index 0 in centre vector)
    # Low  = lowest population density
    # Medium = the remaining one
    # Population density is feature index 0
    popByCluster = {i: centre[0] for i, centre in enumerate(clusterCentres)}

    sortedByPop = sorted(popByCluster, key=lambda i: popByCluster[i], reverse=True)
    highCluster   = sortedByPop[0]
    lowCluster    = sortedByPop[2]
    mediumCluster = sortedByPop[1]

    clusterToLabel = {
        highCluster:   "High",
        mediumCluster: "Medium",
        lowCluster:    "Low",
    }
    return clusterToLabel


def generateSyntheticLabels(X):
    # Score each node with the formula, normalise to [0,1], apply thresholds
    # score = (pop * 0.6) + ((1 / (proximity + 1)) * 0.4)
    scores = (X[:, 0] * 0.6) + ((1.0 / (X[:, 1] + 1)) * 0.4)

    maxScore = scores.max()
    if maxScore == 0:
        # Degenerate case -- everything is zero, treat all as Low
        normScores = scores
    else:
        normScores = scores / maxScore

    labels = []
    for s in normScores:
        if s > 0.66:
            labels.append("High")
        elif s > 0.33:
            labels.append("Medium")
        else:
            labels.append("Low")

    return labels


def trainKNN(X, labels):
    # Train KNN classifier (k=5) on the full synthetic dataset
    model = KNeighborsClassifier(n_neighbors=5)
    model.fit(X, labels)
    return model


def runCrime(graph):
    # Stage 1 and Stage 2 pipeline: cluster nodes, generate synthetic labels,
    # train KNN, predict risk for every node, write riskIndex back to graph.

    allNodes, X = extractFeatures(graph)

    # Stage 1 -- K-Means clustering (educational demonstration)
    clusterLabels, clusterCentres = runKMeans(X)
    clusterToLabel = assignClusterRiskLabels(clusterCentres)

    # Build the K-Means label list (used for logging/inspection if needed)
    kmeansLabels = [clusterToLabel[label] for label in clusterLabels]

    # Stage 2 -- Generate synthetic labels using the scoring formula
    syntheticLabels = generateSyntheticLabels(X)

    # Train KNN on the synthetic dataset, then predict for all nodes
    knn = trainKNN(X, syntheticLabels)
    predictions = knn.predict(X)

    # Write riskIndex back into the graph for every node
    for node, predictedLabel in zip(allNodes, predictions):
        graph.setRiskIndex(node, RISK_INDEX_MAP[predictedLabel])
