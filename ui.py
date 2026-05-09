import os
import tkinter as tk
from PIL import Image, ImageTk

from eventLog import EventLog


# Building types are drawn with one of two Tilemap sprites. Distinct types
# share a sprite -- the on-grid 3-letter label (HOS, SCH, ...) does the
# distinguishing.
BUILDING_SPRITES = {
    "Hospital":       "building1",
    "School":         "building1",
    "Residential":    "building2",
    "Industrial":     "building1",
    "PowerPlant":     "building1",
    "AmbulanceDepot": "building2",
}

# Empty cells pick from this set deterministically (per coord) for visual variety.
GROUND_VARIETY = ["grass", "wavy_grass", "flower_ground", "stoned_grass"]

# Pixel gap between cell edge and the filled building rectangle
MARGIN = 4

# Target canvas dimension in pixels -- cell size is derived to fit inside this
CANVAS_TARGET = 600

# Min and max cell size in pixels
MIN_CELL_SIZE = 20
MAX_CELL_SIZE = 50

# Tool descriptions surfaced under the Mouse Tool radio group
TOOL_DESCRIPTIONS = {
    "inspect":   "Click any cell to view its stats in Node Info.",
    "flood":     "Click two adjacent cells to flood the road between them.",
    "emergency": "Click any accessible cell to dispatch a civilian emergency there.",
}

# Modern font stack -- Segoe UI for general text, Consolas for the status bar
# and event log where a monospace font reads better.
FONT_TITLE  = ("Segoe UI Semibold", 10)
FONT_BODY   = ("Segoe UI", 10)
FONT_SMALL  = ("Segoe UI", 9)
FONT_HINT   = ("Segoe UI", 9, "italic")
FONT_BUTTON = ("Segoe UI Semibold", 10)
FONT_STATUS = ("Consolas", 11, "bold")
FONT_LABEL  = ("Segoe UI", 8, "bold")
FONT_LEGEND = ("Consolas", 9, "bold")
FONT_MONO   = ("Consolas", 10)

# Base UI colour palette
COLOURS = {
    "bg":               "#13131e",
    "panel":            "#1d1d2f",
    "panel_alt":        "#262640",
    "border":           "#3a3a5a",
    "text":             "#e8e8f4",
    "text_dim":         "#a0a0c0",
    "accent":           "#5dd9ff",
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
    "medicalPath":      "#ffd966",
    "routeA":           "#ff6600",
    "routeB":           "#00cc44",
    "btnPrimary":       "#3d8bd9",
    "btnSecondary":     "#5a5a78",
    "btnAccent":        "#f0a830",
    "btnPlay":          "#22a85d",
    "btnPause":         "#d94545",
}


class AppUI:
    """
    Single-window Tk UI laid out in three columns:
      left   = status bar + city grid Canvas
      middle = settings, tools, overlays, node info
      right  = event log
    The UI talks only to the AppController -- never to the simulation or graph
    directly except for read-only rendering.
    """

    def __init__(self, controller):
        self._controller = controller

        # View state (UI-only, not part of the simulation)
        self._overlayMode     = None
        self._selectedNode    = None
        self._autoPlaying     = False
        self._coverageDist    = {}
        self._coverageMaxDist = 0.0
        self._isRunning       = True

        # Mouse tool: "inspect", "flood", or "emergency"
        self._toolMode        = "inspect"
        self._floodFirstNode  = None

        # Cell size in pixels. Recomputed whenever grid size changes.
        self._cellSize        = self._computeCellSize(controller.getGraph().cols)

        # Tk root and child widgets (created in setup)
        self._tkRoot          = None
        self._canvas          = None
        self._eventLog        = None
        self._nodeInfoText    = None
        self._playPauseBtn    = None
        self._toolModeVar     = None
        self._toolDescLabel   = None
        self._statusLabel     = None

        # Tk variables for settings widgets
        self._gridSizeVar     = None
        self._floodProbVar    = None
        self._stepDelayVar    = None
        self._buildingVars    = {}
        self._residentialHopsVar = None
        self._powerplantHopsVar  = None

        # Sprite caches: keep ImageTk references alive to prevent garbage collection
        self._spriteCache     = {}    # building type -> ImageTk
        self._groundCache     = []    # ground variants for Empty cells

    # ------------------------------------------------------------------ #
    #  Public lifecycle                                                    #
    # ------------------------------------------------------------------ #

    def setup(self):
        # Build the Tk window and load sprites. Call once before run().
        self._buildWindow()
        self._loadSprites()
        self._render()
        self._refreshStatus()
        self.addLog("CityMind started. Configure settings and press Start.")

    def run(self):
        # Hand control to Tk's main loop.
        self._tkRoot.protocol("WM_DELETE_WINDOW", self._onClose)
        self._scheduleAutoTick()
        self._tkRoot.mainloop()

    def addLog(self, text):
        # Append a line to the event log. Used by the controller's event listener.
        if self._eventLog is not None:
            self._eventLog.addEntry(text)

    # ------------------------------------------------------------------ #
    #  Window construction                                                 #
    # ------------------------------------------------------------------ #

    def _buildWindow(self):
        graph = self._controller.getGraph()

        self._tkRoot = tk.Tk()
        self._tkRoot.title("CityMind -- Urban Intelligence System")
        self._tkRoot.configure(bg=COLOURS["bg"])

        # ---- Column 1: status bar above the city grid canvas ----
        leftFrame = tk.Frame(self._tkRoot, bg=COLOURS["bg"])
        leftFrame.pack(side=tk.LEFT, fill=tk.Y, padx=8, pady=8)

        self._statusLabel = tk.Label(
            leftFrame, text="", fg=COLOURS["accent"], bg=COLOURS["panel_alt"],
            font=FONT_STATUS, anchor="w",
            padx=12, pady=10, relief=tk.FLAT
        )
        self._statusLabel.pack(side=tk.TOP, fill=tk.X, pady=(0, 8))

        canvasW = self._cellSize * graph.cols
        canvasH = self._cellSize * graph.rows
        self._canvas = tk.Canvas(
            leftFrame, width=canvasW, height=canvasH,
            bg=COLOURS["bg"], highlightthickness=0
        )
        self._canvas.pack(side=tk.TOP)
        self._canvas.bind("<Button-1>", self._onCanvasClick)

        # ---- Column 2: control panels ----
        controlFrame = tk.Frame(self._tkRoot, bg=COLOURS["bg"], width=320)
        controlFrame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 8), pady=8)
        controlFrame.pack_propagate(False)

        self._buildSettingsPanel(controlFrame)
        self._buildConstraintsPanel(controlFrame)
        self._buildToolPanel(controlFrame)
        self._buildOverlayButtons(controlFrame)
        self._buildNodeInfoPanel(controlFrame)

        # ---- Column 3: legend on top, event log fills the rest ----
        rightFrame = tk.Frame(self._tkRoot, bg=COLOURS["bg"], width=320)
        rightFrame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 8), pady=8)

        self._buildLegendPanel(rightFrame)

        logFrame = tk.Frame(rightFrame, bg=COLOURS["bg"])
        logFrame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self._eventLog = EventLog(logFrame)

    def _buildSettingsPanel(self, parent):
        frame = tk.LabelFrame(
            parent, text=" Settings ", fg=COLOURS["text"], bg=COLOURS["panel"],
            font=FONT_TITLE, padx=10, pady=6,
            relief=tk.FLAT, borderwidth=0
        )
        frame.pack(side=tk.TOP, fill=tk.X, pady=(0, 8))

        # Grid size
        self._gridSizeVar = tk.StringVar(value=str(self._controller.getGraph().cols))
        self._labeledEntry(frame, "Grid Size:", self._gridSizeVar, row=0)

        # Building counts
        defaults = self._controller.getDefaultCounts()
        ordered  = ["Hospital", "School", "Industrial", "Residential",
                    "PowerPlant", "AmbulanceDepot"]
        for i, bType in enumerate(ordered):
            var = tk.StringVar(value=str(defaults.get(bType, 0)))
            self._buildingVars[bType] = var
            self._labeledEntry(frame, f"{bType}:", var, row=i + 1)

        # Flood probability slider
        self._floodProbVar = tk.DoubleVar(value=0.30)
        tk.Label(
            frame, text="Flood Probability:", fg=COLOURS["text"], bg=COLOURS["panel"],
            font=FONT_BODY, anchor="w"
        ).grid(row=8, column=0, sticky="w", pady=3)
        tk.Scale(
            frame, variable=self._floodProbVar,
            from_=0.0, to=1.0, resolution=0.05, orient=tk.HORIZONTAL,
            bg=COLOURS["panel"], fg=COLOURS["text"], font=FONT_SMALL,
            highlightthickness=0, troughcolor=COLOURS["panel_alt"],
            length=170, sliderrelief=tk.FLAT, sliderlength=18
        ).grid(row=8, column=1, sticky="w", pady=3)

        # Step delay slider
        self._stepDelayVar = tk.DoubleVar(value=0.4)
        tk.Label(
            frame, text="Step Delay (s):", fg=COLOURS["text"], bg=COLOURS["panel"],
            font=FONT_BODY, anchor="w"
        ).grid(row=9, column=0, sticky="w", pady=3)
        tk.Scale(
            frame, variable=self._stepDelayVar,
            from_=0.0, to=2.0, resolution=0.1, orient=tk.HORIZONTAL,
            bg=COLOURS["panel"], fg=COLOURS["text"], font=FONT_SMALL,
            highlightthickness=0, troughcolor=COLOURS["panel_alt"],
            length=170, sliderrelief=tk.FLAT, sliderlength=18
        ).grid(row=9, column=1, sticky="w", pady=3)

        # Control buttons -- two rows so they breathe
        btnFrame = tk.Frame(frame, bg=COLOURS["panel"])
        btnFrame.grid(row=10, column=0, columnspan=2, pady=(10, 2), sticky="ew")

        rowOne = tk.Frame(btnFrame, bg=COLOURS["panel"])
        rowOne.pack(side=tk.TOP, fill=tk.X, pady=(0, 4))
        rowTwo = tk.Frame(btnFrame, bg=COLOURS["panel"])
        rowTwo.pack(side=tk.TOP, fill=tk.X)

        self._makeButton(rowOne, "Generate City", self._onStartClicked, COLOURS["btnPrimary"]).pack(
            side=tk.LEFT, expand=True, fill=tk.X, padx=2)
        self._makeButton(rowOne, "Reset",         self._onResetClicked,  COLOURS["btnSecondary"]).pack(
            side=tk.LEFT, expand=True, fill=tk.X, padx=2)
        self._makeButton(rowTwo, "Step",          self._onStepClicked,   COLOURS["btnAccent"]).pack(
            side=tk.LEFT, expand=True, fill=tk.X, padx=2)

        self._playPauseBtn = self._makeButton(
            rowTwo, "Play", self._onPlayPauseClicked, COLOURS["btnPlay"]
        )
        self._playPauseBtn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)

    def _makeButton(self, parent, text, command, bg, fg=None):
        return tk.Button(
            parent, text=text, command=command,
            bg=bg, fg=fg if fg is not None else "white",
            activebackground=bg, activeforeground="white",
            relief=tk.FLAT, borderwidth=0, padx=10, pady=6,
            font=FONT_BUTTON, cursor="hand2"
        )

    def _labeledEntry(self, parent, labelText, variable, row):
        tk.Label(
            parent, text=labelText, fg=COLOURS["text"], bg=COLOURS["panel"],
            font=FONT_BODY, anchor="w"
        ).grid(row=row, column=0, sticky="w", pady=3)
        tk.Entry(
            parent, textvariable=variable, width=6,
            bg=COLOURS["panel_alt"], fg=COLOURS["text"], insertbackground=COLOURS["text"],
            relief=tk.FLAT, font=FONT_BODY,
            highlightthickness=1, highlightbackground=COLOURS["border"],
            highlightcolor=COLOURS["accent"]
        ).grid(row=row, column=1, sticky="w", pady=3, padx=(8, 0))

    def _buildConstraintsPanel(self, parent):
        frame = tk.LabelFrame(
            parent, text=" Constraints ", fg=COLOURS["text"], bg=COLOURS["panel"],
            font=FONT_TITLE, padx=10, pady=6,
            relief=tk.FLAT, borderwidth=0
        )
        frame.pack(side=tk.TOP, fill=tk.X, pady=(0, 8))

        self._residentialHopsVar = tk.StringVar(value="3")
        self._labeledEntry(frame, "Residential hops:", self._residentialHopsVar, row=0)

        self._powerplantHopsVar = tk.StringVar(value="2")
        self._labeledEntry(frame, "PowerPlant hops:", self._powerplantHopsVar, row=1)

        tk.Label(
            frame,
            text="Edit these and re-Generate to test the city under different rules.",
            fg=COLOURS["text_dim"], bg=COLOURS["panel"], font=FONT_HINT,
            anchor="w", justify="left", wraplength=280, padx=2, pady=4
        ).grid(row=2, column=0, columnspan=2, sticky="w", pady=(6, 0))

    def _buildLegendPanel(self, parent):
        frame = tk.LabelFrame(
            parent, text=" Legend ", fg=COLOURS["text"], bg=COLOURS["panel"],
            font=FONT_TITLE, padx=10, pady=6,
            relief=tk.FLAT, borderwidth=0
        )
        frame.pack(side=tk.TOP, fill=tk.X, pady=(0, 8))

        items = [
            ("MED",   COLOURS["medicalTeam"],    "Medical team"),
            ("+",     "#e54a4a",                 "Ambulance (white square + cross)"),
            ("!",     "#ff3030",                 "Active emergency"),
            ("---",   COLOURS["road_flooded"],   "Flooded road"),
            ("---",   COLOURS["routeA"],         "Route A (primary corridor)"),
            ("---",   COLOURS["routeB"],         "Route B (backup corridor)"),
            ("- -",   COLOURS["medicalPath"],    "Planned A* path"),
        ]

        for symbol, colour, desc in items:
            row = tk.Frame(frame, bg=COLOURS["panel"])
            row.pack(side=tk.TOP, fill=tk.X, pady=2)

            tk.Label(
                row, text=symbol, fg=colour, bg=COLOURS["panel"],
                font=FONT_LEGEND, width=5, anchor="w"
            ).pack(side=tk.LEFT)
            tk.Label(
                row, text=desc, fg=COLOURS["text"], bg=COLOURS["panel"],
                font=FONT_SMALL, anchor="w"
            ).pack(side=tk.LEFT)

    def _buildToolPanel(self, parent):
        # Mouse-tool radio group with a one-line description that updates on change
        frame = tk.LabelFrame(
            parent, text=" Mouse Tool ", fg=COLOURS["text"], bg=COLOURS["panel"],
            font=FONT_TITLE, padx=10, pady=6,
            relief=tk.FLAT, borderwidth=0
        )
        frame.pack(side=tk.TOP, fill=tk.X, pady=(0, 8))

        radioRow = tk.Frame(frame, bg=COLOURS["panel"])
        radioRow.pack(side=tk.TOP, fill=tk.X)

        self._toolModeVar = tk.StringVar(value="inspect")
        tools = [("Inspect", "inspect"), ("Flood", "flood"), ("Emergency", "emergency")]
        for label, mode in tools:
            tk.Radiobutton(
                radioRow, text=label, variable=self._toolModeVar, value=mode,
                command=self._onToolModeChanged,
                bg=COLOURS["panel"], fg=COLOURS["text"],
                selectcolor=COLOURS["panel_alt"], activebackground=COLOURS["panel"],
                activeforeground=COLOURS["text"], font=FONT_BODY,
                cursor="hand2"
            ).pack(side=tk.LEFT, padx=4)

        self._toolDescLabel = tk.Label(
            frame, text=TOOL_DESCRIPTIONS["inspect"],
            fg=COLOURS["text_dim"], bg=COLOURS["panel"], font=FONT_HINT,
            anchor="w", justify="left", wraplength=280, padx=2, pady=4
        )
        self._toolDescLabel.pack(side=tk.TOP, fill=tk.X, pady=(6, 0))

    def _buildOverlayButtons(self, parent):
        frame = tk.LabelFrame(
            parent, text=" Overlays ", fg=COLOURS["text"], bg=COLOURS["panel"],
            font=FONT_TITLE, padx=10, pady=6,
            relief=tk.FLAT, borderwidth=0
        )
        frame.pack(side=tk.TOP, fill=tk.X, pady=(0, 8))

        row = tk.Frame(frame, bg=COLOURS["panel"])
        row.pack(side=tk.TOP, fill=tk.X)

        overlayDefs = [
            ("Road Network", "roads"),
            ("Coverage",     "coverage"),
            ("Crime Risk",   "crime"),
        ]
        for label, mode in overlayDefs:
            tk.Button(
                row, text=label,
                command=lambda m=mode: self._toggleOverlay(m),
                bg=COLOURS["panel_alt"], fg=COLOURS["text"],
                activebackground=COLOURS["accent"], activeforeground=COLOURS["bg"],
                relief=tk.FLAT, borderwidth=0, padx=10, pady=6,
                font=FONT_SMALL, cursor="hand2"
            ).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)

        tk.Label(
            frame,
            text="Toggle road colour-coding, ambulance reach heatmap, or crime risk gradient.",
            fg=COLOURS["text_dim"], bg=COLOURS["panel"], font=FONT_HINT,
            anchor="w", justify="left", wraplength=280, padx=2, pady=4
        ).pack(side=tk.TOP, fill=tk.X, pady=(6, 0))

    def _buildNodeInfoPanel(self, parent):
        frame = tk.LabelFrame(
            parent, text=" Node Info ", fg=COLOURS["text"], bg=COLOURS["panel"],
            font=FONT_TITLE, padx=10, pady=6,
            relief=tk.FLAT, borderwidth=0
        )
        frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, pady=(0, 8))

        self._nodeInfoText = tk.Text(
            frame, height=6, state=tk.DISABLED,
            bg=COLOURS["panel_alt"], fg=COLOURS["text"], font=FONT_MONO,
            relief=tk.FLAT, padx=8, pady=6, wrap=tk.WORD
        )
        self._nodeInfoText.pack(fill=tk.BOTH, expand=True)

    # ------------------------------------------------------------------ #
    #  Cell size + sprite loading                                          #
    # ------------------------------------------------------------------ #

    def _computeCellSize(self, gridSize):
        # Pick a cell size so the grid roughly fits CANVAS_TARGET pixels.
        gridSize = max(1, gridSize)
        return max(MIN_CELL_SIZE, min(MAX_CELL_SIZE, CANVAS_TARGET // gridSize))

    def _loadSprites(self):
        spriteSize = max(8, self._cellSize - MARGIN * 2)
        baseDir    = os.path.dirname(os.path.abspath(__file__))
        tilesDir   = os.path.join(baseDir, "assets", "kenney_tiny_town", "Tilemap")

        # Building sprites
        self._spriteCache = {}
        for buildingType, tileName in BUILDING_SPRITES.items():
            self._spriteCache[buildingType] = self._loadSprite(tilesDir, tileName, spriteSize)

        # Ground variants (used for Empty cells, picked deterministically per coord)
        self._groundCache = []
        for tileName in GROUND_VARIETY:
            sprite = self._loadSprite(tilesDir, tileName, spriteSize)
            if sprite is not None:
                self._groundCache.append(sprite)

    def _loadSprite(self, folder, tileName, size):
        path = os.path.join(folder, f"{tileName}.png")
        try:
            raw    = Image.open(path).convert("RGBA")
            scaled = raw.resize((size, size), Image.NEAREST)
            return ImageTk.PhotoImage(scaled)
        except Exception:
            return None

    def _resizeCanvasIfNeeded(self):
        # Match the canvas to the controller's current graph dimensions and
        # reload sprites if cell size changed.
        graph        = self._controller.getGraph()
        newCellSize  = self._computeCellSize(max(graph.rows, graph.cols))
        sizeChanged  = newCellSize != self._cellSize

        self._cellSize = newCellSize

        canvasW = self._cellSize * graph.cols
        canvasH = self._cellSize * graph.rows
        self._canvas.config(width=canvasW, height=canvasH)

        if sizeChanged:
            self._loadSprites()

        # Re-pack so child frames flow around the resized canvas, then clear the
        # cached geometry so the root window snaps back to its natural size and
        # nothing gets cropped or overlapped.
        self._tkRoot.update_idletasks()
        self._tkRoot.geometry("")

    # ------------------------------------------------------------------ #
    #  Auto-play scheduling                                                #
    # ------------------------------------------------------------------ #

    def _scheduleAutoTick(self):
        if not self._isRunning:
            return

        if self._autoPlaying:
            stepDelay = self._readStepDelay()
            events    = self._controller.autoStepIfDue(stepDelay)
            if events:
                self._render()
                self._refreshStatus()
            if self._controller.isFinished():
                self._setAutoPlaying(False)

        self._tkRoot.after(100, self._scheduleAutoTick)

    # ------------------------------------------------------------------ #
    #  Button callbacks                                                    #
    # ------------------------------------------------------------------ #

    def _onStartClicked(self):
        settings = self.getSimSettings()
        self.addLog("Starting simulation setup...")
        self._tkRoot.update_idletasks()

        logs = self._controller.startSimulation(settings)
        for entry in logs:
            self.addLog(entry)
        self._eventLog.addSeparator()

        self._resizeCanvasIfNeeded()
        self._render()
        self._refreshStatus()

    def _onResetClicked(self):
        self._setAutoPlaying(False)
        settings = self.getSimSettings()
        self._controller.resetSimulation(settings)
        self._eventLog.clear()
        self.addLog("Simulation reset. Press Start to begin.")
        self._resizeCanvasIfNeeded()
        self._render()
        self._refreshStatus()

    def _onStepClicked(self):
        self._controller.stepSimulation()
        self._render()
        self._refreshStatus()

    def _onPlayPauseClicked(self):
        self._setAutoPlaying(not self._autoPlaying)

    def _setAutoPlaying(self, value):
        self._autoPlaying = value
        if value:
            self._playPauseBtn.config(text="Pause", bg="#e84040")
        else:
            self._playPauseBtn.config(text="Play", bg="#00cc44")

    def _toggleOverlay(self, mode):
        if self._overlayMode == mode:
            self._overlayMode = None
        else:
            self._overlayMode = mode
            if mode == "coverage":
                self._refreshCoverage()
        self._render()

    def _refreshCoverage(self):
        # Weighted Dijkstra distances from every node to its nearest ambulance.
        self._coverageDist    = self._controller.getCoverageDistances()
        finiteVals            = [d for d in self._coverageDist.values() if d != float('inf')]
        self._coverageMaxDist = max(finiteVals) if finiteVals else 0.0

    def _onCanvasClick(self, event):
        c = event.x // self._cellSize
        r = event.y // self._cellSize
        node = (r, c)

        if node not in self._controller.getGraph().nodes:
            return

        if self._toolMode == "flood":
            self._handleFloodClick(node)
        elif self._toolMode == "emergency":
            self._handleEmergencyClick(node)
        else:
            self._handleInspectClick(node)

    def _handleInspectClick(self, node):
        info = self._controller.getNodeInfo(node)
        if info is None:
            return
        self._selectedNode = node
        self._showNodeInfo(info)
        self._render()

    def _handleFloodClick(self, node):
        # Two-click pattern: first click selects, second click on an adjacent
        # node floods the connecting road.
        if self._floodFirstNode is None:
            self._floodFirstNode = node
            self.addLog(f"Flood tool: selected {node}, click an adjacent cell to flood the road.")
            self._render()
            return

        first = self._floodFirstNode
        self._floodFirstNode = None

        if node == first:
            self.addLog("Flood tool: same cell clicked twice -- selection cleared.")
            self._render()
            return

        event = self._controller.floodEdge(first, node)
        if event is None:
            self.addLog(f"Flood tool: {first} and {node} are not adjacent or already flooded.")
        else:
            self.addLog(event)

        self._render()

    def _handleEmergencyClick(self, node):
        event = self._controller.addEmergency(node)
        if event is None:
            self.addLog(f"Emergency tool: cannot add at {node} (already queued, current position, or inaccessible).")
        else:
            self.addLog(event)
            self._refreshStatus()
        self._render()

    def _onToolModeChanged(self):
        self._toolMode = self._toolModeVar.get()
        self._floodFirstNode = None
        self._toolDescLabel.config(text=TOOL_DESCRIPTIONS[self._toolMode])
        self._render()

    def _showNodeInfo(self, info):
        text = (
            f"Node: {info['node']}\n"
            f"Type: {info['type']}\n"
            f"Population: {info['population']}\n"
            f"Risk Index: {info['riskIndex']}\n"
            f"Accessible: {info['accessible']}"
        )
        self._nodeInfoText.config(state=tk.NORMAL)
        self._nodeInfoText.delete("1.0", tk.END)
        self._nodeInfoText.insert(tk.END, text)
        self._nodeInfoText.config(state=tk.DISABLED)

    def _onClose(self):
        self._isRunning = False
        self._tkRoot.destroy()

    # ------------------------------------------------------------------ #
    #  Status bar                                                          #
    # ------------------------------------------------------------------ #

    def _refreshStatus(self):
        # Top-of-canvas status line that summarises what the simulation is doing
        if self._statusLabel is None:
            return

        sim   = self._controller.getSimulation()
        state = self._controller.getRouterState()

        if not sim.setupDone:
            self._statusLabel.config(
                text="Press Start to generate a city and begin the 20-step simulation."
            )
            return

        reached = len(state.reached) if state else 0
        skipped = len(state.skipped) if state else 0
        pending = len(state.civilians) - state.currentTarget if state else 0
        ambs    = len(self._controller.getGraph().ambulancePositions)

        if sim.currentStep <= sim.totalSteps:
            stepText = f"Step {sim.currentStep}/{sim.totalSteps}"
        else:
            extra = sim.currentStep - sim.totalSteps
            stepText = f"Step {sim.currentStep}/{sim.totalSteps} +{extra} (extended)"

        self._statusLabel.config(
            text=(
                f"{stepText}   "
                f"Civilians: {reached} reached / {pending} pending / {skipped} skipped   "
                f"Ambulances: {ambs}"
            )
        )

    # ------------------------------------------------------------------ #
    #  Rendering                                                           #
    # ------------------------------------------------------------------ #

    def _nodeCentre(self, node):
        r, c = node
        x = c * self._cellSize + self._cellSize // 2
        y = r * self._cellSize + self._cellSize // 2
        return (x, y)

    def _render(self):
        if self._canvas is None:
            return

        if self._overlayMode == "coverage":
            self._refreshCoverage()

        self._canvas.delete("all")
        self._drawNodes()
        self._drawRoads()
        self._drawRoutes()
        self._drawMedicalPath()
        self._drawEmergencies()
        self._drawAmbulances()
        self._drawMedicalTeam()
        self._drawFloodSelection()

    def _drawNodes(self):
        graph     = self._controller.getGraph()
        showLabel = self._cellSize >= 30   # only show 3-char labels when there's room

        for node, data in graph.nodes.items():
            r, c = node
            x = c * self._cellSize + MARGIN
            y = r * self._cellSize + MARGIN
            w = self._cellSize - MARGIN * 2

            if self._overlayMode:
                colour = self._nodeColour(node, data)
                self._canvas.create_rectangle(x, y, x + w, y + w, fill=colour, outline="")
            else:
                self._drawCellSprite(node, data, x, y, w)

            if showLabel and data["type"] != "Empty":
                label = data["type"][:3].upper()
                self._canvas.create_text(
                    x + 2, y + 2, anchor=tk.NW, text=label,
                    fill="white", font=FONT_LABEL
                )

    def _drawCellSprite(self, node, data, x, y, w):
        # Buildings: pick from BUILDING_SPRITES. Empty cells: pick a ground
        # variant deterministically by coord so the layout looks varied but
        # stable across renders.
        if data["type"] == "Empty":
            if self._groundCache:
                r, c = node
                idx = (r * 7 + c * 13) % len(self._groundCache)
                self._canvas.create_image(x, y, anchor=tk.NW, image=self._groundCache[idx])
                return
        else:
            sprite = self._spriteCache.get(data["type"])
            if sprite is not None:
                self._canvas.create_image(x, y, anchor=tk.NW, image=sprite)
                return

        # Fallback: solid colour rectangle when a sprite is missing
        colour = COLOURS.get(data["type"], COLOURS["Empty"])
        self._canvas.create_rectangle(x, y, x + w, y + w, fill=colour, outline="")

    def _nodeColour(self, node, data):
        if self._overlayMode == "coverage":
            distance = self._coverageDist.get(node, float('inf'))
            return self._coverageGradient(distance, self._coverageMaxDist)

        if self._overlayMode == "crime":
            return self._crimeGradient(data["riskIndex"])

        return COLOURS.get(data["type"], COLOURS["Empty"])

    def _crimeGradient(self, riskIndex):
        # Map riskIndex in [1.0, 2.5] to a green -> yellow -> red gradient.
        risk = max(1.0, min(2.5, riskIndex))
        if risk <= 1.75:
            t     = (risk - 1.0) / 0.75
            red   = int(255 * t)
            green = 200
        else:
            t     = (risk - 1.75) / 0.75
            red   = 255
            green = int(200 * (1.0 - t))
        return f"#{red:02x}{green:02x}00"

    def _coverageGradient(self, distance, maxDistance):
        # Distance to nearest ambulance: green (close) -> yellow -> red (far).
        if distance == float('inf'):
            return "#660000"
        if maxDistance <= 0:
            return "#00c800"
        t = min(1.0, distance / maxDistance)
        if t <= 0.5:
            s     = t * 2
            red   = int(255 * s)
            green = 200
        else:
            s     = (t - 0.5) * 2
            red   = 255
            green = int(200 * (1.0 - s))
        return f"#{red:02x}{green:02x}00"

    def _drawRoads(self):
        graph = self._controller.getGraph()
        for (nodeA, nodeB), edgeData in graph.edges.items():
            colour = self._roadColour(graph, nodeA, nodeB, edgeData)
            if colour is None:
                continue

            ax, ay = self._nodeCentre(nodeA)
            bx, by = self._nodeCentre(nodeB)
            self._canvas.create_line(ax, ay, bx, by, fill=colour, width=2)

    def _roadColour(self, graph, nodeA, nodeB, edgeData):
        if edgeData["blocked"]:
            return COLOURS["road_flooded"]

        if self._overlayMode == "roads":
            typeA = graph.nodes[nodeA]["type"]
            typeB = graph.nodes[nodeB]["type"]
            if typeA == "Residential" or typeB == "Residential":
                return COLOURS["road_residential"]
            return COLOURS["road"]

        return COLOURS["road"]

    def _drawRoutes(self):
        routeA, routeB = self._controller.getRoutes()
        for nodeA, nodeB in routeA:
            self._drawRouteLine(nodeA, nodeB, COLOURS["routeA"])
        for nodeA, nodeB in routeB:
            self._drawRouteLine(nodeA, nodeB, COLOURS["routeB"])

    def _drawRouteLine(self, nodeA, nodeB, colour):
        ax, ay = self._nodeCentre(nodeA)
        bx, by = self._nodeCentre(nodeB)
        self._canvas.create_line(ax, ay, bx, by, fill=colour, width=4)

    def _drawMedicalPath(self):
        # Highlight the medical team's planned A* path so the user can see
        # where it's heading on the next steps.
        state = self._controller.getRouterState()
        if state is None or not state.currentPath:
            return

        chain = [state.currentPos] + list(state.currentPath)
        for i in range(len(chain) - 1):
            ax, ay = self._nodeCentre(chain[i])
            bx, by = self._nodeCentre(chain[i + 1])
            self._canvas.create_line(
                ax, ay, bx, by,
                fill=COLOURS["medicalPath"], width=3, dash=(4, 3)
            )

    def _drawAmbulances(self):
        # White square + red cross. Bigger now so the icon reads at any zoom.
        graph = self._controller.getGraph()
        size  = max(8, self._cellSize // 4)
        for pos in graph.ambulancePositions:
            cx, cy = self._nodeCentre(pos)
            self._canvas.create_rectangle(
                cx - size, cy - size, cx + size, cy + size,
                fill="white", outline="#cc0000", width=1
            )
            self._canvas.create_line(cx - size + 2, cy, cx + size - 2, cy,
                                     fill="#cc0000", width=2)
            self._canvas.create_line(cx, cy - size + 2, cx, cy + size - 2,
                                     fill="#cc0000", width=2)
            if self._cellSize >= 35:
                self._canvas.create_text(
                    cx, cy + size + 7, text="AMB",
                    fill="white", font=("Consolas", 7, "bold")
                )

    def _drawEmergencies(self):
        # Pending civilians get a red ring + ! inside.
        radius = max(10, self._cellSize // 3)
        for node in self._controller.getActiveEmergencies():
            cx, cy = self._nodeCentre(node)
            self._canvas.create_oval(
                cx - radius, cy - radius, cx + radius, cy + radius,
                outline="#ff3030", width=2
            )
            self._canvas.create_text(
                cx, cy, text="!", fill="#ff3030",
                font=("Consolas", max(10, self._cellSize // 3), "bold")
            )

    def _drawFloodSelection(self):
        if self._floodFirstNode is None:
            return
        cx, cy = self._nodeCentre(self._floodFirstNode)
        radius = self._cellSize // 2 - 2
        self._canvas.create_rectangle(
            cx - radius, cy - radius, cx + radius, cy + radius,
            outline="#00bfff", width=3
        )

    def _drawMedicalTeam(self):
        # Cyan square with bold "MED" so the team is unmistakable on the grid.
        state = self._controller.getRouterState()
        if state is None or state.currentPos is None:
            return

        cx, cy = self._nodeCentre(state.currentPos)
        size   = max(10, self._cellSize // 3)

        self._canvas.create_rectangle(
            cx - size, cy - size, cx + size, cy + size,
            fill=COLOURS["medicalTeam"], outline="#005a4f", width=2
        )
        self._canvas.create_text(
            cx, cy, text="MED",
            fill="#003a33", font=("Consolas", max(7, self._cellSize // 6), "bold")
        )

    # ------------------------------------------------------------------ #
    #  Getters                                                             #
    # ------------------------------------------------------------------ #

    def getSimSettings(self):
        return {
            "gridSize":         int(self._gridSizeVar.get()),
            "floodProbability": float(self._floodProbVar.get()),
            "stepDelay":        float(self._stepDelayVar.get()),
            "residentialHops":  self._readIntVar(self._residentialHopsVar, 3),
            "powerplantHops":   self._readIntVar(self._powerplantHopsVar, 2),
            "buildings": {
                "Hospital":       int(self._buildingVars["Hospital"].get()),
                "School":         int(self._buildingVars["School"].get()),
                "Industrial":     int(self._buildingVars["Industrial"].get()),
                "Residential":    int(self._buildingVars["Residential"].get()),
                "PowerPlant":     int(self._buildingVars["PowerPlant"].get()),
                "AmbulanceDepot": int(self._buildingVars["AmbulanceDepot"].get()),
            }
        }

    def _readIntVar(self, var, fallback):
        try:
            return int(var.get())
        except (ValueError, tk.TclError):
            return fallback

    def _readStepDelay(self):
        try:
            return float(self._stepDelayVar.get())
        except (ValueError, tk.TclError):
            return 0.4
