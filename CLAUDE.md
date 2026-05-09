# CityMind — Project Reference Guide

This file is the single source of truth for all implementation decisions made by the group. Every module must be written to be consistent with the decisions recorded here. Read this before writing any code.

---

## Group

- Zarrar Nadeem — 24i-0735
- Shahmeer Zubair — 24i-0580
- Raahim Babar — 24i-0561

**Deadline:** 10th May, 11:59 PM

---

## Project Summary

CityMind is a grid-based urban intelligence system. The city is modeled as a graph where every grid coordinate is a node and every connection between adjacent nodes is a road (edge). Five AI modules operate on this shared graph to solve city planning, routing, optimization, and prediction challenges. All modules share one single city graph object — no module keeps its own copy.

---

## Session Checkpoint — Progress Tracker

Live record of where the project stands. Update this at the end of every session so the next one starts with full context. Tick boxes when work lands.

### Done

- [x] `cityGraph.py` — shared graph foundation (nodes, edges, adjacency, getters/setters at bottom)
- [x] `csp.py` — Challenge 1 CSP layout planner (backtracking + MRV + LCV + forward checking + minimum-conflict fallback)
- [x] `mst.py` — Challenge 2 Kruskal's MST + dual independent A* corridors between Primary Hospital and Primary Depot
- [x] `crime.py` — Challenge 5 K-Means clustering then KNN classifier writing `riskIndex` back to the graph
- [x] `ga.py` — Challenge 3 Genetic Algorithm with Dijkstra-based fitness for ambulance placement
- [x] `astar.py` — Challenge 4 A* router with Manhattan heuristic, sequential civilian targeting, dynamic reroute on flood
- [x] `simulation.py` — 20-step loop wiring CSP → MST → crime → GA → A*; `rebuild` for clean restarts
- [x] `eventLog.py` — Tkinter Text widget event log with scrollback
- [x] `appController.py` — controller layer between UI and simulation (proper OOP boundary)
- [x] `ui.py` — single-window Tk UI with Canvas grid, sprite support via PIL, settings, overlays, info panel, event log
- [x] `main.py` — thin entry point: build controller, build UI, wire event listener, hand off to Tk
- [x] **Single-window app**: dropped pygame; the whole interface lives in one Tk root
- [x] **Proper OOP**: `AppUI` only ever calls `AppController`; no direct simulation/graph access from UI
- [x] CityGraph getters/setters moved to the bottom of the class (style rule)
- [x] A* renamed `tentativeG` → `nextCost` (style rule: no `tentativeCost` naming)
- [x] Kenney Tiny Town sprites loaded via `PIL.ImageTk.PhotoImage`, cached on the UI instance
- [x] **Manual flood tool** — Mouse Tool radio "Flood": two-click adjacent cells to flood the connecting road, with a blue selection ring after the first click
- [x] **Emergency toggle tool** — Mouse Tool radio "Emergency": click any accessible node to append a civilian to the medical team's queue
- [x] **Active emergency markers** — pending civilians render as red `!` rings on the grid
- [x] **Crime heatmap** — proper green → yellow → red gradient over `riskIndex` ∈ [1.0, 2.5] (no more solid bands)
- [x] **Coverage overlay** — multi-source weighted Dijkstra distances via `AppController.getCoverageDistances()`; recomputes every render so floods reflect immediately
- [x] **Ambulance icon** — white square + red cross (reads as a medical vehicle without needing a sprite asset)
- [x] **Controller surface for manual interactions** — `floodEdge`, `addEmergency`, `getActiveEmergencies`, `getCoverageDistances` on `AppController`; the UI never reaches into `Simulation` or `CityGraph` for these operations
- [x] **Three-column layout** — left = status bar + city grid, middle = controls (Settings, Constraints, Mouse Tool, Overlays, Node Info), right = Legend + event log. The log is visible the moment the window opens.
- [x] **Dynamic cell size** — `_computeCellSize` targets a ~600 px canvas; the canvas + sprites resize on Generate, and the Tk root re-snaps to its natural size with `geometry("")` so other panels never get cropped or overlapped.
- [x] **Status bar** — top-of-canvas line that shows `Step X/20` plus civilians reached/pending/skipped and ambulance count. Updates on every step.
- [x] **Bigger labelled icons** — medical team is a cyan square with bold "MED"; ambulances are white squares with a red cross and "AMB" label below at larger zooms. Path overlay is a yellow dashed line showing the planned A* route.
- [x] **Tool description text** — one-line help under the Mouse Tool radio group, plus a static hint under Overlays.
- [x] **Legend panel** — compact static legend in the right column (above the event log) keyed to MED, ambulance, emergency, flooded road, route A, route B, and the planned A* path.
- [x] **"Generate City" button** — Start renamed to "Generate City" to match the PDF mockup wording.
- [x] **Sim continues past 20 steps when emergencies are added** — `addEmergency` extends `Simulation.totalSteps` to `currentStep + 20` if the budget already ran out, so the team can actually respond. Auto-play resumes on the next tick.
- [x] **Live modification readiness** — CSP proximity hops are module-level constants (`RESIDENTIAL_MAX_HOPS`, `POWERPLANT_MAX_HOPS`); `runCSP(... residentialHops=, powerplantHops=)` overrides them per run. UI exposes them in a "Constraints" panel; `Simulation.rebuild` and `AppController.startSimulation` thread the values through.
- [x] **Industrial-adjacency rule is live-modifiable** — `INDUSTRIAL_ADJACENCY_RULE` flag in `csp.py`, `runCSP(... industrialAdjacencyRule=)` override, checkbox in the Constraints panel.
- [x] **10 police officers deployed** — `crime.deployPoliceOfficers` greedy top-10 by `riskIndex`; rendered as blue "P" badges and listed in the legend.
- [x] **K-Means is no longer dead code** — `crime.runCrime` now cross-validates K-Means clusters against the synthetic formula labels and logs the agreement percentage and per-tier counts. KNN still trains on the synthetic dataset per spec.
- [x] **MST events flow through the event log** — `mst.buildRoadNetwork` returns `(routeA, routeB, events)`; the controller forwards them to the UI instead of stdout.
- [x] **`astar.stepRouter` cleaned up** — dropped the unused `eventLog` parameter.
- [x] **GA params aligned** — code and CLAUDE.md both at 30 population / 60 generations, with a fitness cache so elitism doesn't re-evaluate the same chromosome.
- [x] **Approximate LCV documented** — `LCV_SAMPLE = 8` is now called out in CLAUDE.md's Challenge 1 section with the rationale.
- [x] **UI polish** — Segoe UI body / Consolas mono fonts, flat-borderless LabelFrames, two-row button bar with consistent fill, hover cursors, gradient status bar, log Text widget grows to fill the column (was capped at the default 24-line height).
- [x] **Tilemap sprites adopted** — `assets/kenney_tiny_town/Tilemap/` `building1` and `building2` for buildings (alternated by category); `grass`, `wavy_grass`, `flower_ground`, `stoned_grass` for Empty cells, picked deterministically per coordinate so the layout looks varied but stable across renders.
- [x] **Sim continues past 20 steps while civilians are pending** — `Simulation.isFinished` only returns True after the 20-step budget AND zero pending civilians, capped at +30 extra steps; the summary message reports actual step count instead of `totalSteps`.
- [x] **Codebase-wide readability pass** — every `lambda` removed, replaced with named helper functions; cryptic two-letter coordinate variables (`cx`, `cy`, `ax`, `ay`, `bx`, `by`, `ox`, `oy`, `r`, `c`, `nb`, etc.) renamed to spelled-out names (`centreX`, `centreY`, `startX`, `startY`, `badgeX`, `badgeY`, `row`, `col`, `neighbour`); generator expressions, comprehensions with conditions, and clever uses of `min`/`max`/`sum`/`sorted(... key=)` rewritten as explicit loops; dead imports (`from cityGraph import CityGraph` in `csp.py` and `mst.py`), the unused `PROXIMITY_TYPES` constant, the never-called `Simulation.autoRun`, and the unused `eventLog` parameter on `astar.stepRouter` all removed.
- [x] **New asset folder wired in** — sprites now load from `assets/` directly (no `kenney_tiny_town/Tilemap` subpath). Mappings: `school.png` for School, `factory2.png` for Industrial, `building1.png` for Hospital and PowerPlant, `building2.png` for Residential and AmbulanceDepot. Empty cells use `grass`, `wavy_grass`, `flower_ground`, `stoned_grass` picked deterministically per coordinate. The `ambulance.png` sprite replaces the hand-drawn cross-on-square ambulance icon.
- [x] **Animated tree** — `spr_tree_animated.png` (2496×64 strip, 39 frames of 64×64) is sliced and resized at sprite-load time. About one in seven Empty cells deterministically becomes a "tree cell" and animates the current frame. A single 100 ms tick (`_scheduleTick`) drives both the auto-step loop and the frame advance.

### In Progress

- [ ] (nothing currently in progress — pick the next item from the list below)

### Remaining / To Improve

- [ ] **Risk weights shift mid-simulation** (highest priority for the viva story). Either implement a periodic risk-shift event during the 20-step loop that bumps a district's `riskIndex` and triggers an ambulance reposition (greedy or partial GA re-run), or commit to defending the static-after-setup design choice in CLAUDE.md and the demo. See "Audit Findings" for the longer write-up.
- [ ] **Road cost weights live-modifiable** — residential 0.8, standard 1.0 are still hardcoded in `cityGraph.py`. Surface them in the Constraints panel for full live-modification coverage.
- [ ] **Sprite review** — pick which Tilemap sprite (building1 vs building2) goes with which building category once we look at them together. Currently alternated by guess.
- [ ] **Group visual theme decision** — colour palette and typography are now functional and consistent (Segoe UI / Consolas, flat panels, accent teal). Final group sign-off still pending.

### Known Issues

- (none currently blocking the demo — last verified end-to-end: Start, all overlays, both Flood and Emergency tools, multiple Steps, clean window close.)

### Audit Findings — Spec / Report vs Code

Most of the original audit items have now been addressed. What's left here is the work that is genuinely architectural or design-debate territory.

**Resolved this session**

- [x] **K-Means output is no longer dead code.** `crime.runCrime` now cross-validates K-Means cluster labels against the formula-based synthetic labels and emits two log lines: agreement percentage and per-tier cluster counts. Stage 1 has a visible role; KNN still trains on the synthetic dataset, which keeps the spec's "you decide the logic" requirement intact.
- [x] **10 police officers are deployed.** `crime.deployPoliceOfficers(graph, count=10)` greedily picks the top-10 highest-risk nodes; `Simulation.setup` calls it after `runCrime` and stores the list on `graph.policeOfficers`. The UI renders each officer as a small blue "P" badge in the cell corner and the legend includes them.
- [x] **MST events flow through the event log.** `mst.buildRoadNetwork` now returns `(routeA, routeB, events)` instead of printing; `Simulation.setup` collects them and the controller appends them to the in-app event log.
- [x] **`astar.stepRouter` no longer takes the unused `eventLog` parameter.** Signature is now `stepRouter(state, graph)`.
- [x] **GA parameter drift fixed.** Code now uses `POPULATION_SIZE = 30`, `NUM_GENERATIONS = 60` — slight bump from the old 20/30, with a fitness cache so elitism does not re-evaluate the same chromosome each generation. CLAUDE.md "Challenge 3" section updated to match.
- [x] **Approximate LCV documented.** CLAUDE.md "Challenge 1" section now explicitly says only `LCV_SAMPLE = 8` candidate cells are scored per choice, with the rationale.
- [x] **Industrial-not-adjacent rule now live-modifiable.** `INDUSTRIAL_ADJACENCY_RULE` is a module flag in `csp.py`; `runCSP(... industrialAdjacencyRule=)` overrides it, threaded through `Simulation` and `AppController`. UI exposes a checkbox in the Constraints panel.

**Still open (raise in next session)**

- **Risk weights never shift mid-simulation.** Statement: "ambulance placements from Challenge 3 are re-evaluated as risk weights shift." We currently set `riskIndex` once in `crime.runCrime` and never change it, and the GA only runs once. Two acceptable defences for the viva: (a) implement a periodic mid-sim risk-shift event that bumps a district's risk and triggers a cheap ambulance reposition (greedy or partial GA re-run), or (b) defend the design choice that "shift" refers to the initial bake-in driven by user-tweakable inputs. Pick one this session and document it.
- **Group visual theme.** Functional polish landed (Segoe UI / Consolas fonts, panel-flat look, three-column layout, status bar). Final colour palette and typography details are still a group decision.
- **Sprite mapping verification.** We're now on the user-supplied `Tilemap/` folder (building1, building2, plus four ground variants). Mapping is plausible but not human-verified for visual coherence; pick which sprite goes with which building category once we look at them together.
- **Live constraint coverage extension.** The Constraints panel now has the residential/powerplant proximity hops and the Industrial-adjacency toggle. The road cost weights (residential 0.8, standard 1.0) are still hardcoded in `cityGraph.py`; expose them next if we want even more dials for the live-modification challenge.

**Viva-defence items to nail down before the demo**

- The GA-runs-once-vs-spec story (above).
- Why approximate LCV is acceptable for our grid sizes (already documented in Challenge 1; rehearse the answer).
- How K-Means now relates to KNN in our pipeline: K-Means is the unsupervised cluster-discovery stage, formula generates the synthetic dataset that satisfies "you decide the logic", KNN trains on that synthetic data, and we cross-validate Stage 1 vs Stage 2 to show the unsupervised view agrees with our formula. (Rehearse this answer; it's the strongest viva story for Challenge 5.)

### Coding-Style Reminders Active in This Project

- **camelCase**, max two words, must mean something. PascalCase only for class names.
- **Getters and setters at the bottom of every class.** Top of class is constructor and core operations; bottom is the read/write surface.
- **No "tentativeCost" / "tentative"** naming in A*. Use `nextCost` or another concrete name.
- **No bracket noise** like `(Hello) world` in comments or output.
- **No output decoration** (`=====`, `-----`) outside menu rendering.
- **Strong OOP**: a controller mediates between UI and simulation/graph. Never let the UI mutate the simulation directly.
- **Library minimalism**: tkinter, sklearn, numpy, Pillow, plus stdlib. Anything new requires justification.
- **Beginner readable**: a first-year CS student should follow any function in 30 seconds. If not, simplify.

---

## Language and Environment

- **Language:** Python 3
- **UI Framework:** Tkinter only — single window. The city grid renders on a Tk `Canvas`; settings, overlays, the node info panel, and the event log live in side panels of the same root window. Pygame was removed because Tk Canvas does everything we need and a single library means a single window.
- **ML Library:** scikit-learn (`sklearn`) for K-Means clustering and KNN classifier

---

## Libraries — Full List and Justification

| Library | Purpose | Why |
|---|---|---|
| `tkinter` | Single-window UI: Canvas grid rendering, settings panel, event log, input fields, control buttons, overlay toggles | Built into Python, supports both 2D drawing and form widgets, no extra dependency |
| `Pillow` (PIL) | Load Kenney Tiny Town PNG sprites and convert them to `ImageTk.PhotoImage` for the Canvas | Tk's built-in `PhotoImage` only supports GIF/PPM, so PNG sprite support requires PIL. Already widely available |
| `sklearn` | K-Means clustering (Challenge 5 stage 1), KNN classifier (Challenge 5 stage 2) | Covered in class, beginner friendly, minimal setup |
| `numpy` | Feature arrays for K-Means and KNN input | Required by sklearn, beginner friendly for array math |
| `random` | Random flood events during simulation, GA mutation and crossover | Standard library, no install needed |
| `math` | Euclidean distance for Primary Hospital selection (Manhattan distance is inline) | Standard library |
| `collections` | `deque` for BFS traversal, `defaultdict` for adjacency list | Standard library |
| `heapq` | Priority queue for A*, Dijkstra, and Kruskal's | Standard library |

No external libraries beyond these. Everything above is either built into Python or installable through the standard tooling. Pygame and `copy` were removed in the refactor because nothing required them anymore.

---

## Code Style Rules

- **Naming:** camelCase for all variables and functions, the camelCase should not exceed twoWords and should have actual meaning. PascalCase for class names. Example: `cityGraph`, `getNeighbours`, `CityNode`.
- **Comments:** Short, humanised, only where the logic is non-obvious. No block comment walls. No em dashes in comments.
- **No over-engineering:** Keep each function doing one clear thing. No abstract base classes or design patterns unless they simplify the code.
- **Beginner readable:** If a first-year CS student cannot follow the logic within 30 seconds of reading a function, it needs to be simplified.
- **Code Readibility**: If the code gets congested, add spaces in between the lines of code so its easy to follow along.
- **Do not add brackets**: Do not add random brackets throughout the code like (Hello) world
- **Output Decoration**: Do not add any output decoration like =====, ----. Unless designing the menu. 
- **Maintain Excellent OOP**: Throughout the code, the code should have a well structured object oriented code base, no random functions being created for the sake of one functionality to be processed. 
- **Do not excessively spam libraries**: Keep the libraries that are being used restricted to libraries that are actually needed, all work can be done in existing libraries unless really required, so just a heads up keep the amount of libraries restricted to what we actually need. 

---

## File Structure

```
AI proj/
├── main.py              # Thin entry point: builds AppController + AppUI, hands control to Tk
├── appController.py     # Controller layer mediating UI <-> simulation/graph (proper OOP boundary)
├── cityGraph.py         # Shared city graph — nodes, edges, getters/setters
├── csp.py               # Challenge 1: CSP city layout planner
├── mst.py               # Challenge 2: Road network via Kruskal + A* backup route
├── ga.py                # Challenge 3: Ambulance placement via Genetic Algorithm
├── astar.py             # Challenge 4: A* emergency routing with dynamic rerouting
├── crime.py             # Challenge 5: K-Means clustering + KNN crime risk predictor
├── simulation.py        # 20-step simulation loop, flood events, step controller
├── ui.py                # Single-window Tk UI: Canvas grid + control panels
├── eventLog.py          # Tkinter event log panel
├── assets/              # Kenney Tiny Town sprites (loaded via PIL)
└── CLAUDE.md            # This file
```

Each group member works primarily in their assigned files. The shared contract is `cityGraph.py` — any change to its public methods must be discussed with the full group before merging. The UI layer (`ui.py`) only ever calls `appController.py`; it never reaches into the simulation or graph internals beyond read-only rendering, which keeps responsibilities clean.

---

## The City Graph — `cityGraph.py`

This is the foundation everything else is built on. It must be written first before any other module can be tested.

### Grid

- Default size: **10x10** (user can change this from the UI before starting, min 5, max 20)
- Every coordinate `(row, col)` is a node regardless of whether a building sits on it
- Nodes with no building assigned are **Empty** intersection nodes — these are valid and necessary
- Connections only exist in the **4 cardinal directions** (up, down, left, right) — no diagonals

### Population density — what it means

Population density is the **total occupancy** of that grid cell — the number of people who either live or work there. It is a single integer per node. Instructor clarification: a school's population is its student count, an industrial node's is its worker count, a residential node's is its residents. Empty nodes have population 0. Values are randomly assigned within type-appropriate ranges at city generation time.

Suggested ranges (adjust if needed):
- Residential: 50–200
- School: 100–400
- Industrial: 80–300
- Hospital: 30–150
- PowerPlant: 20–80
- AmbulanceDepot: 10–40
- Empty: 0

### Node properties (stored per node)

```python
{
    "type": str,          # "Residential", "Hospital", "School", "Industrial",
                          # "PowerPlant", "AmbulanceDepot", or "Empty"
    "population": int,    # total occupancy of this grid cell
    "riskIndex": float,   # crime risk multiplier, set by crime module, starts at 1.0
    "accessible": bool,   # False if flooded or blocked
}
```

### Edge properties (stored per edge)

```python
{
    "cost": float,        # base cost: 1.0 standard, 0.8 if either endpoint is Residential
    "blocked": bool,      # True if flooded
}
```

### Implementation notes

- Use an **adjacency list** as a dictionary: `graph[node] = list of (neighbour, edgeCost)`
- The graph is a single object passed by reference to all modules
- A flood sets `edge["blocked"] = True` on both directions of that edge immediately
- After a flood, all modules see the change instantly since they hold a reference to the same object
- `riskIndex` starts at `1.0` (no multiplier) and is updated to 1.25, 1.75, or 2.5 by the crime module

---

## Challenge 1 — City Layout (CSP) — `csp.py`

**Algorithm:** Constraint Satisfaction Problem with backtracking, MRV heuristic, LCV heuristic, and forward checking.

### Constraints

1. Industrial zones cannot be adjacent (4-directional) to Schools or Hospitals
2. Every Residential node must be within 3 road hops of at least one Hospital
3. Every Power Plant must be within 2 road hops of at least one Industrial zone

### Why forward checking and not AC-3

Both are valid pruning strategies. Forward checking is chosen here because it is simpler to implement, easier to understand, and sufficient for a 10x20 grid with a small number of buildings. AC-3 enforces full arc consistency across the entire constraint graph on every assignment, which is more powerful but also significantly more complex to code — and harder to explain in the viva. For our problem size, forward checking catches the same violations that matter before we waste time going down a dead-end branch.

### How it works

1. User specifies counts of each building type via the UI
2. CSP assigns buildings to grid nodes one at a time
3. MRV picks the variable (unplaced building type) with the fewest remaining valid grid positions
4. LCV picks the value (grid cell) that eliminates the fewest options for other unplaced buildings. To keep backtracking fast on larger grids, only the first `LCV_SAMPLE = 8` candidate cells per choice are scored and the rest are appended unscored after a shuffle. This is approximate LCV: the heuristic ordering still beats random and we never lose correctness because forward checking and the leaf proximity validation still gate every full assignment.
5. Forward checking prunes any grid cell that would immediately violate a constraint after each assignment
6. Backtracking undoes the last assignment and tries the next option if no valid cell remains

### If no valid layout exists — minimum conflict fallback

The project requires the system to identify the conflicting rule AND propose a minimum conflict solution. The procedure is:

1. Run the full CSP with backtracking first
2. If no solution is found, identify which constraint is blocking (whichever causes the final dead-end)
3. Log the specific constraint that failed with a clear message
4. Run a **minimum conflict fallback**: place buildings greedily without that constraint, then report how many violations exist and which nodes are in conflict
5. Highlight the conflicting nodes in the UI so the user can adjust their building counts and retry

This satisfies the project requirement of "identify which specific rule is causing the conflict and propose minimum conflict solution."

### Output

- Fully populated `cityGraph` with all nodes assigned their type (Empty nodes remain for unused coordinates)
- If CSP succeeds: valid layout, all constraints satisfied
- If CSP fails: conflict message + a minimum-violation layout shown in the UI with problem nodes highlighted

---

## Challenge 2 — Road Network (MST + A*) — `mst.py`

**Algorithm:** Kruskal's algorithm for minimum spanning tree, then A* to add the backup emergency route.

### Primary Hospital designation

Among all Hospital nodes placed by the CSP, the **Primary Hospital** is the one closest to the geometric centre of the grid (minimum Euclidean distance from the grid centre point). If two hospitals are equidistant from the centre, pick the one with the lower row-major index. This is deterministic, simple to implement, and reflects real urban planning logic. This designation is computed once in `mst.py` and stored on the graph object so all other modules can read it.

### Primary Ambulance Depot designation

Similarly, if there are multiple AmbulanceDepot nodes, the **Primary Depot** is the one closest to the geometric centre of the grid using the same rule. The dual-route guarantee is between the Primary Hospital and the Primary Depot.

### Road costs

- Standard road: **1.0**
- Road where either endpoint is a Residential node: **0.8**

### How it works

1. Kruskal's builds the MST connecting all nodes at minimum total cost — this is the base road network
2. A* finds the shortest path from the Primary Hospital to the Primary Ambulance Depot
3. All edges along that A* path are recorded as Route A
4. Those edges are **temporarily removed** from the graph (in memory only, not permanently)
5. A* runs again from Primary Hospital to Primary Depot — since Route A edges are gone, it is forced to find a completely different path (Route B)
6. Both Route A and Route B edges are restored and added permanently to the network
7. Result: MST base network + two completely independent emergency corridor routes

### Why remove the full path, not just one edge

Removing only one edge would make A* detour around that single edge but reuse most of Route A. The two routes would share the majority of their edges, meaning one flood event could still block both. Removing all of Route A's edges forces A* to find a path that shares zero edges with Route A — a genuinely independent backup. The higher cost is acceptable because the safety guarantee is the actual requirement.

### Output

- Updated `cityGraph` with all road edges marked as built
- Primary Hospital and Primary Depot stored on the graph for other modules to use

---

## Challenge 3 — Ambulance Placement (GA) — `ga.py`

**Algorithm:** Genetic Algorithm.

### Ambulance placement rule — any accessible node

Ambulances can be positioned at **any accessible node** on the grid, not just AmbulanceDepot nodes. This decision was made because restricting placement to depot nodes would make the GA's search space trivially small and would defeat the purpose of optimization. The GA's job is to find the best possible coverage positions across the entire grid. The AmbulanceDepot node type simply represents the home base; during simulation the ambulances are wherever the GA placed them. This choice is documented here for viva justification.

### Setup

- 3 ambulances to place
- A chromosome = a list of 3 node coordinates, e.g. `[(2,3), (7,1), (5,8)]`
- Population size: 30 chromosomes
- Generations: 60
- Mutation rate: 10%
- Fitness cache: chromosomes are keyed by their sorted-tuple form so elitism does not re-evaluate the same Dijkstra-heavy fitness twice across generations.

### Fitness function

For a given chromosome (placement of 3 ambulances), compute the **weighted shortest path** distance from every accessible node to its nearest ambulance using **Dijkstra's algorithm**. The edge cost used is `base road cost × riskIndex` of the destination node (same cost formula as A*). The fitness score is the **maximum of these distances** (worst-case response time). Lower is better.

**Why Dijkstra and not BFS here:** BFS treats every edge as equal weight 1. But crime risk multipliers make edges unequal — a high-crime node costs 2.5× more to traverse. BFS would give the wrong distances. Dijkstra handles weighted edges correctly and is the right tool here. Plain BFS would only be valid if all edges were the same cost, which they are not once crime risk is assigned.

### How it works

1. Generate 50 random valid placements as initial population (all 3 positions must be accessible nodes)
2. For each generation: evaluate fitness of all 50 chromosomes using Dijkstra
3. Select top 50% (25 chromosomes) as parents — elitism keeps the best solutions
4. Crossover: pair up parents and split each chromosome at a random index to produce 25 children
5. Mutate: for each child, with 10% probability replace one ambulance position with a random accessible node
6. New generation = the 25 parents + 25 children (keeps population at 50)
7. Repeat for 100 generations, keep the chromosome with the lowest fitness score

### Role in simulation

The GA runs **once before the simulation starts** to determine the initial ambulance positions. This is the optimal placement given the city layout and crime risk weights.

During the 20-step simulation, ambulances do **not** move unless their current node becomes inaccessible (`accessible = False` due to flooding). If that happens, a simple greedy fallback kicks in: check all 4 neighbouring nodes, move the ambulance to the nearest accessible one. The GA is not re-run during simulation — it is computationally expensive and its purpose is the initial optimal placement. The greedy fallback during simulation demonstrates a second strategy (reactive vs. optimal) which is a strong viva talking point.

The project statement says "ambulance placements from Challenge 3 are re-evaluated as risk weights shift" — this refers to the GA taking risk weights as input before the simulation begins, not re-running the GA every step.

### Output

- 3 node coordinates for ambulance starting positions
- These are passed to the simulation loop and stored on the shared graph

---

## Challenge 4 — Emergency Routing (A*) — `astar.py`

**Algorithm:** A* search with Manhattan distance heuristic.

### Heuristic

```
h(node) = |node.row - goal.row| + |node.col - goal.col|
```

This is admissible on a grid (never overestimates the true cost) so A* is guaranteed to find the shortest path. This is the exact property the project requires.

### Medical team starting position

The medical team starts at the **Primary Hospital** node (designated by `mst.py` and stored on the graph). This is the natural starting point — the hospital dispatches the team. The starting position is read from the graph at the beginning of the simulation.

### Handling multiple civilians — sequential single-goal runs

A* is a **single-goal** algorithm. It does not natively handle multiple destinations at once. To route the team to all civilians in sequence, A* is run once per civilian:

1. Run A* from the team's current position to civilian 1 → follow that path step by step
2. Once civilian 1 is reached, run A* from civilian 1's position to civilian 2 → follow that path
3. Continue until all civilians are reached

The order of civilians is fixed as a list provided at simulation start. The team always targets the next civilian in the list, not the nearest one. This keeps the logic simple and explainable.

### Handling a completely unreachable civilian

If A* is run and no path exists (all routes to the civilian are blocked by floods), the system must:

1. Log the failure in the event log: `[Step N] Civilian at (r,c) is unreachable — all paths flooded. Skipping.`
2. Mark that civilian as skipped
3. Move to the next civilian on the list
4. Do not halt the simulation

This behaviour was confirmed by the instructor: "If no path exists, the system should gracefully recognize that the path cost is infinite, log the failure, and proceed to the next reachable civilian."

### Per-step dynamic rerouting

1. At each simulation step the team moves one cell along its current A* path
2. Before moving, check if the next cell on the path is still accessible
3. If a flood has blocked it, immediately re-run A* from the current position to the current target civilian
4. If the re-run also finds no path, apply the unreachable civilian rule above

### Cost weighting

Edge cost used by A* = `base road cost × riskIndex of destination node`. The riskIndex is set by the crime module and stored on each node. This makes high-crime areas more costly to traverse.

### Output

- The path as an ordered list of nodes to follow
- Real-time rerouting whenever a flood blocks the current path
- Event log entries for every reroute and every skipped civilian

---

## Challenge 5 — Crime Risk Prediction — `crime.py`

**Algorithm:** K-Means clustering (unsupervised) followed by KNN classification (supervised).

### Stage 1 — Clustering

- **k = 3** clusters fixed, matching exactly the three risk levels (High, Medium, Low)
- Features per node: `[populationDensity, proximityToIndustrial]`
- `proximityToIndustrial` = BFS hop count to the nearest Industrial node (lower = closer = higher risk)
- K-Means groups all nodes into 3 natural clusters without any labels
- Label assignment after clustering: highest average population + lowest industrial distance = High risk; lowest average population = Low risk; middle cluster = Medium risk
- Using k=3 is the right call here because the downstream classifier expects exactly 3 labels. Using an elbow method would add complexity with no benefit.

### Stage 2 — Synthetic dataset generation

For each node, assign a crime label using this scoring rule:

```
score = (populationDensity * 0.6) + ((1 / (proximityToIndustrial + 1)) * 0.4)
```

- score > 0.66 → High
- score > 0.33 → Medium
- else → Low

This formula is defensible: high occupancy and closeness to industrial zones both correlate with higher crime likelihood in urban models. The thresholds divide the score range into equal thirds.

### Stage 3 — KNN classifier

- Train a KNN classifier (k=5 neighbours) on the synthetic dataset from Stage 2
- Features: `[populationDensity, proximityToIndustrial]`
- Labels: High / Medium / Low
- Predict the risk level for every node in the graph
- Write the result back into `cityGraph`: set each node's `riskIndex` to the appropriate multiplier

### Crime risk as cost multiplier in A* and GA

| Risk Level | riskIndex stored on node | Cost Multiplier effect |
|---|---|---|
| Low | 1.25 | road cost × 1.25 |
| Medium | 1.75 | road cost × 1.75 |
| High | 2.5 | road cost × 2.5 |

Nodes with no assigned risk (before crime module runs) default to `riskIndex = 1.0` (no penalty).

### When it runs

Crime module runs **once after the CSP and MST are complete** but **before the simulation starts**. The risk indices are then baked into the graph for the GA and A* to use throughout the simulation.

---

## Simulation Loop — `simulation.py`

### Structure

- 20 steps total
- Each step executes in this order:
  1. Check if a random flood event occurs (30% chance per step)
  2. If flood: randomly pick one accessible edge, block it in both directions, log the event
  3. Move the medical team one cell along its current A* path
  4. If the next cell is now blocked: re-run A* from the current position; if still no path, log civilian as unreachable and skip
  5. Check if any ambulance is now on an inaccessible node: if yes, greedy-move it to the nearest accessible neighbour
  6. Update the UI (redraw grid, overlays, event log)
  7. Pause for the configured step delay

### Flood probability

30% chance per step. Ensures floods happen regularly enough to demonstrate rerouting without making the city impassable. Configurable from the UI settings panel.

### Step control

- Play button: run all remaining steps automatically with the step delay between each
- Pause button: halt between steps
- Step button: advance exactly one step manually
- Simulation ends after step 20 — shows a summary in the event log, does not loop

---

## UI Design — `ui.py` + `eventLog.py`

### Layout

Single Tk window with two side-by-side panels:

- **Left:** A `tk.Canvas` that draws the city grid — building rectangles or sprites, roads as lines between centres, route highlights, ambulances as circles, the medical team as a diamond.
- **Right:** A 360-pixel control column containing the settings panel at the top, the overlay toggle row, the node info panel, and the event log filling whatever space remains.

### Grid rendering

- Each node is a square cell drawn on the Canvas at `CELL_SIZE = 50` pixels with a `MARGIN = 4` border.
- Building types render as Kenney Tiny Town sprites loaded through `PIL.ImageTk.PhotoImage`. If a sprite is missing, the cell falls back to a coloured rectangle.
- Roads draw as lines between node centres. Flooded roads paint blue regardless of overlay; the road-network overlay additionally tints residential-discounted roads yellow.
- Route A and Route B (the two emergency corridors from MST/A*) overlay the base roads in distinct thick lines (orange and green).
- Ambulances render as white circles. The medical team renders as a cyan diamond at its current cell.
- UI design and creative visual theme are still up to the group — the project rubric awards up to full marks for interface creativity.

### Overlay toggles (buttons in Tkinter panel)

Three toggleable overlays drawn on top of the grid in Pygame:

| Toggle | What it shows |
|---|---|
| Road Network | Color-coded roads: white = standard, yellow = residential (discounted), blue = flooded |
| Ambulance Coverage | Heatmap shading per node: darker = farther from nearest ambulance (Dijkstra distances) |
| Crime Risk Heatmap | Red = High, Orange = Medium, Green = Low |

### Settings panel (Tkinter)

- Grid size input (default 10, min 5, max 20)
- Building count inputs: Hospitals, Schools, Industrial, Residential, Power Plants, Ambulance Depots
- Flood probability slider (default 30%)
- Step delay slider (speed of auto-play)
- Start Simulation button
- Reset button

### Click interactions

- Click any node: side panel shows its stats (type, population, risk level, accessibility, riskIndex)
- Flood tool: user clicks one node then an adjacent node — the connecting road is flooded manually

### Event log (Tkinter text widget)

Scrollable, timestamped log. Examples:

```
[Step 3] Road (4,5)-(4,6) flooded automatically.
[Step 3] Medical team rerouted. New path length: 7 hops.
[Step 5] Ambulance at (2,3) relocated to (2,4) — node inaccessible.
[Step 6] Civilian at (8,9) is unreachable — all paths flooded. Skipping.
[Step 7] Road (1,2)-(1,3) flooded automatically.
```

---

## Development Order

Build in this order so each module can be tested before the next depends on it:

1. `cityGraph.py` — shared graph structure (all other modules need this)
2. `csp.py` — place buildings on the graph
3. `mst.py` — build roads, designate Primary Hospital and Primary Depot
4. `crime.py` — assign risk weights to all nodes
5. `ga.py` — place ambulances using the weighted graph
6. `astar.py` — route the medical team through the weighted graph
7. `simulation.py` — wire all modules into the 20-step loop
8. `ui.py` + `eventLog.py` — render everything visually
9. `main.py` — launch point that ties UI and simulation together

---

## Key Design Decisions (with full reasoning for peer review and viva)

**Why forward checking and not AC-3?**
Forward checking is simpler to implement and sufficient for our grid size. After each assignment it checks only the directly affected neighbours, which catches violations before we go deeper into a dead-end. AC-3 checks the entire constraint graph repeatedly — more thorough but significantly more complex to code and explain. For a 10x20 grid with a small number of buildings, forward checking does the job.

**Why minimum conflict fallback in CSP?**
The project statement explicitly requires it: "if no valid layout is possible, identify which specific rule is causing the conflict and propose minimum conflict solution." Reporting only the error without a fallback layout fails this requirement.

**Why remove the full Route A path in MST (not just one edge)?**
Removing only one edge lets A* reuse most of Route A's edges for Route B. One flood could then block both routes simultaneously. Removing all of Route A forces A* to find a path with zero shared edges — a genuinely independent backup route as the project demands.

**Why Dijkstra in the GA fitness function and not BFS?**
BFS treats every edge as weight 1 and gives wrong distances when edges have different costs. Crime risk multipliers make edges unequal. Dijkstra handles weighted edges and gives the true shortest weighted distance. Using BFS here would mean the GA optimises for the wrong metric.

**Why ambulances can be placed on any accessible node?**
Restricting to AmbulanceDepot nodes only would make the GA's search space tiny and the optimization trivial. The project says "positioned at locations on the grid" — any node qualifies. The AmbulanceDepot is the home base type, not the only valid position.

**Why A* runs once per civilian sequentially?**
A* is a single-source single-goal algorithm. Running it once for the whole list of civilians is not how it works. Sequential runs — reach civilian 1, then re-run to civilian 2 — is simple, correct, and easy to explain in the viva.

**Why K-Means k=3?**
The downstream KNN classifier predicts exactly 3 labels (High, Medium, Low). Using k=3 means the clusters map directly to these labels with no ambiguity. Elbow method would add complexity with no benefit.

**Why GA runs once, not per step?**
The GA explores 50 chromosomes over 100 generations. Running this per step would cause multi-second delays between steps, breaking the simulation feel. The GA finds the optimal initial placement; the greedy fallback handles mid-simulation disruptions. Two strategies demonstrated — stronger viva argument than one.

**Why Primary Hospital = closest to grid centre?**
Deterministic (same result every run), simple to compute, reflects real urban planning where a central hospital serves the widest area. Requires no extra user input and is easy to explain.

**Why Pygame + Tkinter together?**
Pygame excels at real-time 2D grid rendering but has no native widget toolkit. Tkinter handles form inputs, sliders, scrollable text, and buttons cleanly. Both are familiar to the team. This is a well-established Python pattern.

**Why Manhattan distance as the A* heuristic?**
On a 4-directional grid, Manhattan distance is the exact minimum number of steps between two nodes. It never overestimates the true cost, making it admissible. An admissible heuristic guarantees A* finds the shortest path — this is the viva answer for heuristic choice.

---

## Implementation Status

All core Python files have been written. Below is a record of what each file contains, so peers and the group can verify correctness manually.

### `cityGraph.py`
- `CityGraph(rows, cols)` — initialises all nodes as Empty with riskIndex=1.0, builds full 4-directional edge grid
- Edge costs: 0.8 if either endpoint is Residential, else 1.0. Updated via `setNodeType`.
- `edgeKey(nodeA, nodeB)` — module-level canonical key function (smaller node first)
- All public methods match spec: `setNodeType`, `getNeighbours`, `getAccessibleNeighbours`, `getEdgeCost`, `getWeightedCost`, `floodEdge`, `unfloodEdge`, `isEdgeBlocked`, `setRiskIndex`, `setAccessible`, `getAllNodes`, `getAccessibleNodes`, `getNodesByType`, `getAllEdges`, `reset`

### `csp.py`
- `runCSP(graph, buildingCounts)` — public entry point, returns `(True, None)` or `(False, conflictInfo)`
- Uses backtracking with MRV (`pickMRV`), LCV (`lcvOrder`), and forward checking (`forwardCheck`)
- Constraint 1 (Industrial adjacency) checked during search via `getValidCells`
- Constraints 2 and 3 (proximity) checked only at the leaf of the backtracking tree via `validateProximity`
- Minimum conflict fallback: if backtracking fails, runs `greedyPlace` then `identifyWorstConstraint`
- BFS uses `graph.getNeighbours` (not accessible version — layout phase ignores flooding)

### `mst.py`
- `buildRoadNetwork(graph)` — public entry point, returns `(routeA, routeB)` as lists of canonical edge tuples
- `pickCentreNode` — designates Primary Hospital and Primary Depot (closest to grid centre, tiebreaker row then col)
- `buildMST` — Kruskal's with Union-Find (path compression + union by rank), stops at numNodes-1 edges
- `astarPath` — local A* for route finding, uses Manhattan distance, respects `graph.isEdgeBlocked`
- Route A edges are blocked via `graph.floodEdge()` before Route B search, then restored via `graph.unfloodEdge()`

### `crime.py`
- `runCrime(graph)` — public entry point, writes riskIndex to every node via `graph.setRiskIndex`
- `getProximityToIndustrial` — BFS hop count to nearest Industrial, fallback = rows+cols if none exists
- Stage 1: KMeans(n_clusters=3, random_state=42, n_init=10). Cluster labelled by population density rank.
- Stage 2: synthetic labels via `score = (pop*0.6) + ((1/(prox+1))*0.4)`, normalised, thresholds 0.66/0.33
- Stage 3: KNeighborsClassifier(n_neighbors=5), trained on all nodes, predicts for all nodes
- riskIndex map: High=2.5, Medium=1.75, Low=1.25

### `ga.py`
- `runGA(graph)` — public entry point, writes and returns `graph.ambulancePositions`
- `dijkstra(graph, source)` — returns distance dict using `getWeightedCost` and `getAccessibleNeighbours`
- Fitness = max(min distance from any node to nearest ambulance) — Dijkstra-based, not BFS
- Population=50, Generations=100, Mutation rate=10%, Elitism keeps top 25
- `fixDuplicates` — replaces duplicate nodes using a pre-collected full position set (not just seen-so-far)
- GA runs once before simulation, does NOT re-run during steps

### `astar.py`
- `findPath(graph, start, goal)` — A* with Manhattan heuristic, uses `getWeightedCost`, returns node list or []
- `RouterState` class: `currentPos`, `civilians` (5 random accessible nodes), `currentPath`, `currentTarget`, `skipped`, `reached`
- `initRouter(graph)` — team starts at `graph.primaryHospital`, returns RouterState
- `stepRouter(state, graph, eventLog)` — moves one cell per call, rerouts on blockage, skips unreachable civilians
- Event strings: `"Civilian at X is unreachable -- all paths flooded. Skipping."`, `"Medical team rerouted. New path length: N hops."`, `"Medical team reached civilian at X."`

### `simulation.py`
- `Simulation(graph, buildingCounts, floodProbability=0.30)` class
- `setup()` — runs CSP → MST → crime → GA → A* in order, returns `(cspSuccess, cspConflict)`
- `step()` — flood check (30% random edge) → advance medical team → ambulance accessibility check. Returns list of event strings.
- `autoRun(onStepCallback)` — runs all remaining steps
- Ambulance relocation: if node inaccessible, greedy-move to first accessible neighbour

### `eventLog.py`
- `EventLog(parent)` class — Tkinter Text widget with scrollbar
- Dark terminal theme: bg=#1e1e1e, fg=#00ff88, Courier font size 9
- `addEntry(text)` — appends line, auto-scrolls to END
- `clear()` — clears all entries
- `addSeparator()` — inserts `"---" * 20` divider line

### `ui.py`
- `AppUI(controller)` — receives only the `AppController`; never sees `Simulation` or `CityGraph` directly
- Single Tk root window. Left side is a `tk.Canvas` of `CELL_SIZE * cols` by `CELL_SIZE * rows` for the grid. Right side is a 360-pixel control panel column.
- Sprites loaded once via `PIL.ImageTk.PhotoImage` and cached on the instance to keep references alive.
- `_render()` clears the canvas and redraws every frame; cheap enough for the supported grid sizes.
- Three overlay modes: `"roads"`, `"coverage"`, `"crime"`. Toggling re-renders.
- Auto-play uses `Tk.after(100, ...)` to poll the controller's `autoStepIfDue(stepDelay)`.
- Click handler: maps Canvas pixel coords to `(row, col)`, asks the controller for node info, populates the side panel.
- All settings (grid size, building counts, flood probability, step delay) come from `getSimSettings()` — handed to the controller as a dict.

### `appController.py`
- `AppController(defaultBuildings, gridSize, floodProbability)` — owns the `CityGraph` and `Simulation`.
- Public surface: `startSimulation`, `stepSimulation`, `autoStepIfDue`, `resetSimulation`, `getNodeInfo`, plus getters `getGraph`, `getSimulation`, `getRouterState`, `getRoutes`, `isSetupDone`, `isFinished`.
- `setEventListener(callback)` registers the UI's log function so simulation events flow into the event log without the UI polling the simulation.
- This class is the OOP boundary: the UI calls into it, never around it.

### `main.py`
- Thin entry point: builds `AppController`, builds `AppUI(controller)`, registers the UI's `addLog` as the controller's event listener, calls `appUI.setup()` then `appUI.run()`.
- No more pygame loop, no more globals, no more callback wiring -- the UI drives Tk's `mainloop`.

---

## Sprites — Status and Source

Sprites are not yet integrated. Placeholder coloured rectangles are used for all building types. When ready, use **Kenney's Tiny Town** pack (CC0, free, top-down):
- URL: [kenney.nl/assets/tiny-town](https://kenney.nl/assets/tiny-town)
- All assets are CC0 — no attribution required, commercial use allowed
- Place downloaded PNG files in the `assets/` folder
- In `ui.py`, load sprites in `_setupPygame()` using `pygame.image.load()` and scale to `(CELL_SIZE - MARGIN*2, CELL_SIZE - MARGIN*2)`
- Replace the coloured rect drawing in `_drawNodes()` with `screen.blit(sprite, rect)` per building type

Building type to sprite filename mapping (to be confirmed once pack is downloaded):
- Residential → house sprite
- Hospital → hospital/medical sprite
- School → school sprite
- Industrial → factory sprite
- PowerPlant → power tower sprite
- AmbulanceDepot → garage/depot sprite
- Ambulance → ambulance vehicle sprite (for `_drawAmbulances`)

---

## What to Do Next

1. Download Kenney Tiny Town sprites and place in `assets/`
2. Wire sprites into `ui.py` `_drawNodes()` and `_drawAmbulances()`
3. Run the system end-to-end and fix any integration bugs
4. Polish UI creative theme (colours, fonts, layout spacing)
5. Test all 5 AI modules working together in the 20-step simulation

---
