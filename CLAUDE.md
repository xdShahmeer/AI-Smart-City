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

## Language and Environment

- **Language:** Python 3
- **UI Framework:** Pygame (grid rendering, sprites, overlays) + Tkinter (settings panel, event log, text inputs, buttons)
- **ML Library:** scikit-learn (`sklearn`) for K-Means clustering and KNN classifier

---

## Libraries — Full List and Justification

| Library | Purpose | Why |
|---|---|---|
| `pygame` | Render the city grid, sprites, overlays, ambulance movement | Handles real-time 2D graphics in Python in a straightforward way |
| `tkinter` | Settings panel, event log text area, input fields, simulation control buttons | Built into Python, familiar to the team, handles UI widgets cleanly |
| `sklearn` | K-Means clustering (Challenge 5 stage 1), KNN classifier (Challenge 5 stage 2) | Covered in class, beginner friendly, minimal setup |
| `random` | Random flood events during simulation, GA mutation and crossover | Standard library, no install needed |
| `math` | Manhattan distance heuristic for A* | Standard library |
| `collections` | `deque` for BFS/neighbour traversal, `defaultdict` for adjacency list | Standard library |
| `heapq` | Priority queue for A* and Kruskal's | Standard library |
| `copy` | Shallow copies of edge lists for MST + backup route logic | Standard library |
| `numpy` | Feature arrays for K-Means and KNN input | Required by sklearn, beginner friendly for array math |

No external libraries beyond these. Everything above is either built into Python or already taught in class.

---

## Code Style Rules

- **Naming:** camelCase for all variables and functions. PascalCase for class names. Example: `cityGraph`, `getNeighbours`, `CityNode`.
- **Comments:** Short, humanised, only where the logic is non-obvious. No block comment walls. No em dashes in comments.
- **No over-engineering:** Keep each function doing one clear thing. No abstract base classes or design patterns unless they simplify the code.
- **Beginner readable:** If a first-year CS student cannot follow the logic within 30 seconds of reading a function, it needs to be simplified.

---

## File Structure

```
AI proj/
├── main.py              # Entry point, launches UI and simulation loop
├── cityGraph.py         # Shared city graph — nodes, edges, update methods
├── csp.py               # Challenge 1: CSP city layout planner
├── mst.py               # Challenge 2: Road network via Kruskal + A* backup route
├── ga.py                # Challenge 3: Ambulance placement via Genetic Algorithm
├── astar.py             # Challenge 4: A* emergency routing with dynamic rerouting
├── crime.py             # Challenge 5: K-Means clustering + KNN crime risk predictor
├── simulation.py        # 20-step simulation loop, flood events, step controller
├── ui.py                # Pygame rendering, overlays, sprite drawing
├── eventLog.py          # Tkinter event log panel
├── assets/              # Sprite images (to be added)
└── CLAUDE.md            # This file
```

Each group member works primarily in their assigned files. The shared contract is `cityGraph.py` — any change to its public methods must be discussed with the full group before merging.

---

## The City Graph — `cityGraph.py`

This is the foundation everything else is built on. It must be written first before any other module can be tested.

### Grid

- Default size: **10x10** (user can change this from the UI before starting)
- Every coordinate `(row, col)` is a node regardless of whether a building sits on it
- Nodes with no building are empty intersection nodes
- Connections only exist in the **4 cardinal directions** (up, down, left, right) — no diagonals

### Node properties (stored per node)

```python
{
    "type": str,          # "Residential", "Hospital", "School", "Industrial",
                          # "PowerPlant", "AmbulanceDepot", or "Empty"
    "population": int,    # population density value
    "riskIndex": float,   # updated by crime module, starts at 0.0
    "accessible": bool,   # False if flooded or blocked
}
```

### Edge properties (stored per edge)

```python
{
    "cost": float,        # base cost: 1.0 standard, 0.8 through residential
    "blocked": bool,      # True if flooded
}
```

### Implementation notes

- Use an **adjacency list** as a dictionary: `graph[node] = list of (neighbour, edgeCost)`
- The graph is a single object passed by reference to all modules
- A flood sets `edge["blocked"] = True` on both directions of that edge immediately
- After a flood, all modules see the change instantly since they hold a reference to the same object

---

## Challenge 1 — City Layout (CSP) — `csp.py`

**Algorithm:** Constraint Satisfaction Problem with backtracking, MRV heuristic, LCV heuristic, and forward checking.

### Constraints

1. Industrial zones cannot be adjacent (4-directional) to Schools or Hospitals
2. Every Residential node must be within 3 road hops of at least one Hospital
3. Every Power Plant must be within 2 road hops of at least one Industrial zone

### How it works

1. User specifies counts of each building type via the UI
2. CSP assigns buildings to grid nodes one at a time
3. MRV picks the variable (unplaced building) with the fewest remaining valid positions
4. LCV picks the value (grid cell) that rules out the fewest options for other buildings
5. Forward checking prunes cells that would immediately violate a constraint
6. If no valid placement exists, the system reports which specific rule caused the conflict

### Output

- Fully populated `cityGraph` with all nodes assigned their type
- If no solution: a clear message naming the conflicting constraint

---

## Challenge 2 — Road Network (MST + A*) — `mst.py`

**Algorithm:** Kruskal's algorithm for minimum spanning tree, then A* to add the backup emergency route.

### Primary Hospital designation

Among all Hospital nodes placed by the CSP, the **Primary Hospital** is the one closest to the geometric centre of the grid (minimum Euclidean distance from the grid centre point). If two hospitals are equidistant from the centre, pick the one with the lower index (row-major order). This is simple, deterministic, and defensible in the viva.

### Road costs

- Standard road: **1.0**
- Road passing through a Residential node (either endpoint is Residential): **0.8**

### How it works

1. Kruskal's builds the MST connecting all nodes at minimum cost — this is the base road network
2. A* finds the shortest path from Primary Hospital to the Ambulance Depot
3. All edges on that A* path are noted
4. Those edges are temporarily removed from the graph
5. A* runs again — this finds a completely separate backup route
6. Both routes (original + backup) are added permanently to the network on top of the MST
7. Result: the full road network with guaranteed dual-path redundancy for the emergency corridor

### Output

- Updated `cityGraph` with all road edges marked as built

---

## Challenge 3 — Ambulance Placement (GA) — `ga.py`

**Algorithm:** Genetic Algorithm.

### Setup

- 3 ambulances to place
- A chromosome = a list of 3 node coordinates, e.g. `[(2,3), (7,1), (5,8)]`
- Population size: 50 chromosomes
- Generations: 100
- Mutation rate: 10%

### Fitness function

For a given chromosome (placement of 3 ambulances), compute the shortest path distance from every node to its nearest ambulance (using BFS since all road costs are equal for coverage purposes). The fitness score is the **maximum of these distances** (worst-case response time). Lower is better.

### How it works

1. Generate 50 random valid placements as initial population
2. For each generation: evaluate fitness of all chromosomes
3. Select top 50% as parents (elitism)
4. Crossover: combine two parent chromosomes by splitting at a random point
5. Mutate: randomly change one ambulance position in some chromosomes
6. Repeat for 100 generations, keep the best result

### Role in simulation

The GA runs **once before the simulation starts** to determine initial ambulance positions. This is the optimal placement. During the 20-step simulation, if a flood cuts off an ambulance node (sets `accessible = False`), a lightweight greedy fallback moves that ambulance to the nearest accessible neighbouring node. The GA is not re-run during simulation — it is too slow for real-time steps and the viva question will focus on understanding the GA itself.

### Output

- 3 node coordinates for ambulance starting positions
- These are passed to the simulation loop

---

## Challenge 4 — Emergency Routing (A*) — `astar.py`

**Algorithm:** A* search with Manhattan distance heuristic.

### Heuristic

```
h(node) = |node.row - goal.row| + |node.col - goal.col|
```

This is admissible on a grid (never overestimates) so A* is guaranteed to find the shortest path.

### How it works

1. A list of civilian locations is given as targets (in order)
2. A* finds the shortest path from current position to the next civilian
3. The medical team moves one cell per simulation step along this path
4. Every step, before moving, the system checks if the next cell on the path is still accessible
5. If a flood has blocked the next cell, A* is immediately re-run from the current position to find a new path
6. This continues until all civilians have been reached

### Cost weighting

Edge cost used by A* = base road cost × crime risk multiplier (see Challenge 5). This means high-crime areas are treated as harder to traverse, matching the project requirement.

### Output

- The path as a list of nodes to follow
- Real-time rerouting whenever a flood blocks the current path

---

## Challenge 5 — Crime Risk Prediction — `crime.py`

**Algorithm:** K-Means clustering (unsupervised) followed by KNN classification (supervised).

### Stage 1 — Clustering

- **k = 3** clusters (fixed, matching the three risk levels: High, Medium, Low)
- Features per node: `[populationDensity, proximityToIndustrial]`
- `proximityToIndustrial` = BFS hop count to the nearest Industrial node (lower = closer)
- K-Means groups nodes into 3 natural clusters without any labels
- The cluster with the highest average population and lowest industrial proximity = High risk
- The cluster with the lowest average population = Low risk
- Middle cluster = Medium risk

### Stage 2 — Synthetic dataset generation

For each node, assign a crime label using this rule:

```
score = (populationDensity * 0.6) + ((1 / (proximityToIndustrial + 1)) * 0.4)
```

- score > 0.66 threshold → High
- score > 0.33 threshold → Medium
- else → Low

This score formula is defensible: high population density and closeness to industrial zones correlate with higher crime likelihood in urban models. The thresholds divide the score range into thirds.

### Stage 3 — KNN classifier

- Train a KNN classifier (k=5 neighbours) on the synthetic dataset
- Features: `[populationDensity, proximityToIndustrial]`
- Labels: High / Medium / Low
- Predict the risk level for every node
- Feed predictions back into `cityGraph`: set each node's `riskIndex` field

### Crime risk as cost multiplier in A* and GA

| Risk Level | Cost Multiplier |
|---|---|
| Low | 1.25× |
| Medium | 1.75× |
| High | 2.5× |

These multipliers apply to the base road cost when A* or GA calculates traversal cost through a node. A node with no assigned risk defaults to 1.0× (no penalty).

### When it runs

Crime module runs **once after the CSP and MST are complete** but **before the simulation starts**. The risk indices are then baked into the graph weights for the entire simulation. If the simulation updates risk weights mid-run (future extension), that would require re-running the KNN predict step only — not the full pipeline.

---

## Simulation Loop — `simulation.py`

### Structure

- 20 steps total
- Each step does the following in order:
  1. Check if a random flood event occurs (30% chance per step)
  2. If flood: randomly pick an accessible edge, block it, log the event
  3. Move the medical team one cell along its current A* path
  4. If the next cell on the path is now blocked: re-run A* from current position, log the reroute
  5. Check if any ambulance is now on an inaccessible node: if yes, greedy-move it to nearest accessible neighbour
  6. Update the UI (redraw grid, overlays, event log)
  7. Pause briefly for visual clarity (configurable step delay)

### Flood probability

30% chance of a flood per step. This ensures floods happen regularly enough to demonstrate rerouting but not so often the city becomes impassable. This value can be adjusted from the UI settings.

### Step control

- Play button: run all remaining steps automatically with the step delay between each
- Pause button: halt between steps
- Step button: advance exactly one step manually
- The simulation does not loop after step 20 — it ends and shows a summary in the event log

---

## UI Design — `ui.py` + `eventLog.py`

### Layout

Two panels side by side:

- **Left (Pygame window):** The city grid — sprites, roads, overlays, ambulance positions
- **Right (Tkinter frame):** Settings panel at the top, event log scrollable text area at the bottom

### Grid rendering

- Each node is a square cell drawn in Pygame
- Building types are shown as sprites (placeholder coloured rectangles until sprites are ready)
- Roads are drawn as lines between connected nodes
- Flooded roads are drawn in blue
- The ambulance sprite moves one cell per step along its path

### Overlay toggles (buttons in Tkinter panel)

Three toggleable overlays drawn on top of the grid in Pygame:

| Toggle | What it shows |
|---|---|
| Road Network | Color-coded roads: white = standard, yellow = residential discount, blue = flooded |
| Ambulance Coverage | Heatmap shading per node: darker = farther from nearest ambulance |
| Crime Risk Heatmap | Red = High, Orange = Medium, Green = Low |

### Settings panel (Tkinter)

- Grid size input (default 10, min 5, max 20)
- Building count inputs: Hospitals, Schools, Industrial, Residential, Power Plants, Ambulance Depots
- Flood probability slider (default 30%)
- Step delay slider (speed of auto-play)
- Start Simulation button
- Reset button

### Click interactions

- Click any node: side panel shows its stats (type, population, risk level, accessibility)
- Flood tool: user clicks one node then an adjacent node, the road between them is flooded manually

### Event log (Tkinter text widget)

Scrollable, timestamped log at the bottom right. Examples:

```
[Step 3] Road (4,5)-(4,6) flooded automatically.
[Step 3] Medical team rerouted. New path length: 7 hops.
[Step 5] Ambulance at (2,3) relocated to (2,4) — node inaccessible.
[Step 7] Road (1,2)-(1,3) flooded automatically.
```

---

## Development Order

Build in this order so each module can be tested before the next one depends on it:

1. `cityGraph.py` — shared graph structure (all other modules need this)
2. `csp.py` — place buildings on the graph
3. `mst.py` — build roads on the graph
4. `crime.py` — assign risk weights to graph nodes
5. `ga.py` — place ambulances using the weighted graph
6. `astar.py` — route the medical team through the weighted graph
7. `simulation.py` — wire all modules into the 20-step loop
8. `ui.py` + `eventLog.py` — render everything visually
9. `main.py` — launch point that ties UI and simulation together

---

## Key Design Decisions (with reasoning for peer review)

**Why K-Means k=3?**
The downstream classifier predicts exactly 3 labels (High, Medium, Low). Using k=3 in clustering means the clusters map directly to these labels without any ambiguity. Elbow method would add complexity with no benefit here.

**Why GA runs once, not per step?**
The GA explores 50 chromosomes over 100 generations. Running this every step would introduce a multi-second delay per simulation step, making the UI feel broken. The GA's purpose is finding the *optimal initial placement*. The simulation then shows how the system adapts to disruptions using a fast greedy fallback — this demonstrates two different strategies (optimisation vs. reactive) which is actually a stronger viva talking point.

**Why Primary Hospital = closest to grid centre?**
This is deterministic (same result every run), simple to implement and explain, and reflects real urban planning logic where a central hospital serves the widest area. It requires no extra user input.

**Why separate files per module?**
Three group members, three ownership areas. Separate files prevent merge conflicts. Each file has one clear purpose. `cityGraph.py` is the shared interface and its public methods are the contract between all modules.

**Why Pygame + Tkinter together?**
Pygame is excellent at real-time grid rendering but has no native widget toolkit. Tkinter handles form inputs, scrollable text, and buttons cleanly. Embedding a Tkinter window alongside a Pygame surface gives the best of both. This is a well-known Python pattern and both libraries are already familiar to the team.

**Why Manhattan distance as A* heuristic?**
On a 4-directional grid, Manhattan distance is the true minimum possible distance between two nodes. It never overestimates, making it admissible. An admissible heuristic guarantees A* finds the shortest path. This is the exact answer needed for the viva question about heuristic choice.

---

## What to Implement Later (Not Now)

- Actual sprite assets (placeholders first, swap in later)
- UI polish and creative visual theme (to be designed as a group)
- Any extra simulation features beyond the 20-step loop

---
