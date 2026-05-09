import random

import csp
import mst
import crime
import ga
import astar


# Hard cap on extra steps the simulation may run past totalSteps to finish off
# any civilians that are still pending. Without this, an unreachable chain of
# events could let the loop run indefinitely.
MAX_EXTRA_STEPS = 30


class Simulation:
    def __init__(self, graph, buildingCounts, floodProbability=0.30,
                 residentialHops=3, powerplantHops=2):
        self.graph            = graph
        self.buildingCounts   = buildingCounts
        self.floodProbability = floodProbability
        self.residentialHops  = residentialHops
        self.powerplantHops   = powerplantHops
        self.totalSteps       = 20
        self.currentStep      = 0
        self.routerState      = None  # created by initRouter during setup
        self.routeA           = []    # primary emergency corridor edges
        self.routeB           = []    # backup emergency corridor edges
        self.floodedEdges     = []    # (nodeA, nodeB) tuples flooded this simulation
        self.setupDone        = False
        self.cspSuccess       = False
        self.cspConflict      = None

    def rebuild(self, graph, buildingCounts, floodProbability,
                residentialHops=3, powerplantHops=2):
        # Re-bind to a fresh graph and clear all simulation-specific state.
        # Used by the controller when starting or resetting a simulation.
        self.graph            = graph
        self.buildingCounts   = buildingCounts
        self.floodProbability = floodProbability
        self.residentialHops  = residentialHops
        self.powerplantHops   = powerplantHops
        self.totalSteps       = 20
        self.currentStep      = 0
        self.routerState      = None
        self.routeA           = []
        self.routeB           = []
        self.floodedEdges     = []
        self.setupDone        = False
        self.cspSuccess       = False
        self.cspConflict      = None

    def setup(self):
        # Run all pre-simulation modules in the required order.
        # Returns (cspSuccess, cspConflict).

        # 1. Place buildings via CSP, with the live-modifiable proximity hops
        self.cspSuccess, self.cspConflict = csp.runCSP(
            self.graph, self.buildingCounts,
            residentialHops=self.residentialHops,
            powerplantHops=self.powerplantHops,
        )

        # 2. Build road network and designate primary hospital/depot
        self.routeA, self.routeB = mst.buildRoadNetwork(self.graph)

        # 3. Assign crime risk indices to every node
        crime.runCrime(self.graph)

        # 4. Place ambulances optimally via GA
        ga.runGA(self.graph)

        # 5. Initialise the A* router for the medical team
        self.routerState = astar.initRouter(self.graph)

        self.setupDone = True
        return (self.cspSuccess, self.cspConflict)

    def step(self):
        # Advance the simulation by one step.
        # Returns a list of event strings generated this step.
        # Hard-stops once we go past the 20-step budget plus the extra-step cap.

        if self.currentStep >= self.totalSteps + MAX_EXTRA_STEPS:
            return []

        self.currentStep += 1
        events = []

        # 1. Random flood event
        if random.random() < self.floodProbability:
            floodEvent = self._tryFloodEdge()
            if floodEvent:
                events.append(floodEvent)

        # 2. Advance the medical team one cell
        routerEvent = astar.stepRouter(self.routerState, self.graph, None)
        if routerEvent is not None:
            events.append(f"[Step {self.currentStep}] {routerEvent}")

        # 3. Relocate any ambulance sitting on an inaccessible node
        for i, ambulance in enumerate(list(self.graph.ambulancePositions)):
            if not self.graph.nodes[ambulance]["accessible"]:
                neighbours = self.graph.getAccessibleNeighbours(ambulance)
                if neighbours:
                    newPos = neighbours[0]
                    self.graph.ambulancePositions[i] = newPos
                    events.append(
                        f"[Step {self.currentStep}] Ambulance at {ambulance} "
                        f"relocated to {newPos} -- node inaccessible."
                    )

        return events

    def _tryFloodEdge(self):
        # Pick one random accessible unblocked edge and flood it.
        # Returns an event string if successful, None otherwise.

        allEdges = self.graph.getAllEdges()

        # Only consider edges that are not already blocked and connect accessible nodes
        candidates = [
            (a, b) for a, b in allEdges
            if not self.graph.isEdgeBlocked(a, b)
            and self.graph.nodes[a]["accessible"]
            and self.graph.nodes[b]["accessible"]
        ]

        if not candidates:
            return None

        nodeA, nodeB = random.choice(candidates)
        self.graph.floodEdge(nodeA, nodeB)
        self.floodedEdges.append((nodeA, nodeB))

        return f"[Step {self.currentStep}] Road {nodeA}-{nodeB} flooded automatically."

    def autoRun(self, onStepCallback=None):
        # Run all remaining steps in sequence.
        # Calls onStepCallback(stepNum, events) after each step if provided.

        while not self.isFinished():
            events = self.step()
            if onStepCallback:
                onStepCallback(self.currentStep, events)

    # ------------------------------------------------------------------ #
    #  Getters                                                             #
    # ------------------------------------------------------------------ #

    def isFinished(self):
        # Within the 20-step budget the sim is never finished.
        if self.currentStep < self.totalSteps:
            return False

        # Past the budget: stay alive while the team still has civilians
        # to handle (manual or initial unreached). Capped at MAX_EXTRA_STEPS
        # so an unreachable cycle cannot block forever -- stepRouter already
        # marks unreachable civilians as skipped on the next step.
        if self.routerState is not None:
            pending = len(self.routerState.civilians) - self.routerState.currentTarget
            if pending > 0 and self.currentStep < self.totalSteps + MAX_EXTRA_STEPS:
                return False

        return True

    def getSummary(self):
        # Returns a short end-of-simulation report string.
        reached = len(self.routerState.reached) if self.routerState else 0
        skipped = len(self.routerState.skipped) if self.routerState else 0

        cspResult = "Success" if self.cspSuccess else "Minimum conflict layout used"

        return (
            f"Simulation complete after {self.currentStep} steps.\n"
            f"Civilians reached: {reached}\n"
            f"Civilians skipped: {skipped}\n"
            f"Roads flooded: {len(self.floodedEdges)}\n"
            f"CSP result: {cspResult}"
        )
