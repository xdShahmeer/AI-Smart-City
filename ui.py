import os
import tkinter as tk
from PIL import Image, ImageTk

from eventLog import EventLog


# asset config

ASSETS_DIR = "assets"

# building sprites
BUILDING_SPRITES = {
    "Hospital":       "building1",
    "School":         "school",
    "Residential":    "building2",
    "Industrial":     "factory2",
    "PowerPlant":     "building1",
    "AmbulanceDepot": "building2",
}

# ground sprites
GROUND_VARIETY = ["grass", "wavy_grass", "flower_ground", "stoned_grass"]

# ambulance sprite
AMBULANCE_SPRITE = "ambulance"

# medical team sprite
MEDICAL_TEAM_SPRITE = "medical_team"

# tree strip
TREE_SPRITE_FILE  = "spr_tree_animated"
TREE_FRAME_WIDTH  = 64
TREE_FRAME_HEIGHT = 64


# layout constants

# cell margin
MARGIN = 4

# canvas target
CANVAS_TARGET = 600

# cell size range
MIN_CELL_SIZE = 20
MAX_CELL_SIZE = 50

# animation tick
ANIMATION_INTERVAL_MS = 100


# tool text
TOOL_DESCRIPTIONS = {
    "inspect":   "Click any cell to view its stats in Node Info.",
    "flood":     "Click two adjacent cells to flood the road between them.",
    "emergency": "Click any accessible cell to dispatch a civilian emergency there.",
}


# fonts

FONT_TITLE  = ("Segoe UI Semibold", 10)
FONT_BODY   = ("Segoe UI", 10)
FONT_SMALL  = ("Segoe UI", 9)
FONT_HINT   = ("Segoe UI", 9, "italic")
FONT_BUTTON = ("Segoe UI Semibold", 10)
FONT_STATUS = ("Consolas", 11, "bold")
FONT_LABEL  = ("Segoe UI", 8, "bold")
FONT_LEGEND = ("Consolas", 9, "bold")
FONT_MONO   = ("Consolas", 10)


# colours

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
    "road_not_built":   "#3a3a5a",
    "medicalTeam":      "#00ffcc",
    "medicalPath":      "#ffd966",
    "routeA":           "#ff6600",
    "routeB":           "#00cc44",
    "btnPrimary":       "#3d8bd9",
    "btnSecondary":     "#5a5a78",
    "btnAccent":        "#f0a830",
    "btnPlay":          "#22a85d",
    "btnPause":         "#d94545",
    "policeOfficer":    "#3873d9",
}


# helpers

def isTreeCell(row, col):
    # tree cell check
    return ((row * 17) + (col * 31)) % 7 == 0


def pickGroundIndex(row, col, numVariants):
    # pick ground index
    if numVariants <= 0:
        return 0
    return ((row * 7) + (col * 13)) % numVariants


# main ui class

class AppUI:
    # single window ui in three columns

    def __init__(self, controller):
        self._controller = controller

        # ui state
        self._overlayMode     = None
        self._selectedNode    = None
        self._autoPlaying     = False
        self._coverageDist    = {}
        self._coverageMaxDist = 0.0
        self._isRunning       = True

        # mouse tool
        self._toolMode       = "inspect"
        self._floodFirstNode = None

        # cell size
        self._cellSize = self._computeCellSize(controller.getGraph().cols)

        # widgets
        self._tkRoot        = None
        self._canvas        = None
        self._eventLog      = None
        self._nodeInfoText  = None
        self._playPauseBtn  = None
        self._toolModeVar   = None
        self._toolDescLabel = None
        self._statusLabel   = None

        # setting vars
        self._gridSizeVar            = None
        self._floodProbVar           = None
        self._stepDelayVar           = None
        self._buildingVars           = {}
        self._residentialHopsVar     = None
        self._powerplantHopsVar      = None
        self._industrialAdjacencyVar = None

        # sprite cache
        self._buildingSprites   = {}
        self._groundSprites     = []
        self._ambulanceSprite   = None
        self._medicalTeamSprite = None
        self._treeFrames        = []
        self._treeFrameIndex    = 0

    # public lifecycle

    def setup(self):
        # build window and load sprites
        self._buildWindow()
        self._loadSprites()
        self._render()
        self._refreshStatus()
        self.addLog("CityMind started. Configure settings and press Generate City.")

    def run(self):
        self._tkRoot.protocol("WM_DELETE_WINDOW", self._onClose)
        self._scheduleTick()
        self._tkRoot.mainloop()

    def addLog(self, text):
        # add log line
        if self._eventLog is not None:
            self._eventLog.addEntry(text)

    # window build

    def _buildWindow(self):
        graph = self._controller.getGraph()

        self._tkRoot = tk.Tk()
        self._tkRoot.title("CityMind -- Urban Intelligence System")
        self._tkRoot.configure(bg=COLOURS["bg"])

        # column 1
        leftFrame = tk.Frame(self._tkRoot, bg=COLOURS["bg"])
        leftFrame.pack(side=tk.LEFT, fill=tk.Y, padx=8, pady=8)

        self._statusLabel = tk.Label(
            leftFrame, text="", fg=COLOURS["accent"], bg=COLOURS["panel_alt"],
            font=FONT_STATUS, anchor="w",
            padx=12, pady=10, relief=tk.FLAT
        )
        self._statusLabel.pack(side=tk.TOP, fill=tk.X, pady=(0, 8))

        canvasWidth  = self._cellSize * graph.cols
        canvasHeight = self._cellSize * graph.rows
        self._canvas = tk.Canvas(
            leftFrame, width=canvasWidth, height=canvasHeight,
            bg=COLOURS["bg"], highlightthickness=0
        )
        self._canvas.pack(side=tk.TOP)
        self._canvas.bind("<Button-1>", self._onCanvasClick)

        # column 2
        controlFrame = tk.Frame(self._tkRoot, bg=COLOURS["bg"], width=320)
        controlFrame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 8), pady=8)
        controlFrame.pack_propagate(False)

        self._buildSettingsPanel(controlFrame)
        self._buildConstraintsPanel(controlFrame)
        self._buildToolPanel(controlFrame)
        self._buildOverlayButtons(controlFrame)
        self._buildNodeInfoPanel(controlFrame)

        # column 3
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

        # grid size
        self._gridSizeVar = tk.StringVar(value=str(self._controller.getGraph().cols))
        self._labeledEntry(frame, "Grid Size:", self._gridSizeVar, row=0)

        # building counts
        defaults = self._controller.getDefaultCounts()
        orderedTypes = ["Hospital", "School", "Industrial", "Residential",
                        "PowerPlant", "AmbulanceDepot"]
        for index in range(len(orderedTypes)):
            buildingType = orderedTypes[index]
            defaultValue = str(defaults.get(buildingType, 0))
            entryVar     = tk.StringVar(value=defaultValue)
            self._buildingVars[buildingType] = entryVar
            self._labeledEntry(frame, f"{buildingType}:", entryVar, row=index + 1)

        # flood probability
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

        # step delay
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

        # control buttons
        buttonFrame = tk.Frame(frame, bg=COLOURS["panel"])
        buttonFrame.grid(row=10, column=0, columnspan=2, pady=(10, 2), sticky="ew")

        topRow = tk.Frame(buttonFrame, bg=COLOURS["panel"])
        topRow.pack(side=tk.TOP, fill=tk.X, pady=(0, 4))
        bottomRow = tk.Frame(buttonFrame, bg=COLOURS["panel"])
        bottomRow.pack(side=tk.TOP, fill=tk.X)

        generateButton = self._makeButton(
            topRow, "Generate City", self._onStartClicked, COLOURS["btnPrimary"]
        )
        generateButton.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)

        resetButton = self._makeButton(
            topRow, "Reset", self._onResetClicked, COLOURS["btnSecondary"]
        )
        resetButton.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)

        stepButton = self._makeButton(
            bottomRow, "Step", self._onStepClicked, COLOURS["btnAccent"]
        )
        stepButton.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)

        self._playPauseBtn = self._makeButton(
            bottomRow, "Play", self._onPlayPauseClicked, COLOURS["btnPlay"]
        )
        self._playPauseBtn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)

    def _makeButton(self, parent, text, command, backgroundColour):
        return tk.Button(
            parent, text=text, command=command,
            bg=backgroundColour, fg="white",
            activebackground=backgroundColour, activeforeground="white",
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

        self._industrialAdjacencyVar = tk.BooleanVar(value=True)
        tk.Checkbutton(
            frame, text="Industrial cannot neighbour School/Hospital",
            variable=self._industrialAdjacencyVar,
            bg=COLOURS["panel"], fg=COLOURS["text"],
            selectcolor=COLOURS["panel_alt"], activebackground=COLOURS["panel"],
            activeforeground=COLOURS["text"], font=FONT_SMALL,
            cursor="hand2", anchor="w", justify="left"
        ).grid(row=2, column=0, columnspan=2, sticky="w", pady=(4, 0))

        tk.Label(
            frame,
            text="Edit these and re-Generate to test the city under different rules.",
            fg=COLOURS["text_dim"], bg=COLOURS["panel"], font=FONT_HINT,
            anchor="w", justify="left", wraplength=280, padx=2, pady=4
        ).grid(row=3, column=0, columnspan=2, sticky="w", pady=(6, 0))

    def _buildLegendPanel(self, parent):
        frame = tk.LabelFrame(
            parent, text=" Legend ", fg=COLOURS["text"], bg=COLOURS["panel"],
            font=FONT_TITLE, padx=10, pady=6,
            relief=tk.FLAT, borderwidth=0
        )
        frame.pack(side=tk.TOP, fill=tk.X, pady=(0, 8))

        legendItems = [
            ("MED", COLOURS["medicalTeam"],   "Medical team"),
            ("AMB", "#e54a4a",                "Ambulance"),
            ("P",   COLOURS["policeOfficer"], "Police officer (top 10 risk)"),
            ("!",   "#ff3030",                "Active emergency"),
            ("---", COLOURS["road_flooded"],  "Flooded road"),
            ("---", COLOURS["routeA"],        "Route A (primary corridor)"),
            ("---", COLOURS["routeB"],        "Route B (backup corridor)"),
            ("- -", COLOURS["medicalPath"],   "Planned A* path"),
        ]

        for symbol, colour, description in legendItems:
            row = tk.Frame(frame, bg=COLOURS["panel"])
            row.pack(side=tk.TOP, fill=tk.X, pady=2)

            tk.Label(
                row, text=symbol, fg=colour, bg=COLOURS["panel"],
                font=FONT_LEGEND, width=5, anchor="w"
            ).pack(side=tk.LEFT)
            tk.Label(
                row, text=description, fg=COLOURS["text"], bg=COLOURS["panel"],
                font=FONT_SMALL, anchor="w"
            ).pack(side=tk.LEFT)

    def _buildToolPanel(self, parent):
        # mouse tool panel
        frame = tk.LabelFrame(
            parent, text=" Mouse Tool ", fg=COLOURS["text"], bg=COLOURS["panel"],
            font=FONT_TITLE, padx=10, pady=6,
            relief=tk.FLAT, borderwidth=0
        )
        frame.pack(side=tk.TOP, fill=tk.X, pady=(0, 8))

        radioRow = tk.Frame(frame, bg=COLOURS["panel"])
        radioRow.pack(side=tk.TOP, fill=tk.X)

        self._toolModeVar = tk.StringVar(value="inspect")

        toolEntries = [("Inspect", "inspect"), ("Flood", "flood"), ("Emergency", "emergency")]
        for label, mode in toolEntries:
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

        # one method per overlay
        roadsButton = self._makeOverlayButton(row, "Road Network", self._onRoadsOverlay)
        roadsButton.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)

        coverageButton = self._makeOverlayButton(row, "Coverage", self._onCoverageOverlay)
        coverageButton.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)

        crimeButton = self._makeOverlayButton(row, "Crime Risk", self._onCrimeOverlay)
        crimeButton.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)

        tk.Label(
            frame,
            text="Toggle road colour-coding, ambulance reach heatmap, or crime risk gradient.",
            fg=COLOURS["text_dim"], bg=COLOURS["panel"], font=FONT_HINT,
            anchor="w", justify="left", wraplength=280, padx=2, pady=4
        ).pack(side=tk.TOP, fill=tk.X, pady=(6, 0))

    def _makeOverlayButton(self, parent, label, command):
        return tk.Button(
            parent, text=label, command=command,
            bg=COLOURS["panel_alt"], fg=COLOURS["text"],
            activebackground=COLOURS["accent"], activeforeground=COLOURS["bg"],
            relief=tk.FLAT, borderwidth=0, padx=10, pady=6,
            font=FONT_SMALL, cursor="hand2"
        )

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

    # cell size and sprite loading

    def _computeCellSize(self, gridSize):
        # fit the grid to the target size
        if gridSize < 1:
            gridSize = 1
        size = CANVAS_TARGET // gridSize
        if size < MIN_CELL_SIZE:
            return MIN_CELL_SIZE
        if size > MAX_CELL_SIZE:
            return MAX_CELL_SIZE
        return size

    def _loadSprites(self):
        # load sprites for current size
        spriteSize = self._cellSize - MARGIN * 2
        if spriteSize < 8:
            spriteSize = 8

        baseDir   = os.path.dirname(os.path.abspath(__file__))
        assetsDir = os.path.join(baseDir, ASSETS_DIR)

        # building sprites
        self._buildingSprites = {}
        for buildingType in BUILDING_SPRITES:
            tileName = BUILDING_SPRITES[buildingType]
            self._buildingSprites[buildingType] = self._loadSquareSprite(
                assetsDir, tileName, spriteSize
            )

        # ground sprites
        self._groundSprites = []
        for tileName in GROUND_VARIETY:
            sprite = self._loadSquareSprite(assetsDir, tileName, spriteSize)
            if sprite is not None:
                self._groundSprites.append(sprite)

        # ambulance sprite
        ambulanceIconSize = self._cellSize // 2
        if ambulanceIconSize < 12:
            ambulanceIconSize = 12
        self._ambulanceSprite = self._loadSquareSprite(
            assetsDir, AMBULANCE_SPRITE, ambulanceIconSize
        )

        # medical team sprite
        medTeamIconSize = self._cellSize // 2
        if medTeamIconSize < 12:
            medTeamIconSize = 12
        self._medicalTeamSprite = self._loadSquareSprite(
            assetsDir, MEDICAL_TEAM_SPRITE, medTeamIconSize
        )

        # tree frames
        self._treeFrames = self._loadTreeFrames(assetsDir, spriteSize)
        self._treeFrameIndex = 0

    def _loadSquareSprite(self, folder, tileName, size):
        # load one sprite
        path = os.path.join(folder, f"{tileName}.png")
        try:
            raw    = Image.open(path).convert("RGBA")
            scaled = raw.resize((size, size), Image.NEAREST)
            return ImageTk.PhotoImage(scaled)
        except Exception:
            return None

    def _loadTreeFrames(self, folder, size):
        # load tree frames
        path = os.path.join(folder, f"{TREE_SPRITE_FILE}.png")
        try:
            strip = Image.open(path).convert("RGBA")
        except Exception:
            return []

        stripWidth, stripHeight = strip.size
        if stripHeight < TREE_FRAME_HEIGHT:
            return []

        numFrames = stripWidth // TREE_FRAME_WIDTH
        frames = []
        for frameIndex in range(numFrames):
            leftX  = frameIndex * TREE_FRAME_WIDTH
            rightX = leftX + TREE_FRAME_WIDTH
            cropBox = (leftX, 0, rightX, TREE_FRAME_HEIGHT)
            frameImage = strip.crop(cropBox)
            frameImage = frameImage.resize((size, size), Image.NEAREST)
            frames.append(ImageTk.PhotoImage(frameImage))
        return frames

    def _resizeCanvasIfNeeded(self):
        # resize canvas if needed
        graph        = self._controller.getGraph()
        newCellSize  = self._computeCellSize(max(graph.rows, graph.cols))
        sizeChanged  = newCellSize != self._cellSize

        self._cellSize = newCellSize

        canvasWidth  = self._cellSize * graph.cols
        canvasHeight = self._cellSize * graph.rows
        self._canvas.config(width=canvasWidth, height=canvasHeight)

        if sizeChanged:
            self._loadSprites()

        # refresh window size
        self._tkRoot.update_idletasks()
        self._tkRoot.geometry("")

    # animation and auto step

    def _scheduleTick(self):
        # repeat tick
        if not self._isRunning:
            return

        # auto step
        if self._autoPlaying:
            stepDelay = self._readStepDelay()
            events = self._controller.autoStepIfDue(stepDelay)
            if len(events) > 0:
                self._refreshStatus()
            if self._controller.isFinished():
                self._setAutoPlaying(False)

        # advance tree frame
        if len(self._treeFrames) > 0:
            self._treeFrameIndex = (self._treeFrameIndex + 1) % len(self._treeFrames)

        # redraw screen
        self._render()

        self._tkRoot.after(ANIMATION_INTERVAL_MS, self._scheduleTick)

    # button callbacks

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
        self.addLog("Simulation reset. Press Generate City to begin.")
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
            self._playPauseBtn.config(text="Pause", bg=COLOURS["btnPause"])
        else:
            self._playPauseBtn.config(text="Play", bg=COLOURS["btnPlay"])

    def _onRoadsOverlay(self):
        self._toggleOverlay("roads")

    def _onCoverageOverlay(self):
        self._toggleOverlay("coverage")

    def _onCrimeOverlay(self):
        self._toggleOverlay("crime")

    def _toggleOverlay(self, mode):
        if self._overlayMode == mode:
            self._overlayMode = None
        else:
            self._overlayMode = mode
            if mode == "coverage":
                self._refreshCoverage()
        self._render()

    def _refreshCoverage(self):
        # refresh coverage distances
        self._coverageDist = self._controller.getCoverageDistances()

        # find max distance
        maxDistance = 0.0
        for distance in self._coverageDist.values():
            if distance == float('inf'):
                continue
            if distance > maxDistance:
                maxDistance = distance
        self._coverageMaxDist = maxDistance

    def _onCanvasClick(self, event):
        col  = event.x // self._cellSize
        row  = event.y // self._cellSize
        node = (row, col)

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
        # two click flood
        if self._floodFirstNode is None:
            self._floodFirstNode = node
            self.addLog(f"Flood tool: selected {node}, click an adjacent cell to flood the road.")
            self._render()
            return

        firstNode = self._floodFirstNode
        self._floodFirstNode = None

        if node == firstNode:
            self.addLog("Flood tool: same cell clicked twice -- selection cleared.")
            self._render()
            return

        floodEvent = self._controller.floodEdge(firstNode, node)
        if floodEvent is None:
            self.addLog(f"Flood tool: {firstNode} and {node} are not adjacent or already flooded.")
        else:
            self.addLog(floodEvent)

        self._render()

    def _handleEmergencyClick(self, node):
        emergencyEvent = self._controller.addEmergency(node)
        if emergencyEvent is None:
            self.addLog(
                f"Emergency tool: cannot add at {node} "
                f"(already queued, current position, or inaccessible)."
            )
        else:
            self.addLog(emergencyEvent)
            self._refreshStatus()
        self._render()

    def _onToolModeChanged(self):
        self._toolMode = self._toolModeVar.get()
        self._floodFirstNode = None
        self._toolDescLabel.config(text=TOOL_DESCRIPTIONS[self._toolMode])
        self._render()

    def _showNodeInfo(self, info):
        textLines = []
        textLines.append(f"Node: {info['node']}")
        textLines.append(f"Type: {info['type']}")
        textLines.append(f"Population: {info['population']}")
        textLines.append(f"Risk Index: {info['riskIndex']}")
        textLines.append(f"Accessible: {info['accessible']}")
        text = chr(10).join(textLines)
        self._nodeInfoText.config(state=tk.NORMAL)
        self._nodeInfoText.delete("1.0", tk.END)
        self._nodeInfoText.insert(tk.END, text)
        self._nodeInfoText.config(state=tk.DISABLED)

    def _onClose(self):
        self._isRunning = False
        self._tkRoot.destroy()

    # status bar

    def _refreshStatus(self):
        # refresh status line
        if self._statusLabel is None:
            return

        sim   = self._controller.getSimulation()
        state = self._controller.getRouterState()

        if not sim.setupDone:
            self._statusLabel.config(
                text="Press Generate City to build a city and begin the 20-step simulation."
            )
            return

        if state is not None:
            reachedCount = len(state.reached)
            skippedCount = len(state.skipped)
            pendingCount = len(state.civilians) - state.currentTarget
        else:
            reachedCount = 0
            skippedCount = 0
            pendingCount = 0

        ambulanceCount = len(self._controller.getGraph().ambulancePositions)

        if sim.currentStep <= sim.totalSteps:
            stepText = f"Step {sim.currentStep}/{sim.totalSteps}"
        else:
            extraSteps = sim.currentStep - sim.totalSteps
            stepText = f"Step {sim.currentStep}/{sim.totalSteps} +{extraSteps} (extended)"

        self._statusLabel.config(
            text=(
                f"{stepText}   "
                f"Civilians: {reachedCount} reached / "
                f"{pendingCount} pending / {skippedCount} skipped   "
                f"Ambulances: {ambulanceCount}"
            )
        )

    # rendering

    def _nodeCentre(self, node):
        nodeRow, nodeCol = node
        centreX = nodeCol * self._cellSize + self._cellSize // 2
        centreY = nodeRow * self._cellSize + self._cellSize // 2
        return (centreX, centreY)

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
        self._drawPoliceOfficers()
        self._drawEmergencies()
        self._drawAmbulances()
        self._drawMedicalTeam()
        self._drawFloodSelection()

    def _drawNodes(self):
        graph     = self._controller.getGraph()
        showLabel = self._cellSize >= 30

        for node in graph.nodes:
            data = graph.nodes[node]
            row, col = node

            cellX     = col * self._cellSize + MARGIN
            cellY     = row * self._cellSize + MARGIN
            cellWidth = self._cellSize - MARGIN * 2

            if self._overlayMode is not None:
                colour = self._nodeColour(node, data)
                self._canvas.create_rectangle(
                    cellX, cellY,
                    cellX + cellWidth, cellY + cellWidth,
                    fill=colour, outline=""
                )
            else:
                self._drawCellSprite(node, data, cellX, cellY, cellWidth)

            if showLabel and data["type"] != "Empty":
                label = data["type"][:3].upper()
                self._canvas.create_text(
                    cellX + 2, cellY + 2, anchor=tk.NW, text=label,
                    fill="white", font=FONT_LABEL
                )

    def _drawCellSprite(self, node, data, cellX, cellY, cellWidth):
        # draw cell sprite
        if data["type"] == "Empty":
            self._drawEmptyCell(node, cellX, cellY, cellWidth)
            return

        buildingSprite = self._buildingSprites.get(data["type"])
        if buildingSprite is not None:
            self._canvas.create_image(cellX, cellY, anchor=tk.NW, image=buildingSprite)
            return

        # fallback colour
        fallbackColour = COLOURS.get(data["type"], COLOURS["Empty"])
        self._canvas.create_rectangle(
            cellX, cellY,
            cellX + cellWidth, cellY + cellWidth,
            fill=fallbackColour, outline=""
        )

    def _drawEmptyCell(self, node, cellX, cellY, cellWidth):
        row, col = node

        # draw ground first
        if len(self._groundSprites) > 0:
            groundIndex = pickGroundIndex(row, col, len(self._groundSprites))
            groundSprite = self._groundSprites[groundIndex]
            self._canvas.create_image(cellX, cellY, anchor=tk.NW, image=groundSprite)
        else:
            self._canvas.create_rectangle(
                cellX, cellY,
                cellX + cellWidth, cellY + cellWidth,
                fill=COLOURS["Empty"], outline=""
            )

        # layer trees on top
        treeAvailable = len(self._treeFrames) > 0
        bigEnough     = self._cellSize >= 24
        if treeAvailable and bigEnough and isTreeCell(row, col):
            currentFrame = self._treeFrames[self._treeFrameIndex]
            self._canvas.create_image(cellX, cellY, anchor=tk.NW, image=currentFrame)

    def _nodeColour(self, node, data):
        if self._overlayMode == "coverage":
            distance = self._coverageDist.get(node, float('inf'))
            return self._coverageGradient(distance, self._coverageMaxDist)

        if self._overlayMode == "crime":
            return self._crimeGradient(data["riskIndex"])

        return COLOURS.get(data["type"], COLOURS["Empty"])

    def _crimeGradient(self, riskIndex):
        # crime colour scale over [1.0, 3.0] to match risk-shift range
        if riskIndex < 1.0:
            risk = 1.0
        elif riskIndex > 3.0:
            risk = 3.0
        else:
            risk = riskIndex

        if risk <= 2.0:
            progress = (risk - 1.0) / 1.0
            redValue   = int(255 * progress)
            greenValue = 200
        else:
            progress = (risk - 2.0) / 1.0
            redValue   = 255
            greenValue = int(200 * (1.0 - progress))

        return f"#{redValue:02x}{greenValue:02x}00"

    def _coverageGradient(self, distance, maxDistance):
        # coverage colour scale
        if distance == float('inf'):
            return "#660000"
        if maxDistance <= 0:
            return "#00c800"

        progress = distance / maxDistance
        if progress > 1.0:
            progress = 1.0

        if progress <= 0.5:
            ramp = progress * 2
            redValue   = int(255 * ramp)
            greenValue = 200
        else:
            ramp = (progress - 0.5) * 2
            redValue   = 255
            greenValue = int(200 * (1.0 - ramp))

        return f"#{redValue:02x}{greenValue:02x}00"

    def _drawRoads(self):
        graph = self._controller.getGraph()
        for edge in graph.edges:
            edgeData = graph.edges[edge]
            nodeA, nodeB = edge

            colour = self._roadColour(graph, nodeA, nodeB, edgeData)
            if colour is None:
                continue

            # thin non built roads
            if self._overlayMode == "roads" and not edgeData.get("built", True):
                lineWidth = 1
            else:
                lineWidth = 2

            startX, startY = self._nodeCentre(nodeA)
            endX,   endY   = self._nodeCentre(nodeB)
            self._canvas.create_line(
                startX, startY, endX, endY, fill=colour, width=lineWidth
            )

    def _roadColour(self, graph, nodeA, nodeB, edgeData):
        if edgeData["blocked"]:
            return COLOURS["road_flooded"]

        if self._overlayMode == "roads":
            if not edgeData.get("built", True):
                return COLOURS["road_not_built"]
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
        startX, startY = self._nodeCentre(nodeA)
        endX,   endY   = self._nodeCentre(nodeB)
        self._canvas.create_line(
            startX, startY, endX, endY, fill=colour, width=4
        )

    def _drawMedicalPath(self):
        # draw planned path
        state = self._controller.getRouterState()
        if state is None or len(state.currentPath) == 0:
            return

        chain = [state.currentPos]
        for nodeOnPath in state.currentPath:
            chain.append(nodeOnPath)

        for index in range(len(chain) - 1):
            startX, startY = self._nodeCentre(chain[index])
            endX,   endY   = self._nodeCentre(chain[index + 1])
            self._canvas.create_line(
                startX, startY, endX, endY,
                fill=COLOURS["medicalPath"], width=3, dash=(4, 3)
            )

    def _drawAmbulances(self):
        # draw ambulances
        graph = self._controller.getGraph()

        for position in graph.ambulancePositions:
            centreX, centreY = self._nodeCentre(position)
            if self._ambulanceSprite is not None:
                self._canvas.create_image(
                    centreX, centreY, anchor=tk.CENTER, image=self._ambulanceSprite
                )
            else:
                self._drawAmbulanceFallback(centreX, centreY)

            if self._cellSize >= 35:
                labelY = centreY + (self._cellSize // 3)
                self._canvas.create_text(
                    centreX, labelY, text="AMB",
                    fill="white", font=("Consolas", 7, "bold")
                )

    def _drawAmbulanceFallback(self, centreX, centreY):
        # fallback ambulance
        size = self._cellSize // 4
        if size < 8:
            size = 8
        self._canvas.create_rectangle(
            centreX - size, centreY - size,
            centreX + size, centreY + size,
            fill="white", outline="#cc0000", width=1
        )
        self._canvas.create_line(
            centreX - size + 2, centreY,
            centreX + size - 2, centreY,
            fill="#cc0000", width=2
        )
        self._canvas.create_line(
            centreX, centreY - size + 2,
            centreX, centreY + size - 2,
            fill="#cc0000", width=2
        )

    def _drawPoliceOfficers(self):
        # draw police badges
        graph = self._controller.getGraph()
        if len(graph.policeOfficers) == 0:
            return

        badgeRadius = self._cellSize // 6
        if badgeRadius < 5:
            badgeRadius = 5

        for node in graph.policeOfficers:
            centreX, centreY = self._nodeCentre(node)

            # move badge to corner
            badgeX = centreX + (self._cellSize // 2) - badgeRadius - 3
            badgeY = centreY - (self._cellSize // 2) + badgeRadius + 3

            self._canvas.create_oval(
                badgeX - badgeRadius, badgeY - badgeRadius,
                badgeX + badgeRadius, badgeY + badgeRadius,
                fill=COLOURS["policeOfficer"], outline="white", width=1
            )

            if self._cellSize >= 35:
                fontSize = badgeRadius
                if fontSize < 7:
                    fontSize = 7
                self._canvas.create_text(
                    badgeX, badgeY, text="P", fill="white",
                    font=("Consolas", fontSize, "bold")
                )

    def _drawEmergencies(self):
        # draw emergency rings
        ringRadius = self._cellSize // 3
        if ringRadius < 10:
            ringRadius = 10

        textSize = self._cellSize // 3
        if textSize < 10:
            textSize = 10

        for node in self._controller.getActiveEmergencies():
            centreX, centreY = self._nodeCentre(node)
            self._canvas.create_oval(
                centreX - ringRadius, centreY - ringRadius,
                centreX + ringRadius, centreY + ringRadius,
                outline="#ff3030", width=2
            )
            self._canvas.create_text(
                centreX, centreY, text="!", fill="#ff3030",
                font=("Consolas", textSize, "bold")
            )

    def _drawFloodSelection(self):
        if self._floodFirstNode is None:
            return
        centreX, centreY = self._nodeCentre(self._floodFirstNode)
        ringRadius = self._cellSize // 2 - 2
        self._canvas.create_rectangle(
            centreX - ringRadius, centreY - ringRadius,
            centreX + ringRadius, centreY + ringRadius,
            outline="#00bfff", width=3
        )

    def _drawMedicalTeam(self):
        # draw medical team with sprite fallback
        state = self._controller.getRouterState()
        if state is None or state.currentPos is None:
            return

        centreX, centreY = self._nodeCentre(state.currentPos)

        if self._medicalTeamSprite is not None:
            self._canvas.create_image(
                centreX, centreY, anchor=tk.CENTER, image=self._medicalTeamSprite
            )
            return

        size = self._cellSize // 3
        if size < 10:
            size = 10

        self._canvas.create_rectangle(
            centreX - size, centreY - size,
            centreX + size, centreY + size,
            fill=COLOURS["medicalTeam"], outline="#005a4f", width=2
        )

        labelFontSize = self._cellSize // 6
        if labelFontSize < 7:
            labelFontSize = 7
        self._canvas.create_text(
            centreX, centreY, text="MED",
            fill="#003a33", font=("Consolas", labelFontSize, "bold")
        )

    # getters

    def getSimSettings(self):
        return {
            "gridSize":                int(self._gridSizeVar.get()),
            "floodProbability":        float(self._floodProbVar.get()),
            "stepDelay":               float(self._stepDelayVar.get()),
            "residentialHops":         self._readIntVar(self._residentialHopsVar, 3),
            "powerplantHops":          self._readIntVar(self._powerplantHopsVar, 2),
            "industrialAdjacencyRule": bool(self._industrialAdjacencyVar.get()),
            "buildings": {
                "Hospital":       int(self._buildingVars["Hospital"].get()),
                "School":         int(self._buildingVars["School"].get()),
                "Industrial":     int(self._buildingVars["Industrial"].get()),
                "Residential":    int(self._buildingVars["Residential"].get()),
                "PowerPlant":     int(self._buildingVars["PowerPlant"].get()),
                "AmbulanceDepot": int(self._buildingVars["AmbulanceDepot"].get()),
            }
        }

    def _readIntVar(self, variable, fallback):
        try:
            return int(variable.get())
        except (ValueError, tk.TclError):
            return fallback

    def _readStepDelay(self):
        try:
            return float(self._stepDelayVar.get())
        except (ValueError, tk.TclError):
            return 0.4
