import random

import csp
import mst
import crime
import ga
import astar


# Hard cap on extra steps the simulation may run past totalSteps to finish off
# any civilians that are still pending. Without this, an unreachable cycle
# could let the loop run indefinitely.
MAX_EXTRA_STEPS = 30


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
        # Re-bind to a fresh graph and clear all simulation-specific state.
        # Used by the controller when starting or resetting a simulation.
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
        # Run all pre-simulation modules in the required order.
        # Returns (cspSuccess, cspConflict, setupEvents).
        setupEvents = []

        # 1. Place buildings via CSP, with the live-modifiable rules
        self.cspSuccess, self.cspConflict = csp.runCSP(
            self.graph, self.buildingCounts,
            residentialHops=self.residentialHops,
            powerplantHops=self.powerplantHops,
            industrialAdjacencyRule=self.industrialAdjacencyRule,
        )

        # 2. Build the road network and designate the primary hospital/depot
        self.routeA, self.routeB, mstEvents = mst.buildRoadNetwork(self.graph)
        setupEvents.extend(mstEvents)

        # 3. Assign crime risk indices to every node
        crimeEvents = crime.runCrime(self.graph)
        setupEvents.extend(crimeEvents)

        # 3b. Deploy 10 police officers to the highest-risk nodes
        self.graph.policeOfficers = crime.deployPoliceOfficers(self.graph, count=10)
        setupEvents.append(
            f"[Crime] Deployed {len(self.graph.policeOfficers)} police officers to highest-risk nodes."
        )

        # 4. Place ambulances optimally via the Genetic Algorithm
        ga.runGA(self.graph)

        # 5. Initialise the A* router for the medical team
        self.routerState = astar.initRouter(self.graph)

        self.setupDone = True
        return (self.cspSuccess, self.cspConflict, setupEvents)

    def step(self):
        # Advance the simulation by one step.
        # Returns a list of event strings produced this step.
        # Stops once we reach totalSteps + MAX_EXTRA_STEPS as a hard safety cap.
        if self.currentStep >= self.totalSteps + MAX_EXTRA_STEPS:
            return []

        self.currentStep += 1
        events = []

        # 1. Random flood event
        if random.random() < self.floodProbability:
            floodEvent = self._tryFloodEdge()
            if floodEvent is not None:
                events.append(floodEvent)

        # 2. Move the medical team one cell along its current path
        routerEvent = astar.stepRouter(self.routerState, self.graph)
        if routerEvent is not None:
            events.append(f"[Step {self.currentStep}] {routerEvent}")

        # 3. Relocate any ambulance that is now sitting on an inaccessible node
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
        # Pick one random unblocked edge that connects two accessible nodes
        # and flood it. Returns the event string on success, None otherwise.

        # Build the list of valid candidates with a plain loop -- a beginner
        # can read this without thinking about generator expressions.
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

    # ------------------------------------------------------------------ #
    #  Getters                                                             #
    # ------------------------------------------------------------------ #

    def isFinished(self):
        # Within the 20-step budget the simulation is never finished.
        if self.currentStep < self.totalSteps:
            return False

        # Past the budget: keep going while civilians remain pending, but only
        # up to MAX_EXTRA_STEPS so an unreachable loop cannot block forever.
        if self.routerState is not None:
            pending = len(self.routerState.civilians) - self.routerState.currentTarget
            if pending > 0 and self.currentStep < self.totalSteps + MAX_EXTRA_STEPS:
                return False

        return True

    def getSummary(self):
        # Short end-of-simulation report shown in the event log.
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

        return (
            f"Simulation complete after {self.currentStep} steps.\n"
            f"Civilians reached: {reached}\n"
            f"Civilians skipped: {skipped}\n"
            f"Roads flooded: {len(self.floodedEdges)}\n"
            f"CSP result: {cspResult}"
        )
