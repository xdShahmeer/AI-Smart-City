from cityGraph import CityGraph
from simulation import Simulation
from ui import AppUI
import pygame
import time


def main():
    graph = CityGraph(rows=10, cols=10)

    defaultBuildings = {
        "Hospital": 2, "School": 3, "Industrial": 4,
        "Residential": 15, "PowerPlant": 2, "AmbulanceDepot": 1
    }

    sim   = Simulation(graph, defaultBuildings, floodProbability=0.30)
    appUI = AppUI(graph, sim)
    appUI.setup()

    # Track when the last simulation step fired (for non-blocking auto-play)
    lastStepTime = [0.0]

    def onStartSimulation():
        settings = appUI.getSimSettings()

        graph.reset(rows=settings["gridSize"], cols=settings["gridSize"])
        sim.graph            = graph
        sim.buildingCounts   = settings["buildings"]
        sim.floodProbability = settings["floodProbability"]

        # Give visual feedback before the blocking setup call
        appUI.addLog("Setting up city... (CSP, MST, crime, GA, A*)")
        appUI.updateTk()

        success, conflictInfo = sim.setup()

        if success:
            appUI.addLog("CSP: valid city layout placed.")
        else:
            appUI.addLog(f"CSP: {conflictInfo}")

        appUI.addLog(f"Ambulances placed at: {graph.ambulancePositions}")
        appUI.eventLog.addSeparator()
        lastStepTime[0] = time.time()

    def onStep():
        if sim.setupDone and not sim.isFinished():
            events = sim.step()
            for e in events:
                appUI.addLog(e)
            if sim.isFinished():
                appUI.addLog(sim.getSummary())
                appUI.eventLog.addSeparator()

    def onReset():
        settings = appUI.getSimSettings()
        graph.reset(rows=settings["gridSize"], cols=settings["gridSize"])
        sim.__init__(graph, settings["buildings"], settings["floodProbability"])
        appUI.autoPlaying = False
        lastStepTime[0]   = 0.0
        appUI.eventLog.clear()
        appUI.addLog("Simulation reset. Press Start to begin.")

    appUI.onStartSimulation = onStartSimulation
    appUI.onStep            = onStep
    appUI.onReset           = onReset

    appUI.addLog("CityMind started. Configure settings and press Start.")

    clock   = pygame.time.Clock()
    running = True

    while running:
        running = appUI.handleEvents()
        appUI.updateTk()

        # Non-blocking auto-play: fire a step only when the delay has elapsed
        if sim.setupDone and appUI.autoPlaying and not sim.isFinished():
            stepDelay = appUI.getSimSettings()["stepDelay"]
            now       = time.time()
            if now - lastStepTime[0] >= stepDelay:
                lastStepTime[0] = now
                events = sim.step()
                for e in events:
                    appUI.addLog(e)
                if sim.isFinished():
                    appUI.addLog(sim.getSummary())
                    appUI.eventLog.addSeparator()
                    appUI.autoPlaying = False

        appUI.render()
        clock.tick(30)

    pygame.quit()


if __name__ == "__main__":
    main()
