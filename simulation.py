import random

import csp
import mst
import crime
import ga
import astar


# extra step cap
MAX_EXTRA_STEPS = 30

# risk shift settings
RISK_SHIFT_INTERVAL   = 5
RISK_SHIFT_NODE_COUNT = 3
RISK_SHIFT_AMOUNT     = 0.25


class Simulation:
    def __init__(self, graph, buildingCounts, floodProbability=0.30,
                 residentialHops=3, powerplantHops=2, industrialAdjacencyRule=True):
        self.graph                   = graph
        self.buildingCounts          = buildingCounts
        self.floodProbability        = floodProbability
        self.residentialHops         = residentialHops
        self.powerplantHops          = powerplantHops
        self.industrialAdjacencyRule = industrialAdjacencyRule

        self.totalSteps   = 20
        self.currentStep  = 0
        self.routerState  = None
        self.routeA       = []
        self.routeB       = []
        self.floodedEdges = []
        self.setupDone    = False
        self.cspSuccess   = False
        self.cspConflict  = None

    def rebuild(self, graph, buildingCounts, floodProbability,
                residentialHops=3, powerplantHops=2, industrialAdjacencyRule=True):
        # reset sim state
        self.graph                   = graph
        self.buildingCounts          = buildingCounts
        self.floodProbability        = floodProbability
        self.residentialHops         = residentialHops
        self.powerplantHops          = powerplantHops
        self.industrialAdjacencyRule = industrialAdjacencyRule

        self.totalSteps   = 20
        self.currentStep  = 0
        self.routerState  = None
        self.routeA       = []
        self.routeB       = []
        self.floodedEdges = []
        self.setupDone    = False
        self.cspSuccess   = False
        self.cspConflict  = None

    def setup(self):
        # run setup modules
        setupEvents = []

        # place buildings
        self.cspSuccess, self.cspConflict = csp.runCSP(
            self.graph, self.buildingCounts,
            residentialHops=self.residentialHops,
            powerplantHops=self.powerplantHops,
            industrialAdjacencyRule=self.industrialAdjacencyRule,
        )

        # build roads
        self.routeA, self.routeB, mstEvents = mst.buildRoadNetwork(self.graph)
        setupEvents.extend(mstEvents)

        # run crime
        crimeEvents = crime.runCrime(self.graph)
        setupEvents.extend(crimeEvents)

        # place police
        self.graph.policeOfficers = crime.deployPoliceOfficers(self.graph, count=10)
        setupEvents.append(
            f"[Crime] Deployed {len(self.graph.policeOfficers)} police officers to highest-risk nodes."
        )

        # run ga
        ga.runGA(self.graph)

        # init router
        self.routerState = astar.initRouter(self.graph)

        self.setupDone = True
        return (self.cspSuccess, self.cspConflict, setupEvents)

    def step(self):
        if self.currentStep >= self.totalSteps + MAX_EXTRA_STEPS:
            return []

        self.currentStep += 1
        events = []

        # flood check
        if random.random() < self.floodProbability:
            floodEvent = self._tryFloodEdge()
            if floodEvent is not None:
                events.append(floodEvent)

        # risk shift
        riskEvent = self._maybeShiftRisk()
        if riskEvent is not None:
            events.append(riskEvent)
            repositionEvents = self._greedyAmbulanceReposition()
            events.extend(repositionEvents)

        # move team
        routerEvent = astar.stepRouter(self.routerState, self.graph)
        if routerEvent is not None:
            events.append(f"[Step {self.currentStep}] {routerEvent}")

        # fix blocked ambulances
        for index in range(len(self.graph.ambulancePositions)):
            ambulance = self.graph.ambulancePositions[index]
            if not self.graph.nodes[ambulance]["accessible"]:
                neighbours = self.graph.getAccessibleNeighbours(ambulance)
                if len(neighbours) > 0:
                    newPos = neighbours[0]
                    self.graph.ambulancePositions[index] = newPos
                    events.append(
                        f"[Step {self.currentStep}] Ambulance at {ambulance} "
                        f"relocated to {newPos} -- node inaccessible."
                    )

        return events

    def _tryFloodEdge(self):
        # flood one open edge
        candidates = []
        for edge in self.graph.getAllEdges():
            nodeA, nodeB = edge
            if self.graph.isEdgeBlocked(nodeA, nodeB):
                continue
            if not self.graph.nodes[nodeA]["accessible"]:
                continue
            if not self.graph.nodes[nodeB]["accessible"]:
                continue
            candidates.append(edge)

        if len(candidates) == 0:
            return None

        chosenEdge = random.choice(candidates)
        nodeA, nodeB = chosenEdge

        self.graph.floodEdge(nodeA, nodeB)
        self.floodedEdges.append((nodeA, nodeB))

        return f"[Step {self.currentStep}] Road {nodeA}-{nodeB} flooded automatically."

    def _maybeShiftRisk(self):
        # shift risk on schedule
        if self.currentStep % RISK_SHIFT_INTERVAL != 0:
            return None

        candidates = []
        for node in self.graph.getAccessibleNodes():
            nodeType = self.graph.nodes[node]["type"]
            if nodeType != "Empty":
                candidates.append(node)

        if len(candidates) < RISK_SHIFT_NODE_COUNT:
            return None

        chosen = random.sample(candidates, RISK_SHIFT_NODE_COUNT)
        for node in chosen:
            oldRisk = self.graph.nodes[node]["riskIndex"]
            newRisk = min(oldRisk + RISK_SHIFT_AMOUNT, 3.0)
            self.graph.setRiskIndex(node, newRisk)

        return (
            f"[Step {self.currentStep}] Risk weights shifted: "
            f"{len(chosen)} nodes increased by {RISK_SHIFT_AMOUNT}. "
            f"Re-evaluating ambulance positions."
        )

    def _greedyAmbulanceReposition(self):
        positions = self.graph.ambulancePositions
        if len(positions) == 0:
            return []

        events = []

        for index in range(len(positions)):
            currentPos = positions[index]

            # skip other ambulances
            otherPositions = set()
            for otherIndex in range(len(positions)):
                if otherIndex != index:
                    otherPositions.add(positions[otherIndex])

            neighbours = self.graph.getAccessibleNeighbours(currentPos, builtOnly=True)

            # score current spot
            currentDist = ga.dijkstra(self.graph, currentPos)
            currentWorst = 0.0
            for node in self.graph.getAccessibleNodes():
                if currentDist[node] > currentWorst:
                    currentWorst = currentDist[node]

            bestNeighbour = None
            bestWorst     = currentWorst

            for neighbour in neighbours:
                if neighbour in otherPositions:
                    continue

                testDist  = ga.dijkstra(self.graph, neighbour)
                testWorst = 0.0
                for node in self.graph.getAccessibleNodes():
                    if testDist[node] > testWorst:
                        testWorst = testDist[node]

                if testWorst < bestWorst:
                    bestWorst     = testWorst
                    bestNeighbour = neighbour

            if bestNeighbour is not None:
                positions[index] = bestNeighbour
                events.append(
                    f"[Step {self.currentStep}] Ambulance at {currentPos} "
                    f"repositioned to {bestNeighbour} due to risk shift."
                )

        return events

    # getters

    def isFinished(self):
        if self.currentStep < self.totalSteps:
            return False

        if self.routerState is not None:
            pending = len(self.routerState.civilians) - self.routerState.currentTarget
            if pending > 0 and self.currentStep < self.totalSteps + MAX_EXTRA_STEPS:
                return False

        return True

    def getSummary(self):
        if self.routerState is not None:
            reached = len(self.routerState.reached)
            skipped = len(self.routerState.skipped)
        else:
            reached = 0
            skipped = 0

        if self.cspSuccess:
            cspResult = "Success"
        else:
            cspResult = "Minimum conflict layout used"

        lines = []
        lines.append(f"Simulation complete after {self.currentStep} steps.")
        lines.append(f"Civilians reached: {reached}")
        lines.append(f"Civilians skipped: {skipped}")
        lines.append(f"Roads flooded: {len(self.floodedEdges)}")
        lines.append(f"CSP result: {cspResult}")
        return chr(10).join(lines)
