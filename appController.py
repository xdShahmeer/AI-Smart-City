import time

from cityGraph import CityGraph
from simulation import Simulation
from ga import dijkstra


class AppController:
    """
    Mediates between the UI layer and the underlying simulation/graph.
    The UI talks only to the controller. The controller owns the city graph
    and the simulation object, and forwards reads/writes through one surface.
    """

    def __init__(self, defaultBuildings, gridSize=10, floodProbability=0.30):
        self._graph          = CityGraph(rows=gridSize, cols=gridSize)
        self._simulation     = Simulation(self._graph, defaultBuildings, floodProbability)
        self._defaultCounts  = dict(defaultBuildings)
        self._lastStepTime   = 0.0
        self._eventListener  = None

    # ------------------------------------------------------------------ #
    #  Simulation control                                                  #
    # ------------------------------------------------------------------ #

    def startSimulation(self, settings):
        # Rebuild the graph from current settings, then run the full setup
        # pipeline (CSP, MST, crime, GA, A*). Returns a list of log strings.
        gridSize         = settings["gridSize"]
        buildingCounts   = settings["buildings"]
        floodProbability = settings["floodProbability"]
        residentialHops  = settings.get("residentialHops", 3)
        powerplantHops   = settings.get("powerplantHops", 2)

        self._graph.reset(rows=gridSize, cols=gridSize)
        self._simulation.rebuild(
            self._graph, buildingCounts, floodProbability,
            residentialHops=residentialHops,
            powerplantHops=powerplantHops,
        )

        logs = []
        logs.append("Setting up city... (CSP, MST, crime, GA, A*)")

        success, conflictInfo = self._simulation.setup()
        if success:
            logs.append("CSP: valid city layout placed.")
        else:
            logs.append(f"CSP: {conflictInfo}")

        logs.append(f"Ambulances placed at: {self._graph.ambulancePositions}")

        self._lastStepTime = time.time()
        return logs

    def stepSimulation(self):
        # Advance one step manually. Returns the events generated.
        if not self._simulation.setupDone or self._simulation.isFinished():
            return []

        events = self._simulation.step()
        if self._simulation.isFinished():
            events.append(self._simulation.getSummary())

        self._emitEvents(events)
        return events

    def autoStepIfDue(self, stepDelay):
        # Called from the main loop while auto-play is on.
        # Fires a step only when stepDelay seconds have passed since the last one.
        if not self._simulation.setupDone or self._simulation.isFinished():
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
        # Wipe graph state and re-create the simulation in a clean state.
        gridSize         = settings["gridSize"]
        buildingCounts   = settings["buildings"]
        floodProbability = settings["floodProbability"]
        residentialHops  = settings.get("residentialHops", 3)
        powerplantHops   = settings.get("powerplantHops", 2)

        self._graph.reset(rows=gridSize, cols=gridSize)
        self._simulation.rebuild(
            self._graph, buildingCounts, floodProbability,
            residentialHops=residentialHops,
            powerplantHops=powerplantHops,
        )
        self._lastStepTime = 0.0

    # ------------------------------------------------------------------ #
    #  Event subscription                                                  #
    # ------------------------------------------------------------------ #

    def _emitEvents(self, events):
        if self._eventListener is None:
            return
        for entry in events:
            self._eventListener(entry)

    # ------------------------------------------------------------------ #
    #  Manual interaction (flood tool, emergency tool)                     #
    # ------------------------------------------------------------------ #

    def floodEdge(self, nodeA, nodeB):
        # Used by the manual flood tool. Validates both endpoints share an edge,
        # the edge is unblocked, and the simulation is set up. Returns an event
        # string on success, None on a no-op.
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
        # Used by the emergency tool. Appends a node to the medical team's
        # civilian queue so the A* router will route there in turn.
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

        # Simulation.isFinished() automatically extends the run while there
        # are pending civilians, so we just need to let auto-play resume on
        # the next tick.
        self._lastStepTime = 0.0

        return f"Manual emergency: civilian added at {node}."

    def getActiveEmergencies(self):
        # Civilians the medical team has not yet reached or skipped.
        state = self._simulation.routerState
        if state is None:
            return []
        return list(state.civilians[state.currentTarget:])

    def getCoverageDistances(self):
        # Multi-source weighted Dijkstra: for every node, the minimum weighted
        # distance to any ambulance. Mirrors the metric the GA fitness uses.
        sources = list(self._graph.ambulancePositions)
        if not sources:
            return {}

        result = {node: float('inf') for node in self._graph.nodes}
        for source in sources:
            distMap = dijkstra(self._graph, source)
            for node, d in distMap.items():
                if d < result[node]:
                    result[node] = d
        return result

    # ------------------------------------------------------------------ #
    #  Node info for the side panel                                        #
    # ------------------------------------------------------------------ #

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

    # ------------------------------------------------------------------ #
    #  Getters / setters                                                   #
    # ------------------------------------------------------------------ #

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
