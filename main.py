from appController import AppController
from ui import AppUI


DEFAULT_BUILDINGS = {
    "Hospital":       2,
    "School":         3,
    "Industrial":     4,
    "Residential":    15,
    "PowerPlant":     2,
    "AmbulanceDepot": 1,
}


def main():
    controller = AppController(DEFAULT_BUILDINGS, gridSize=10, floodProbability=0.30)
    appUI      = AppUI(controller)

    # connect events to log
    controller.setEventListener(appUI.addLog)

    appUI.setup()
    appUI.run()


if __name__ == "__main__":
    main()
