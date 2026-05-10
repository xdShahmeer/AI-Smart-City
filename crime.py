from collections import deque

import numpy as np
from sklearn.cluster import KMeans
from sklearn.neighbors import KNeighborsClassifier


# risk index map
RISK_INDEX_MAP = {
    "High":   2.5,
    "Medium": 1.75,
    "Low":    1.25,
}

# risk tier order
RISK_TIERS = ("High", "Medium", "Low")


# feature extraction

def getProximityToIndustrial(graph, node):
    industrialSet = set(graph.getNodesByType("Industrial"))

    # no industrial nodes
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

    # no path found
    return graph.rows + graph.cols


def extractFeatures(graph):
    allNodes = graph.getAllNodes()

    featureRows = []
    for node in allNodes:
        population = graph.nodes[node]["population"]
        proximity  = getProximityToIndustrial(graph, node)
        featureRows.append([population, proximity])

    return allNodes, np.array(featureRows, dtype=float)


# stage 1 k means

def runKMeans(featureMatrix):
    model = KMeans(n_clusters=3, random_state=42, n_init=10)
    model.fit(featureMatrix)
    return model.labels_, model.cluster_centers_


def assignClusterRiskLabels(clusterCentres):
    # map clusters to labels
    populationByCluster = []
    for clusterId in range(len(clusterCentres)):
        populationDensity = clusterCentres[clusterId][0]
        populationByCluster.append((clusterId, populationDensity))

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
    return clusterEntry[1]


# stage 2 synthetic labels

def generateSyntheticLabels(featureMatrix):
    populationColumn = featureMatrix[:, 0]
    proximityColumn  = featureMatrix[:, 1]

    proximityWeight = 1.0 / (proximityColumn + 1.0)
    rawScores       = (populationColumn * 0.6) + (proximityWeight * 0.4)

    maxScore = rawScores.max()
    if maxScore == 0:
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


# stage 3 knn

def trainKNN(featureMatrix, labels):
    model = KNeighborsClassifier(n_neighbors=5)
    model.fit(featureMatrix, labels)
    return model


# stage compare

def countAgreement(kmeansLabels, syntheticLabels):
    agreeCount = 0
    for index in range(len(kmeansLabels)):
        if kmeansLabels[index] == syntheticLabels[index]:
            agreeCount += 1
    return agreeCount


def countByTier(labelList):
    counts = {}
    for tier in RISK_TIERS:
        counts[tier] = 0
    for label in labelList:
        if label in counts:
            counts[label] += 1
    return counts


# pipeline entry

def runCrime(graph):
    # run the full risk pipeline
    events = []

    allNodes, featureMatrix = extractFeatures(graph)

    # stage 1
    clusterLabels, clusterCentres = runKMeans(featureMatrix)
    clusterToLabel                = assignClusterRiskLabels(clusterCentres)

    kmeansLabels = []
    for clusterId in clusterLabels:
        kmeansLabels.append(clusterToLabel[clusterId])

    # stage 2
    syntheticLabels = generateSyntheticLabels(featureMatrix)

    # compare stages
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

    # stage 3
    knn         = trainKNN(featureMatrix, syntheticLabels)
    predictions = knn.predict(featureMatrix)

    # write risk back to graph
    for index in range(len(allNodes)):
        node           = allNodes[index]
        predictedLabel = predictions[index]
        graph.setRiskIndex(node, RISK_INDEX_MAP[predictedLabel])

    return events


# police deployment

def riskIndexFor(graph, node):
    return graph.nodes[node]["riskIndex"]


def deployPoliceOfficers(graph, count=10):
    # pick top risk nodes
    allNodes = graph.getAllNodes()
    sortedByRisk = list(allNodes)

    def riskKey(node):
        return graph.nodes[node]["riskIndex"]

    sortedByRisk.sort(key=riskKey, reverse=True)

    return sortedByRisk[:count]
