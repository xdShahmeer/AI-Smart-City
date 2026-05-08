import os
import pygame
import tkinter as tk
from collections import deque
from eventLog import EventLog


# Maps each building type to a tile filename (no extension) from the Kenney pack
SPRITE_TILES = {
    "Empty":          "tile_0000",   # green grass
    "Residential":    "tile_0072",   # brown brick house panel
    "Hospital":       "tile_0060",   # blue-grey checkered floor (clean/clinical)
    "School":         "tile_0074",   # stone arch facade
    "Industrial":     "tile_0048",   # dark stone floor (factory feel)
    "PowerPlant":     "tile_0096",   # grey castle stone (solid structure)
    "AmbulanceDepot": "tile_0084",   # gate/door frame (depot entrance)
}


# Pixels per grid cell
CELL_SIZE = 60

# Gap between cell edge and the filled building rectangle
MARGIN = 4

# Colour palette (hex strings, converted to RGB via hexToRgb)
COLOURS = {
    "bg":               "#1a1a2e",
    "Residential":      "#e8a87c",
    "Hospital":         "#e84040",
    "School":           "#4a90d9",
    "Industrial":       "#8b8b8b",
    "PowerPlant":       "#f0c040",
    "AmbulanceDepot":   "#a040e0",
    "Empty":            "#2d2d44",
    "road":             "#cccccc",
    "road_residential": "#f0e080",
    "road_flooded":     "#0080ff",
    "ambulance":        "#ffffff",
    "medicalTeam":      "#00ffcc",
    "routeA":           "#ff6600",
    "routeB":           "#00cc44",
}


def hexToRgb(hexStr):
    # Convert "#rrggbb" to (r, g, b) tuple
    hexStr = hexStr.lstrip("#")
    r = int(hexStr[0:2], 16)
    g = int(hexStr[2:4], 16)
    b = int(hexStr[4:6], 16)
    return (r, g, b)


def nodeCentre(node):
    # Pixel centre of a grid node (r, c)
    r, c = node
    x = c * CELL_SIZE + CELL_SIZE // 2
    y = r * CELL_SIZE + CELL_SIZE // 2
    return (x, y)


def bfsDistances(graph, sources):
    # BFS from all source nodes simultaneously. Returns {node: distance} for
    # every node reachable from any source. Unvisited nodes are omitted.
    dist = {}
    queue = deque()
    for s in sources:
        if s not in dist:
            dist[s] = 0
            queue.append(s)

    while queue:
        current = queue.popleft()
        for neighbour in graph.getNeighbours(current):
            if neighbour not in dist:
                dist[neighbour] = dist[current] + 1
                queue.append(neighbour)

    return dist


class AppUI:
    def __init__(self, graph, simulation):
        self.graph       = graph
        self.simulation  = simulation
        self.eventLog    = None   # created during setup() once Tkinter frame exists

        # Active overlay: None | "roads" | "coverage" | "crime"
        self.overlayMode = None

        # Currently selected node for the info panel
        self.selectedNode = None

        # Ambulance coverage distances (populated when coverage overlay is active)
        self.coverageDist = {}

        # Playback state
        self.autoPlaying = False

        # Placeholder callbacks -- main.py replaces these before the loop starts
        self.onStartSimulation = lambda: None
        self.onReset           = lambda: None
        self.onStep            = lambda: None

        # Tkinter variables (created in setup)
        self.gridSizeVar    = None
        self.floodProbVar   = None
        self.stepDelayVar   = None
        self.buildingVars   = {}

        # Tkinter widgets we need to reference later
        self.nodeInfoText   = None
        self.playPauseBtn   = None
        self.tkRoot         = None
        self.pgScreen       = None

    # ------------------------------------------------------------------ #
    #  Initialisation                                                      #
    # ------------------------------------------------------------------ #

    def setup(self):
        # Initialise Pygame and Tkinter windows. Call once before the main loop.
        self._setupPygame()
        self._setupTkinter()

    def _setupPygame(self):
        pygame.init()
        width  = CELL_SIZE * self.graph.cols
        height = CELL_SIZE * self.graph.rows
        self.pgScreen = pygame.display.set_mode((width, height))
        pygame.display.set_caption("CityMind -- Urban Intelligence System")
        self.pgFont = pygame.font.SysFont("monospace", 10)
        self._loadSprites()

    def _loadSprites(self):
        spriteSize = CELL_SIZE - MARGIN * 2
        tilesDir   = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                  "assets", "kenney_tiny_town", "Tiles")
        self.sprites = {}
        for buildingType, tileName in SPRITE_TILES.items():
            path = os.path.join(tilesDir, f"{tileName}.png")
            try:
                raw = pygame.image.load(path).convert_alpha()
                self.sprites[buildingType] = pygame.transform.scale(raw, (spriteSize, spriteSize))
            except Exception:
                self.sprites[buildingType] = None

    def _setupTkinter(self):
        self.tkRoot = tk.Tk()
        self.tkRoot.title("CityMind -- Control Panel")
        self.tkRoot.geometry("360x800")
        self.tkRoot.configure(bg="#1a1a2e")
        self.tkRoot.resizable(False, False)

        # Build each panel section in order
        self._buildSettingsPanel()
        self._buildOverlayButtons()
        self.tkRoot.update_idletasks()   # ensure layout before measuring remaining space
        self._buildNodeInfoPanel()
        self._buildEventLogPanel()

    def _buildSettingsPanel(self):
        # Outer frame for all settings widgets
        frame = tk.LabelFrame(
            self.tkRoot,
            text="Settings",
            fg="white",
            bg="#1a1a2e",
            font=("Courier", 9, "bold"),
            padx=6,
            pady=4
        )
        frame.pack(side=tk.TOP, fill=tk.X, padx=8, pady=(8, 4))

        # Grid size
        self.gridSizeVar = tk.StringVar(value="10")
        self._labeledEntry(frame, "Grid Size:", self.gridSizeVar, row=0)

        # Building counts
        defaults = {
            "Hospital":       "2",
            "School":         "3",
            "Industrial":     "4",
            "Residential":    "15",
            "PowerPlant":     "2",
            "AmbulanceDepot": "1",
        }
        for i, (bType, default) in enumerate(defaults.items()):
            var = tk.StringVar(value=default)
            self.buildingVars[bType] = var
            self._labeledEntry(frame, f"{bType}:", var, row=i + 1)

        # Flood probability slider
        self.floodProbVar = tk.DoubleVar(value=0.30)
        tk.Label(
            frame, text="Flood Probability:", fg="white", bg="#1a1a2e",
            font=("Courier", 9), anchor="w"
        ).grid(row=8, column=0, sticky="w", pady=2)
        tk.Scale(
            frame,
            variable=self.floodProbVar,
            from_=0.0, to=1.0, resolution=0.05,
            orient=tk.HORIZONTAL,
            bg="#1a1a2e", fg="white",
            highlightthickness=0, troughcolor="#2d2d44",
            length=160,
        ).grid(row=8, column=1, sticky="w", pady=2)

        # Step delay slider
        self.stepDelayVar = tk.DoubleVar(value=0.5)
        tk.Label(
            frame, text="Step Delay (s):", fg="white", bg="#1a1a2e",
            font=("Courier", 9), anchor="w"
        ).grid(row=9, column=0, sticky="w", pady=2)
        tk.Scale(
            frame,
            variable=self.stepDelayVar,
            from_=0.0, to=2.0, resolution=0.1,
            orient=tk.HORIZONTAL,
            bg="#1a1a2e", fg="white",
            highlightthickness=0, troughcolor="#2d2d44",
            length=160,
        ).grid(row=9, column=1, sticky="w", pady=2)

        # Control buttons
        btnFrame = tk.Frame(frame, bg="#1a1a2e")
        btnFrame.grid(row=10, column=0, columnspan=2, pady=(6, 2))

        tk.Button(
            btnFrame, text="Start Simulation",
            command=self._onStartClicked,
            bg="#4a90d9", fg="white",
            relief=tk.FLAT, padx=8, pady=4,
            font=("Courier", 9, "bold")
        ).pack(side=tk.LEFT, padx=4)

        tk.Button(
            btnFrame, text="Reset",
            command=self._onResetClicked,
            bg="#8b8b8b", fg="white",
            relief=tk.FLAT, padx=8, pady=4,
            font=("Courier", 9, "bold")
        ).pack(side=tk.LEFT, padx=4)

        tk.Button(
            btnFrame, text="Step",
            command=self._onStepClicked,
            bg="#f0c040", fg="#1a1a2e",
            relief=tk.FLAT, padx=8, pady=4,
            font=("Courier", 9, "bold")
        ).pack(side=tk.LEFT, padx=4)

        self.playPauseBtn = tk.Button(
            btnFrame, text="Play",
            command=self._onPlayPauseClicked,
            bg="#00cc44", fg="white",
            relief=tk.FLAT, padx=8, pady=4,
            font=("Courier", 9, "bold")
        )
        self.playPauseBtn.pack(side=tk.LEFT, padx=4)

    def _labeledEntry(self, parent, labelText, variable, row):
        # Helper: one label + entry row in a grid layout
        tk.Label(
            parent, text=labelText, fg="white", bg="#1a1a2e",
            font=("Courier", 9), anchor="w"
        ).grid(row=row, column=0, sticky="w", pady=2)
        tk.Entry(
            parent, textvariable=variable, width=5,
            bg="#2d2d44", fg="white", insertbackground="white",
            relief=tk.FLAT, font=("Courier", 9)
        ).grid(row=row, column=1, sticky="w", pady=2)

    def _buildOverlayButtons(self):
        # Three toggle buttons for the three overlay modes
        frame = tk.Frame(self.tkRoot, bg="#1a1a2e")
        frame.pack(side=tk.TOP, fill=tk.X, padx=8, pady=(4, 4))

        tk.Label(
            frame, text="Overlays:", fg="white", bg="#1a1a2e",
            font=("Courier", 9, "bold")
        ).pack(side=tk.LEFT, padx=(0, 6))

        overlayDefs = [
            ("Road Network", "roads"),
            ("Coverage",     "coverage"),
            ("Crime Risk",   "crime"),
        ]
        for label, mode in overlayDefs:
            tk.Button(
                frame, text=label,
                command=lambda m=mode: self._toggleOverlay(m),
                bg="#2d2d44", fg="white",
                relief=tk.FLAT, padx=6, pady=3,
                font=("Courier", 8)
            ).pack(side=tk.LEFT, padx=2)

    def _buildNodeInfoPanel(self):
        frame = tk.LabelFrame(
            self.tkRoot,
            text="Node Info",
            fg="white",
            bg="#1a1a2e",
            font=("Courier", 9, "bold"),
            padx=6,
            pady=4
        )
        frame.pack(side=tk.TOP, fill=tk.X, padx=8, pady=(4, 4))

        self.nodeInfoText = tk.Text(
            frame,
            height=5,
            state=tk.DISABLED,
            bg="#2d2d44",
            fg="white",
            font=("Courier", 9),
            relief=tk.FLAT,
            padx=4,
            pady=4,
            wrap=tk.WORD
        )
        self.nodeInfoText.pack(fill=tk.X)

    def _buildEventLogPanel(self):
        # Event log fills whatever space remains at the bottom
        frame = tk.Frame(self.tkRoot, bg="#1a1a2e")
        frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=8, pady=(4, 8))

        # Build the EventLog widget inside this frame
        self.eventLog = EventLog(frame)

    # ------------------------------------------------------------------ #
    #  Button callbacks                                                    #
    # ------------------------------------------------------------------ #

    def _onStartClicked(self):
        self.onStartSimulation()

    def _onResetClicked(self):
        self.autoPlaying = False
        if self.playPauseBtn:
            self.playPauseBtn.config(text="Play", bg="#00cc44")
        self.onReset()

    def _onStepClicked(self):
        self.onStep()

    def _onPlayPauseClicked(self):
        self.autoPlaying = not self.autoPlaying
        if self.autoPlaying:
            self.playPauseBtn.config(text="Pause", bg="#e84040")
        else:
            self.playPauseBtn.config(text="Play", bg="#00cc44")

    def _toggleOverlay(self, mode):
        # Toggle the requested overlay; turn it off if already active
        if self.overlayMode == mode:
            self.overlayMode = None
        else:
            self.overlayMode = mode
            if mode == "coverage":
                self._refreshCoverage()

    def _refreshCoverage(self):
        # Compute BFS distances from every ambulance position for the heatmap
        sources = list(self.graph.ambulancePositions)
        if sources:
            self.coverageDist = bfsDistances(self.graph, sources)
        else:
            self.coverageDist = {}

    # ------------------------------------------------------------------ #
    #  Public API                                                          #
    # ------------------------------------------------------------------ #

    def render(self):
        # Redraw the full Pygame grid. Call every frame.
        self.pgScreen.fill(hexToRgb(COLOURS["bg"]))
        self._drawNodes()
        self._drawRoads()
        self._drawRoutes()
        self._drawAmbulances()
        self._drawMedicalTeam()
        pygame.display.flip()

    def handleEvents(self):
        # Process Pygame events. Returns False if the user closed the window.
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self._handleClick(event.pos)
        return True

    def updateTk(self):
        # Keep the Tkinter window responsive without blocking
        if self.tkRoot:
            self.tkRoot.update()

    def getSimSettings(self):
        # Return current values from all settings widgets
        return {
            "gridSize":         int(self.gridSizeVar.get()),
            "floodProbability": float(self.floodProbVar.get()),
            "stepDelay":        float(self.stepDelayVar.get()),
            "buildings": {
                "Hospital":       int(self.buildingVars["Hospital"].get()),
                "School":         int(self.buildingVars["School"].get()),
                "Industrial":     int(self.buildingVars["Industrial"].get()),
                "Residential":    int(self.buildingVars["Residential"].get()),
                "PowerPlant":     int(self.buildingVars["PowerPlant"].get()),
                "AmbulanceDepot": int(self.buildingVars["AmbulanceDepot"].get()),
            }
        }

    def addLog(self, text):
        # Proxy to the event log widget
        self.eventLog.addEntry(text)

    def showNodeInfo(self, node):
        # Display stats for the clicked node in the info panel
        data = self.graph.nodes[node]
        info = (
            f"Node: {node}\n"
            f"Type: {data['type']}\n"
            f"Population: {data['population']}\n"
            f"Risk Index: {data['riskIndex']}\n"
            f"Accessible: {data['accessible']}"
        )
        self.nodeInfoText.config(state=tk.NORMAL)
        self.nodeInfoText.delete("1.0", tk.END)
        self.nodeInfoText.insert(tk.END, info)
        self.nodeInfoText.config(state=tk.DISABLED)

    # ------------------------------------------------------------------ #
    #  Pygame drawing helpers                                              #
    # ------------------------------------------------------------------ #

    def _drawNodes(self):
        for node, data in self.graph.nodes.items():
            r, c = node
            x = c * CELL_SIZE + MARGIN
            y = r * CELL_SIZE + MARGIN
            w = CELL_SIZE - MARGIN * 2
            h = CELL_SIZE - MARGIN * 2

            if self.overlayMode:
                # Overlay modes always use coloured rects
                colour = self._nodeColour(node, data)
                pygame.draw.rect(self.pgScreen, colour, (x, y, w, h))
            else:
                sprite = self.sprites.get(data["type"])
                if sprite:
                    self.pgScreen.blit(sprite, (x, y))
                else:
                    colour = hexToRgb(COLOURS.get(data["type"], COLOURS["Empty"]))
                    pygame.draw.rect(self.pgScreen, colour, (x, y, w, h))

            # Type label on non-empty cells so buildings are always readable
            if data["type"] != "Empty":
                label    = data["type"][:3].upper()
                textColr = (255, 255, 255) if not self.overlayMode else (220, 220, 220)
                textSurf = self.pgFont.render(label, True, textColr)
                self.pgScreen.blit(textSurf, (x + 2, y + 2))

    def _nodeColour(self, node, data):
        # Overlay modes modify cell colour; fall back to building type colour
        if self.overlayMode == "coverage":
            dist = self.coverageDist.get(node, 0)
            intensity = min(255, int(dist * 10))
            return (0, 0, intensity)

        if self.overlayMode == "crime":
            risk = data["riskIndex"]
            if risk >= 2.5:
                return hexToRgb("#ff0000")   # High
            if risk >= 1.75:
                return hexToRgb("#ff8800")   # Medium
            if risk >= 1.25:
                return hexToRgb("#00aa00")   # Low
            return hexToRgb(COLOURS["Empty"])

        return hexToRgb(COLOURS.get(data["type"], COLOURS["Empty"]))

    def _drawRoads(self):
        # Draw each edge as a line between the two node centres
        for (nodeA, nodeB), edgeData in self.graph.edges.items():
            colour = self._roadColour(nodeA, nodeB, edgeData)
            if colour is None:
                continue  # hidden in this view

            ax, ay = nodeCentre(nodeA)
            bx, by = nodeCentre(nodeB)
            pygame.draw.line(self.pgScreen, colour, (ax, ay), (bx, by), 2)

    def _roadColour(self, nodeA, nodeB, edgeData):
        blocked = edgeData["blocked"]

        if blocked:
            return hexToRgb(COLOURS["road_flooded"])

        if self.overlayMode == "roads":
            typeA = self.graph.nodes[nodeA]["type"]
            typeB = self.graph.nodes[nodeB]["type"]
            if typeA == "Residential" or typeB == "Residential":
                return hexToRgb(COLOURS["road_residential"])
            return hexToRgb(COLOURS["road"])

        # Normal view -- show unblocked roads in standard colour, skip blocked
        if not blocked:
            return hexToRgb(COLOURS["road"])

        return None

    def _drawRoutes(self):
        # Highlight the two emergency corridor routes when available
        if not self.simulation:
            return

        routeA = getattr(self.simulation, "routeA", [])
        routeB = getattr(self.simulation, "routeB", [])

        for nodeA, nodeB in routeA:
            self._drawRouteLine(nodeA, nodeB, hexToRgb(COLOURS["routeA"]))

        for nodeA, nodeB in routeB:
            self._drawRouteLine(nodeA, nodeB, hexToRgb(COLOURS["routeB"]))

    def _drawRouteLine(self, nodeA, nodeB, colour):
        ax, ay = nodeCentre(nodeA)
        bx, by = nodeCentre(nodeB)
        pygame.draw.line(self.pgScreen, colour, (ax, ay), (bx, by), 4)

    def _drawAmbulances(self):
        colour = hexToRgb(COLOURS["ambulance"])
        for pos in self.graph.ambulancePositions:
            cx, cy = nodeCentre(pos)
            pygame.draw.circle(self.pgScreen, colour, (cx, cy), 8)

    def _drawMedicalTeam(self):
        # Draw as a small cyan diamond at the team's current position
        if not self.simulation:
            return

        routerState = getattr(self.simulation, "routerState", None)
        if routerState is None:
            return

        pos = routerState.currentPos
        if pos is None:
            return

        cx, cy = nodeCentre(pos)
        colour  = hexToRgb(COLOURS["medicalTeam"])
        size    = 8
        # Diamond: top, right, bottom, left
        points = [
            (cx,        cy - size),
            (cx + size, cy),
            (cx,        cy + size),
            (cx - size, cy),
        ]
        pygame.draw.polygon(self.pgScreen, colour, points)

    # ------------------------------------------------------------------ #
    #  Input handling                                                      #
    # ------------------------------------------------------------------ #

    def _handleClick(self, pos):
        mouseX, mouseY = pos
        c = mouseX // CELL_SIZE
        r = mouseY // CELL_SIZE

        node = (r, c)
        if node in self.graph.nodes:
            self.selectedNode = node
            self.showNodeInfo(node)
