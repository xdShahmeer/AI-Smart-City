import time

from cityGraph import CityGraph
from simulation import Simulation
from ga import dijkstra


class AppController:
    # ui talks only to this class

    def __init__(self, defaultBuildings, gridSize=10, floodProbability=0.30):
        self._graph         = CityGraph(rows=gridSize, cols=gridSize)
        self._simulation    = Simulation(self._graph, defaultBuildings, floodProbability)
        self._defaultCounts = dict(defaultBuildings)
        self._lastStepTime  = 0.0
        self._eventListener = None

    # simulation control

    def startSimulation(self, settings):
        # rebuild graph then run setup
        gridSize             = settings["gridSize"]
        buildingCounts       = settings["buildings"]
        floodProbability     = settings["floodProbability"]
        residentialHops      = settings.get("residentialHops", 3)
        powerplantHops       = settings.get("powerplantHops", 2)
        industrialAdjacency  = settings.get("industrialAdjacencyRule", True)

        self._graph.reset(rows=gridSize, cols=gridSize)
        self._simulation.rebuild(
            self._graph, buildingCounts, floodProbability,
            residentialHops=residentialHops,
            powerplantHops=powerplantHops,
            industrialAdjacencyRule=industrialAdjacency,
        )

        logs = []
        logs.append("Setting up city... (CSP, MST, crime, GA, A*)")

        success, conflictInfo, setupEvents = self._simulation.setup()
        if success:
            logs.append("CSP: valid city layout placed.")
        else:
            logs.append(f"CSP: {conflictInfo}")

        # setup logs come back as lines
        for entry in setupEvents:
            logs.append(entry)

        logs.append(f"Ambulances placed at: {self._graph.ambulancePositions}")

        self._lastStepTime = time.time()
        return logs

    def stepSimulation(self):
        if not self._simulation.setupDone:
            return []
        if self._simulation.isFinished():
            return []

        events = self._simulation.step()
        if self._simulation.isFinished():
            events.append(self._simulation.getSummary())

        self._emitEvents(events)
        return events

    def autoStepIfDue(self, stepDelay):
        if not self._simulation.setupDone:
            return []
        if self._simulation.isFinished():
            return []

        now = time.time()
        if now - self._lastStepTime < stepDelay:
            return []

        self._lastStepTime = now
        events = self._simulation.step()
        if self._simulation.isFinished():
            events.append(self._simulation.getSummary())

        self._emitEvents(events)
        return events

    def resetSimulation(self, settings):
        # reset graph and sim
        gridSize             = settings["gridSize"]
        buildingCounts       = settings["buildings"]
        floodProbability     = settings["floodProbability"]
        residentialHops      = settings.get("residentialHops", 3)
        powerplantHops       = settings.get("powerplantHops", 2)
        industrialAdjacency  = settings.get("industrialAdjacencyRule", True)

        self._graph.reset(rows=gridSize, cols=gridSize)
        self._simulation.rebuild(
            self._graph, buildingCounts, floodProbability,
            residentialHops=residentialHops,
            powerplantHops=powerplantHops,
            industrialAdjacencyRule=industrialAdjacency,
        )
        self._lastStepTime = 0.0

    # event subscription

    def _emitEvents(self, events):
        if self._eventListener is None:
            return
        for entry in events:
            self._eventListener(entry)

    # manual tools

    def floodEdge(self, nodeA, nodeB):
        if not self._simulation.setupDone:
            return None
        if nodeB not in self._graph.getNeighbours(nodeA):
            return None
        if self._graph.isEdgeBlocked(nodeA, nodeB):
            return None

        self._graph.floodEdge(nodeA, nodeB)
        self._simulation.floodedEdges.append((nodeA, nodeB))
        return f"Manual flood: road {nodeA}-{nodeB} blocked."

    def addEmergency(self, node):
        if not self._simulation.setupDone:
            return None

        state = self._simulation.routerState
        if state is None:
            return None
        if node == state.currentPos:
            return None
        if node in state.civilians:
            return None
        if not self._graph.nodes[node]["accessible"]:
            return None

        state.civilians.append(node)

        # let auto play keep going
        self._lastStepTime = 0.0

        return f"Manual emergency: civilian added at {node}."

    def getActiveEmergencies(self):
        state = self._simulation.routerState
        if state is None:
            return []
        return list(state.civilians[state.currentTarget:])

    def getCoverageDistances(self):
        sources = list(self._graph.ambulancePositions)
        if len(sources) == 0:
            return {}

        # start every node at infinity
        result = {}
        for node in self._graph.nodes:
            result[node] = float('inf')

        for source in sources:
            distanceMap = dijkstra(self._graph, source)
            for node in distanceMap:
                if distanceMap[node] < result[node]:
                    result[node] = distanceMap[node]

        return result

    # node info

    def getNodeInfo(self, node):
        if node not in self._graph.nodes:
            return None
        data = self._graph.nodes[node]
        return {
            "node":       node,
            "type":       data["type"],
            "population": data["population"],
            "riskIndex":  data["riskIndex"],
            "accessible": data["accessible"],
        }

    # getters and setters

    def getGraph(self):
        return self._graph

    def getSimulation(self):
        return self._simulation

    def getRouterState(self):
        return self._simulation.routerState

    def getRoutes(self):
        return (self._simulation.routeA, self._simulation.routeB)

    def getDefaultCounts(self):
        return dict(self._defaultCounts)

    def isSetupDone(self):
        return self._simulation.setupDone

    def isFinished(self):
        return self._simulation.isFinished()

    def setEventListener(self, callback):
        self._eventListener = callback
