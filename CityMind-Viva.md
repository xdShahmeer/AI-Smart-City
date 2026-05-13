# CityMind -- Comprehensive Viva/Demo Reference

**Group:** Zarrar Nadeem (24i-0735), Shahmeer Zubair (24i-0580), Raahim Babar (24i-0561)

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [System Architecture](#2-system-architecture)
3. [Boot-Up and Initialization Flow](#3-boot-up-and-initialization-flow)
4. [The Shared City Graph](#4-the-shared-city-graph)
5. [Challenge 1 -- CSP City Layout](#5-challenge-1----csp-city-layout)
6. [Challenge 2 -- Road Network (MST + A*)](#6-challenge-2----road-network-mst--a)
7. [Challenge 3 -- Ambulance Placement (GA)](#7-challenge-3----ambulance-placement-ga)
8. [Challenge 4 -- Emergency Routing (A*)](#8-challenge-4----emergency-routing-a)
9. [Challenge 5 -- Crime Risk Prediction (K-Means + KNN)](#9-challenge-5----crime-risk-prediction-k-means--knn)
10. [The Simulation Loop](#10-the-simulation-loop)
11. [UI Architecture](#11-ui-architecture)
12. [OOP Design and Controller Layer](#12-oop-design-and-controller-layer)
13. [Decision Justifications and Rejected Alternatives](#13-decision-justifications-and-rejected-alternatives)
14. [Viva Question Bank](#14-viva-question-bank)

---

## 1. Project Overview

CityMind is a grid-based urban intelligence system. The city is modelled as a graph where every grid coordinate is a node and every connection between adjacent nodes is a road (edge). Five AI modules operate on this shared graph to solve city planning, routing, optimization, and prediction challenges.

| Challenge | Algorithm | Module File | Purpose |
|-----------|-----------|-------------|---------|
| 1 | CSP (Backtracking + MRV + LCV + Forward Checking) | `csp.py` | Place buildings on the grid satisfying constraints |
| 2 | Kruskal's MST + A* dual-corridor | `mst.py` | Build minimum-cost road network with dual emergency routes |
| 3 | Genetic Algorithm | `ga.py` | Optimize ambulance placements for worst-case coverage |
| 4 | A* Search | `astar.py` | Route a medical team to civilians with dynamic rerouting |
| 5 | K-Means + KNN | `crime.py` | Predict crime risk levels and deploy police |

All modules share **one single `CityGraph` object** passed by reference. When one module writes data (e.g., sets a building type, marks a road as flooded, sets a risk index), every other module sees the change instantly.

---

## 2. System Architecture

```
main.py  (thin entry point)
  |
  +-- AppController (controller.py)   <-- OOP boundary, UI never touches simulation/graph directly
  |     |
  |     +-- CityGraph (cityGraph.py)  <-- shared graph, one instance, passed by reference to all modules
  |     +-- Simulation (simulation.py) <-- orchestrates CSP -> MST -> Crime -> GA -> A* in sequence
  |           |
  |           +-- csp.py   (Challenge 1)
  |           +-- mst.py   (Challenge 2)
  |           +-- crime.py (Challenge 5)
  |           +-- ga.py    (Challenge 3)
  |           +-- astar.py (Challenge 4)
  |
  +-- AppUI (ui.py)                  <-- single Tkinter window, 3-column layout
  |     +-- EventLog (eventLog.py)   <-- scrollable event log
  |
  Event flow: UI calls AppController -> AppController calls Simulation -> Simulation calls algorithm modules
  Event log: Simulation emits events via AppController -> AppUI.addLog -> EventLog.addEntry
```

**Critical OOP rule:** The UI (`AppUI`) ONLY ever calls `AppController`. It NEVER accesses `Simulation` or `CityGraph` directly. This is enforced by design.

**File listing:**

| File | Lines | Purpose |
|------|-------|---------|
| `main.py` | 27 | Entry point, builds controller and UI, wires event listener |
| `appController.py` | 209 | Controller mediating UI <-> simulation |
| `cityGraph.py` | 232 | Shared graph: nodes, edges, adjacency list, getters/setters |
| `csp.py` | 339 | CSP layout planner |
| `mst.py` | 232 | Kruskal's MST + dual A* emergency routes |
| `crime.py` | 211 | K-Means clustering + KNN classifier + police deployment |
| `ga.py` | 193 | Genetic algorithm for ambulance placement |
| `astar.py` | 143 | A* router with dynamic rerouting |
| `simulation.py` | 267 | 20-step simulation loop |
| `ui.py` | 1206 | Single-window Tk UI: Canvas grid + control panels |
| `eventLog.py` | 61 | Tkinter Text widget event log |

---

## 3. Boot-Up and Initialization Flow

### What happens when `python main.py` runs:

**Step 1: Controller creation**
```python
controller = AppController(DEFAULT_BUILDINGS, gridSize=10, floodProbability=0.30)
```
- Creates a `CityGraph(rows=10, cols=10)` -- 100 nodes, all type "Empty", all riskIndex=1.0, all accessible=True
- Creates 4-directional edges between every adjacent pair (180 total edges for 10x10)
- Edge costs: 0.8 if either endpoint is Residential, else 1.0
- Creates a `Simulation` wrapping the graph with default building counts

**Step 2: UI creation**
```python
appUI = AppUI(controller)
```
- Builds the Tkinter root window with 3-column layout
- Column 1: Status bar + city canvas (empty, grey grid)
- Column 2: Settings + Constraints + Mouse Tool + Overlays + Node Info panels
- Column 3: Legend + Event Log

**Step 3: Wire event listener**
```python
controller.setEventListener(appUI.addLog)
```
- Any event string emitted by the simulation or controller flows directly into the UI's event log

**Step 4: Setup UI**
```python
appUI.setup()
```
- Loads all sprite images (buildings, ground variants, ambulance, medical team, animated tree strip)
- Renders the initial empty canvas
- Initial status bar: "Press Generate City to build a city and begin the 20-step simulation."

**Step 5: Run**
```python
appUI.run()
```
- Starts the Tkinter main loop
- A 100ms tick (`_scheduleTick`) drives both the auto-step loop and the animated tree frames

### When the user clicks "Generate City":

1. **UI reads settings** from all input fields (grid size, building counts, flood probability, step delay, CSP hop limits, industrial adjacency toggle)
2. **UI calls `controller.startSimulation(settings)`**
3. **Controller calls `graph.reset(rows, cols)`** -- wipes everything, rebuilds grid
4. **Controller calls `simulation.rebuild(...)`** -- resets all simulation state
5. **Controller calls `simulation.setup()`** -- this triggers the full pipeline:
   - CSP places buildings on the graph
   - MST builds the road network and finds dual emergency routes
   - Crime assigns risk indices via K-Means + KNN
   - Police are deployed to top-10 highest-risk nodes
   - GA places 3 ambulances at optimal positions
   - A* initializes the router state with 5 civilians
6. **Setup events flow back** to the UI event log
7. **Canvas resizes** dynamically based on grid dimensions
8. **Status bar updates** to show "Step 0/20" with civilian/ambulance counts

The system is now ready for stepping, auto-play, or manual interactions.

---

## 4. The Shared City Graph (`cityGraph.py`)

### Data Model

**Grid:** Default 10x10 (configurable 5-20). Every coordinate `(row, col)` is a node.

**Node properties (per node):**
```python
{
    "type":       str,     # "Residential", "Hospital", "School", "Industrial",
                           # "PowerPlant", "AmbulanceDepot", or "Empty"
    "population": int,     # random within type-appropriate range (e.g. Residential: 50-200)
    "riskIndex":  float,   # starts at 1.0, set by crime module: 1.25/1.75/2.5 (Low/Med/High)
    "accessible": bool,    # False if flooded or blocked
}
```

**Edge properties (per edge between adjacent nodes):**
```python
{
    "cost":    float,  # 1.0 standard, 0.8 if either endpoint is Residential
    "blocked": bool,   # True if flooded
    "built":   bool,   # True if part of MST + emergency route network
}
```

**Population ranges per type:**

| Type | Min | Max |
|------|-----|-----|
| Residential | 50 | 200 |
| School | 100 | 400 |
| Industrial | 80 | 300 |
| Hospital | 30 | 150 |
| PowerPlant | 20 | 80 |
| AmbulanceDepot | 10 | 40 |
| Empty | 0 | 0 |

### Implementation

- **Adjacency list** as a dictionary: `graph[node] = list of (neighbour, edgeCost)`
- Connections only in **4 cardinal directions** (up, down, left, right) -- no diagonals
- Edges stored in a canonical key format via `edgeKey(nodeA, nodeB)` which returns `(smallerNode, largerNode)` for consistent lookup
- **Single object passed by reference** to all modules -- changes are instantly visible everywhere

### Key Getters/Setters

| Method | Purpose |
|--------|---------|
| `setNodeType(node, type)` | Assigns building type, random population, recalculates incident edge costs |
| `setRiskIndex(node, risk)` | Writes crime risk multiplier |
| `setAccessible(node, bool)` | Marks node as accessible/blocked |
| `floodEdge(a, b)` | Blocks an edge (symmetric, one call blocks both directions) |
| `unfloodEdge(a, b)` | Restores a blocked edge |
| `setBuiltEdges(list)` | Marks specific edges as part of the built road network |
| `getNeighbours(node, builtOnly=False)` | All or built-only neighbours |
| `getAccessibleNeighbours(node, builtOnly=False)` | Only unblocked reachable neighbours |
| `getEdgeCost(a, b)` | Base cost (returns `inf` if blocked) |
| `getWeightedCost(a, b)` | Base cost × destination node's riskIndex |
| `isEdgeBlocked(a, b)` | Quick blocked-status check |
| `isEdgeBuilt(a, b)` | Quick built-status check |
| `getAllNodes()` | All node coordinates |
| `getAccessibleNodes()` | Only accessible nodes |
| `getNodesByType(type)` | All nodes of a given building type |
| `getAllEdges()` | All edge keys |

### Graph State Fields (set by other modules)

```python
graph.primaryHospital     # (row, col) -- set by mst.py
graph.primaryDepot        # (row, col) -- set by mst.py
graph.ambulancePositions  # [(r1,c1), (r2,c2), (r3,c3)] -- set by ga.py
graph.policeOfficers      # [(r1,c1), ...] -- top 10 highest-risk, set by crime.py
graph.builtEdges          # list of canonical edge keys for MST + routes
```

---

## 5. Challenge 1 -- CSP City Layout (`csp.py`)

### Algorithm

**Backtracking search** with three constraint-propagation heuristics:

1. **MRV (Minimum Remaining Values):** Pick the unplaced building type with the fewest remaining valid grid positions. This reduces the branching factor by tackling the hardest-to-place buildings first.

2. **Approximate LCV (Least Constraining Value):** Score candidate cells by how many options they leave for other unplaced buildings. To keep backtracking fast on larger grids, only the first `LCV_SAMPLE = 8` cells are scored and the rest are appended unscored after a shuffle. This is approximate LCV -- the ordering still beats random and correctness is never lost because forward checking and the leaf proximity validation still gate every full assignment.

3. **Forward Checking:** After each assignment, check if any unplaced building type has zero remaining valid cells. If so, prune the branch immediately rather than descending deeper.

### Constraints (3 rules)

| ID | Constraint | When Checked |
|----|-----------|-------------|
| C1 | Industrial zones cannot be adjacent (4-directional) to Schools or Hospitals | During search (`getValidCells`) |
| C2 | Every Residential node must be within N hops of at least one Hospital (default N=3) | At the leaf (`validateProximity`) |
| C3 | Every Power Plant must be within N hops of at least one Industrial zone (default N=2) | At the leaf (`validateProximity`) |

C2 and C3 are checked only at the leaf of the backtracking tree because they require BFS which is expensive. Forward checking catches C1 violations during search, and C2/C3 are verified once we've placed all buildings.

### Why Forward Checking and NOT AC-3

Both are valid pruning strategies. Forward checking checks only the directly affected neighbour types after each assignment. AC-3 enforces full arc consistency across the entire constraint graph on every assignment, which is more powerful but also significantly more complex to code and harder to explain in a viva. For a 10x10 grid with a small number of buildings, forward checking catches the same violations that matter before wasting time on dead-end branches. AC-3 would add complexity with marginal benefit.

### Placement Order

Buildings are placed in priority order (hardest-to-constrain first):
1. Hospital (rare, needed by Residential)
2. Industrial (constrained by adjacency, needed by PowerPlant)
3. AmbulanceDepot (rare)
4. School (constrained by Industrial adjacency)
5. PowerPlant (needs Industrial nearby)
6. Residential (numerous, constrained by Hospital proximity)

Within backtracking, MRV overrides this static order dynamically per step.

### Minimum-Conflict Fallback

If no valid layout exists (backtracking exhausts the search space), the system:

1. Identifies which constraint caused the failure: `identifyWorstConstraint()` counts violations for each of the 3 constraints and returns the one with the most violations.
2. Places buildings greedily ignoring all constraints via `greedyPlace()`.
3. Logs a message like: `"Constraint failed: Residential-Hospital proximity. A minimum-conflict layout has been placed. Adjust the building counts and retry."`
4. The user can see the highlighted problem nodes and adjust building counts.

This satisfies the project requirement of "identify which specific rule is causing the conflict and propose minimum conflict solution."

### Live Modification Readiness

Three module-level constants are live-modifiable from the UI:

| Constant | Default | UI Control |
|----------|---------|------------|
| `RESIDENTIAL_MAX_HOPS` | 3 | "Residential hops" input in Constraints panel |
| `POWERPLANT_MAX_HOPS` | 2 | "PowerPlant hops" input in Constraints panel |
| `INDUSTRIAL_ADJACENCY_RULE` | True | Checkbox in Constraints panel |

These are threaded from UI -> `AppController` -> `Simulation` -> `runCSP(... residentialHops=, powerplantHops=, industrialAdjacencyRule=)`. The globals are saved/restored per run so overrides don't leak across "Generate City" re-runs.

### BFS Helper

`bfsHops(graph, startNode, targetType, maxHops)` performs bounded BFS to check if a target building type exists within N hops. Used by `isResidentialOk()` and `isPowerPlantOk()` for proximity validation. Stops early at maxHops to avoid unnecessary grid traversal.

---

## 6. Challenge 2 -- Road Network: MST + A* (`mst.py`)

### Algorithm Overview

The road network is built in two stages:

1. **Kruskal's MST** -- connects ALL nodes at minimum total cost
2. **Dual independent A* corridors** -- guarantees two completely disjoint paths between the Primary Hospital and Primary Depot

### Primary Node Selection

Among all Hospital nodes, the **Primary Hospital** is the node closest to the geometric centre of the grid (minimum Euclidean distance). Tiebreaker: lower row, then lower column. Same rule for **Primary Depot** among AmbulanceDepot nodes.

**Why closest to centre:** Deterministic, simple to compute, reflects real urban planning where a central hospital serves the widest area. No extra user input needed.

### Kruskal's MST (`buildMST`)

**Implementation:**
- Union-Find with **path compression** (`findRoot`) and **union by rank** (`unionByRank`)
- All edges sorted by cost using `sortByEdgeCost`
- Iterates sorted edges, adding each that doesn't create a cycle
- Stops when `numNodes - 1` edges are in the MST

**Time complexity:** O(E log E) dominated by edge sorting. For a 10x10 grid: 180 edges.

### Dual Emergency Corridors

Building the dual routes involves a carefully sequenced operation:

1. **Mark MST edges as built** via `graph.setBuiltEdges(mstEdges)` -- this is the base road network
2. **Find Route A:** Run A* from Primary Hospital to Primary Depot using only `built` edges (MST only at this point)
3. **Add Route A to built set** and mark its edges as built
4. **Temporarily block all Route A edges** using `graph.floodEdge()` -- this forces Route B to use different edges
5. **Find Route B:** Run A* from Primary Hospital to Primary Depot on ALL grid edges (`builtOnly=False`), but Route A edges are blocked, so it must find a completely independent path
6. **Restore Route A edges** via `graph.unfloodEdge()`
7. **Mark Route B edges as built** and add to the final built set

**Result:** Base MST network + two completely edge-independent emergency corridors.

### Why Remove the Full Route A Path (Not Just One Edge)?

Removing only one edge would make A* detour around that single edge but reuse most of Route A's other edges. The two routes would share the majority of their connections, meaning one flood event could still block both paths simultaneously. By removing ALL of Route A's edges during the Route B search, we force A* to find a path that shares ZERO edges with Route A -- a genuinely independent backup. The higher path cost is acceptable because the safety guarantee (no single flood can disconnect the hospital from the depot) is the actual requirement.

### A* Implementation in MST

Uses Manhattan distance heuristic, respects `graph.isEdgeBlocked()`, checks the `"built"` flag. Returns an ordered list of nodes from start to goal, or `[]` if no path exists.

### Events Emitted

```python
"[MST] Primary Hospital: (r, c)"
"[MST] Primary Depot:    (r, c)"
"[MST] Kruskal's MST built: N edges spanning M nodes."
"[MST] Route A: N edges, path length M nodes."
"[MST] Route B: N edges, path length M nodes."
"[MST] No independent Route B found -- city topology may be too constrained."
```

---

## 7. Challenge 3 -- Ambulance Placement: GA (`ga.py`)

### Algorithm

**Genetic Algorithm** -- evolution-inspired optimization.

### Problem Encoding

- **Chromosome:** A list of 3 node coordinates, e.g., `[(2,3), (7,1), (5,8)]`
- **Search space:** Any accessible node on the grid (not restricted to AmbulanceDepot nodes)

### Why Ambulances Can Be Placed on ANY Accessible Node

The project says ambulances should be "positioned at locations on the grid." Restricting to AmbulanceDepot nodes would make the GA's search space trivially small (often just 1-2 nodes) and defeat the purpose of optimization. The AmbulanceDepot type represents the home base; during simulation, ambulances are wherever the GA determined was optimal.

### Fitness Function

For a given chromosome (3 ambulance positions):

1. Run **Dijkstra's algorithm** from each ambulance position
2. For every accessible node in the graph, find the minimum weighted distance to the nearest ambulance
3. **Fitness = maximum of these distances** (worst-case response time)
4. Lower is better

Edge costs are `baseCost × riskIndex` of the destination node (`getWeightedCost`). This means high-crime areas are treated as more "expensive" to traverse, penalizing placements that require travelling through dangerous zones.

**Why Dijkstra and not BFS?** BFS treats every edge as weight 1. But crime risk multipliers make edges unequal -- a 2.5× high-crime edge is three times as "expensive" as a 0.8 residential edge. BFS would give incorrect distances. Dijkstra handles weighted edges correctly.

### GA Parameters

| Parameter | Value |
|-----------|-------|
| Population size | 30 |
| Generations | 60 |
| Mutation rate | 10% |
| Ambulances | 3 |
| Parents kept (elitism) | 15 (top 50%) |

### Loop Structure

1. **Initialization:** 30 random chromosomes, each with 3 distinct accessible node positions
2. **Per generation:**
   - Evaluate fitness of all 30 chromosomes using Dijkstra (with a **fitness cache** keyed by sorted-tuple to avoid re-evaluating the same chromosome)
   - **Elitism:** Keep top 15 as parents
   - **Crossover:** Pair up parents, split at random index to produce 15 children
   - **Duplicate fix:** `fixDuplicates()` ensures children don't have repeated positions
   - **Mutation:** 10% chance per child to replace one position with a random unused accessible node
   - Next generation = 15 parents + 15 children
3. After 60 generations, return the best chromosome found

### Role in Simulation

The GA runs **once** after the CSP, MST, and crime modules complete, to find the optimal initial ambulance placement.

**During the 20-step simulation**, ambulances can move in three ways:

1. **Risk-shift reposition** (every 5 steps): A crime wave bumps riskIndex on 3 random nodes. Each ambulance checks adjacent neighbours and moves if doing so improves worst-case coverage. This is a **greedy local hill-climb** using Dijkstra.

2. **Flood-forced relocation**: If an ambulance's current node becomes inaccessible (flooded), it moves to the nearest accessible neighbour.

3. **Static placement** otherwise: Ambulances stay where the GA placed them.

**Why GA runs once, not per step:** The GA explores 30 chromosomes × 60 generations × Dijkstra on ~100 nodes. Running this per step would cause multi-second delays between steps, breaking the simulation feel. The GA gives optimal static placement; the risk-shift reposition handles mid-simulation changes. Two strategies demonstrated -- optimal + reactive -- which is a stronger viva argument.

**Project statement compliance:** "Ambulance placements from Challenge 3 are re-evaluated as risk weights shift" -- satisfied by the periodic `_maybeShiftRisk` + `_greedyAmbulanceReposition` in `simulation.py`.

### Fitness Cache

Chromosomes are keyed by their sorted-tuple form: `tuple(sorted(chromosome))`. Since crossover and elitism can produce duplicate chromosomes across generations, the cache prevents re-running the same Dijkstra-heavy fitness computation. This is especially important since the top chromosome persists through elitism.

---

## 8. Challenge 4 -- Emergency Routing: A* (`astar.py`)

### Algorithm

**A* search** with **Manhattan distance heuristic**, scaled by the minimum edge cost (0.8) to maintain admissibility.

### Heuristic

```python
h(node) = 0.8 * (|node.row - goal.row| + |node.col - goal.col|)
```

**Why 0.8 scaling matters:** Edges have two possible costs: 1.0 (standard) and 0.8 (residential discount). Without scaling, the Manhattan distance heuristic (counting each step as 1.0) would overestimate the true cost on a path through residential roads. For example, 5 residential hops = true cost 5 × 0.8 = 4.0, but Manhattan estimates 5.0. That's an overestimate, which breaks admissibility. Scaling by the cheapest edge cost (0.8) makes 5 × 0.8 = 4.0, which never exceeds the true minimum cost. The heuristic is now admissible on ALL edges, guaranteeing A* finds the shortest path.

### Edge Costs for A*

`getWeightedCost(nodeA, nodeB)` = `baseEdgeCost × riskIndex[nodeB]`. High-crime areas are more costly to traverse, forcing the medical team to prefer safer routes.

### Medical Team Routing (`RouterState`)

**Starting position:** Primary Hospital (designated by `mst.py`).

**Civilians:** 5 randomly selected nodes that are actually reachable from the Primary Hospital via the built road network. `_generateCivilians()` validates connectivity with A* before adding any node as a civilian target, ensuring no civilian is placed on unreachable nodes.

**Sequential single-goal runs:**
A* is a single-source, single-goal algorithm. It cannot natively handle multiple destinations. The team is routed sequentially:
1. A* from current position to civilian 1 → follow path
2. Once civilian 1 is reached, A* from civilian 1 to civilian 2 → follow path
3. Continue until all civilians are reached or skipped

The order of civilians is fixed (the order they were selected). The team always targets the next civilian in the list.

### Per-Step Dynamic Rerouting

```python
def stepRouter(state, graph):
    # Called once per simulation step
    # Moves the medical team ONE cell along the current A* path

    # 1. Build new path if needed (no current path)
    # 2. Check if next cell is still accessible (not flooded/blocked)
    # 3. If blocked: re-run A* from current position to target civilian
    # 4. If re-run also finds no path: mark civilian as unreachable, skip to next
    # 5. If path clear: move one cell forward
    # 6. If destination reached: mark as reached, advance to next civilian
```

### Handling Unreachable Civilians

If A* finds no path (all routes to the civilian are blocked by floods):
1. Log: `"Civilian at (r,c) is unreachable -- all paths flooded. Skipping."`
2. Mark that civilian as `skipped`
3. Move to the next civilian on the list
4. Do not halt the simulation

### Traversal Restriction

`findPath()` calls `graph.getAccessibleNeighbours(current, builtOnly=True)`, which means the medical team only traverses edges that are both:
- Not flooded (`blocked=False`)
- Part of the built road network (`built=True`) -- MST + Route A + Route B edges

This enforces that the medical team uses the actual road network that Kruskal's MST constructed, not arbitrary grid adjacencies.

---

## 9. Challenge 5 -- Crime Risk Prediction: K-Means + KNN (`crime.py`)

### Three-Stage Pipeline

#### Stage 1: K-Means Clustering (Unsupervised)

| Parameter | Value |
|-----------|-------|
| k (clusters) | 3 (matching Low/Medium/High) |
| random_state | 42 (deterministic) |
| n_init | 10 |

**Features per node:** `[populationDensity, proximityToIndustrial]`

**`proximityToIndustrial`:** BFS hop count to the nearest Industrial node. Lower = closer = higher risk. If no Industrial nodes exist, fallback = `rows + cols`.

**Cluster-to-label mapping:** Clusters are sorted by their centroid's population density value. Highest average population → High risk, lowest → Low risk, middle → Medium.

#### Stage 2: Synthetic Label Generation (Supervised Ground Truth)

For each node, a crime score is computed using the formula:

```
score = (populationDensity × 0.6) + ((1 / (proximityToIndustrial + 1)) × 0.4)
```

The reciprocal `1/(proximity+1)` means closer proximity to industrial zones yields a higher component. Population density is weighted more heavily (0.6 vs 0.4) to reflect that occupancy is the stronger predictor of crime.

The score is normalized to [0, 1] by dividing by the maximum score. Then:

| Normalized Score | Label |
|-----------------|-------|
| > 0.66 | High |
| > 0.33 | Medium |
| ≤ 0.33 | Low |

The thresholds divide the range into equal thirds.

#### Stage 3: KNN Classifier (Supervised)

| Parameter | Value |
|-----------|-------|
| k (neighbours) | 5 |
| Features | `[populationDensity, proximityToIndustrial]` |
| Labels | High / Medium / Low (from synthetic formula) |

The KNN is **trained on the synthetic labels** from Stage 2 and predicts risk levels for all nodes.

### Why K-Means k=3?

The downstream KNN predicts exactly 3 labels (High, Medium, Low). Using k=3 means the clusters map naturally to these labels with no ambiguity. An elbow method would add complexity with no benefit for this problem.

### Why This Pipeline?

- **K-Means** provides an unsupervised discovery of natural groupings in the data. It tells us what the data looks like without any labels.
- **Synthetic formula** creates a defensible labelled dataset based on urban crime theory: high occupancy + proximity to industry correlates with higher crime.
- **KNN** is trained on the synthetic data, giving us a supervised classifier that can be explained (5-nearest-neighbour voting).
- **Cross-validation:** The code logs the agreement percentage between K-Means clusters and formula labels, showing the unsupervised view aligns with the synthetic rules.

### Risk Index Mapping

| Risk Level | riskIndex stored on node | Cost Multiplier effect |
|---|---|---|
| Low | 1.25 | road cost × 1.25 |
| Medium | 1.75 | road cost × 1.75 |
| High | 2.5 | road cost × 2.5 |

Before the crime module runs, all nodes default to `riskIndex = 1.0` (no penalty).

### Police Deployment

`deployPoliceOfficers(graph, count=10)` selects the top-10 nodes by `riskIndex` (highest first). These are rendered on the grid as blue "P" badges and listed in the legend.

### When It Runs

Crime module runs **once after CSP and MST are complete** but **before the simulation starts**. The risk indices are baked into the graph for the GA and A* to use.

**Mid-simulation risk shifts:** Every 5 steps, `_maybeShiftRisk()` bumps `riskIndex` on 3 random non-empty nodes by +0.25 (capped at 3.0) to simulate a shifting crime landscape. This satisfies the project requirement that risk weights change during the simulation.

---

## 10. The Simulation Loop (`simulation.py`)

### Setup Sequence (`setup()`)

Calls all modules in the correct dependency order:
```
1. csp.runCSP()          → places buildings on graph
2. mst.buildRoadNetwork() → builds MST + Route A + Route B
3. crime.runCrime()       → assigns riskIndex via K-Means + KNN
4. crime.deployPoliceOfficers() → places 10 police on highest-risk nodes
5. ga.runGA()            → places 3 ambulances via genetic optimization
6. astar.initRouter()    → creates RouterState with 5 civilians
```

### Step Sequence (`step()`)

Each step executes in this order:

```
1. Random flood check (probability from settings, default 30%)
   → Pick one random unblocked edge between accessible nodes
   → Mark it as blocked (symmetric, visible to all modules immediately)

2. Risk shift check (every 5 steps: 5, 10, 15, 20)
   → Bump riskIndex on 3 random non-empty nodes by +0.25
   → Greedy reposition each ambulance: check adjacent neighbours, move if improves worst-case coverage

3. Medical team movement (astar.stepRouter)
   → Move one cell along current A* path
   → Re-route if next cell is blocked
   → Skip civilian if no path exists

4. Ambulance flood-forced relocation
   → If any ambulance is on an inaccessible node, move to first accessible neighbour
```

### Step Extension

The simulation nominally has 20 steps. However:

- If civilians are still pending after step 20, the simulation extends up to +30 extra steps (capped) to let the medical team continue. `isFinished()` only returns True when the budget is exhausted AND no civilians are pending.
- If the user manually adds emergencies via the Emergency tool while the simulation has finished, extra steps are granted automatically.

### Risk-Shift Event (`_maybeShiftRisk` + `_greedyAmbulanceReposition`)

**Purpose:** Satisfies the project statement's requirement that "ambulance placements are re-evaluated as risk weights shift."

**How it works:**
1. Every 5 steps (5, 10, 15, 20), select 3 random non-empty accessible nodes
2. Bump each node's `riskIndex` by +0.25 (cap at 3.0)
3. Log the crime wave event
4. For each ambulance, run a local hill-climb: compute Dijkstra from the current position, then from each adjacent neighbour. If any neighbour provides strictly better worst-case coverage, move there.

**Performance:** At most 3 ambulances × (1 + 4 neighbours) = 15 Dijkstra runs. Each Dijkstra on a 20×20 grid takes a few milliseconds -- acceptable within a single step.

### Flood Events

- 30% chance per step (configurable via UI slider 0%-100%)
- Picks a random edge between two accessible nodes
- The edge becomes immediately blocked, visible to all modules
- Logged: `"[Step N] Road (r,c)-(r,c) flooded automatically."`

### Manual Interactions During Simulation

- **Flood tool:** Two-click adjacent cells to manually flood a road
- **Emergency tool:** Click any accessible node to append a civilian to the medical team's queue
- Both are routed through `AppController`, which validates and applies the change to the shared graph

---

## 11. UI Architecture (`ui.py`)

### Layout

Single Tkinter window with a **three-column layout**:

| Column | Content |
|--------|---------|
| **Left** | Status bar (top ribbon showing Step X/20, civilians, ambulances) + City grid Canvas |
| **Middle** | Settings panel + Constraints panel + Mouse Tool radio + Overlay toggles + Node Info panel |
| **Right** | Legend panel + Event Log (fills remaining vertical space) |

### Dynamic Cell Sizing

`_computeCellSize()` targets a ~600px canvas. On "Generate City", the canvas resizes proportional to the grid size, sprites are reloaded at the new cell size, and the Tk root snaps to its natural dimensions with `geometry("")` to prevent cropping.

### Sprite System

Sprites are loaded from `assets/` via `PIL.ImageTk.PhotoImage`:

| Building Type | Sprite File |
|--------------|-------------|
| Hospital | `building1.png` |
| School | `school.png` |
| Residential | `building2.png` |
| Industrial | `factory2.png` |
| PowerPlant | `building1.png` |
| AmbulanceDepot | `building2.png` |
| Ambulance | `ambulance.png` |
| Medical Team | `medical_team.png` |

**Empty cells** use ground variants (`grass.png`, `wavy_grass.png`, `flower_ground.png`, `stoned_grass.png`) picked deterministically per coordinate for visual variety that is stable across renders.

**Animated trees:** `spr_tree_animated.png` (2496×64 strip, 39 frames of 64×64) is sliced at load time. About 1 in 7 Empty cells deterministically becomes a "tree cell" and displays the current animation frame. A 100ms tick advances frames.

**Fallbacks:** If any sprite file is missing, building types render as coloured rectangles, ambulances render as a white square with a red cross, and the medical team renders as a cyan "MED" square.

### Three Overlay Toggles

| Overlay | What It Shows |
|---------|--------------|
| **Road Network** | Built roads: white (standard cost), yellow (residential discount), blue (flooded). Non-built edges: faint dark grey (1px thin) |
| **Ambulance Coverage** | Heatmap per node: green-close to red-far, based on multi-source weighted Dijkstra distances from all ambulances. Recomputes every render so floods reflect immediately. |
| **Crime Risk** | Green→yellow→red gradient over `riskIndex ∈ [1.0, 3.0]`. Smooth interpolation, not discrete bands. |

### Three Mouse Tools

| Tool | Action |
|------|--------|
| **Inspect** | Click any cell to view its stats in the Node Info panel (type, population, riskIndex, accessibility) |
| **Flood** | Two-click: click first cell (blue ring appears), click adjacent second cell -- the connecting road is flooded |
| **Emergency** | Click any accessible cell to append a civilian to the medical team's queue. Pending civilians render as red `!` rings. |

### Control Buttons

| Button | Action |
|--------|--------|
| **Generate City** | Reads all settings, runs full setup pipeline, renders city |
| **Reset** | Clears everything, resets simulation state |
| **Step** | Advances 1 simulation step |
| **Play/Pause** | Toggles auto-play at the configured step delay |

### Settings Panel

- Grid size: 5-20 (input field)
- Building counts: 6 input fields for each type
- Flood probability: 0%-100% slider
- Step delay: 0-2 second slider (auto-play speed)

### Constraints Panel (Live Modification)

- Residential hops (input, default 3)
- PowerPlant hops (input, default 2)
- Industrial adjacency rule (checkbox, default ON)
- Hint text: "Edit these and re-Generate to test the city under different rules."

### Status Bar

Displays: `Step X/20   Civilians: N reached / M pending / K skipped   Ambulances: A`

During extended steps (past 20): `Step X/20 +N (extended)`

### Event Log

- `Consolas` monospace font, dark terminal theme (bg=#161623, fg=#7ce9b3)
- Auto-scrolls to bottom on each entry
- Read-only, scrollbar on the right
- Visual separators between major sections

### Rendering Pipeline (`_render()`)

Called on every 100ms tick, redraws all layers in order:
1. Nodes (sprites or overlay colours)
2. Roads (lines between centres, coloured by type and status)
3. Routes (thick orange line = Route A, thick green line = Route B)
4. Medical path (yellow dashed line showing planned A* route)
5. Police officers (blue "P" badges in cell corners)
6. Active emergencies (red "!" rings on pending civilian cells)
7. Ambulances (ambulance sprite or fallback cross)
8. Medical team (sprite or cyan "MED" square)
9. Flood selection (blue ring on first-click cell)

---

## 12. OOP Design and Controller Layer

### Strict Boundary

```
UI (AppUI)  ──calls──>  AppController  ──calls──>  Simulation  ──calls──>  Algorithm Modules
                                                ──calls──>  CityGraph (shared object)
```

The UI never directly accesses `Simulation` or `CityGraph`. All mutations and queries go through `AppController`'s public methods:

| Controller Method | Purpose |
|------------------|---------|
| `startSimulation(settings)` | Full setup pipeline |
| `stepSimulation()` | Advance 1 step |
| `autoStepIfDue(stepDelay)` | Time-gated auto-step |
| `resetSimulation(settings)` | Wipe and rebuild |
| `getNodeInfo(node)` | Read node data for UI |
| `floodEdge(a, b)` | Manual flood tool |
| `addEmergency(node)` | Manual emergency tool |
| `getActiveEmergencies()` | List pending civilians |
| `getCoverageDistances()` | Multi-source Dijkstra for coverage overlay |
| `getGraph()` | Read-only graph access (for rendering) |
| `getSimulation()` | Read-only simulation access (for status) |
| `getRouterState()` | Read router state (for medical team drawing) |
| `getRoutes()` | Read Route A / Route B edge lists |
| `isSetupDone()` | Check if simulation is ready |
| `isFinished()` | Check if simulation is complete |
| `setEventListener(callback)` | Wire UI's `addLog` as event listener |

### Event Flow

```
Simulation emits event string
  → AppController._emitEvents() 
    → AppController._eventListener (i.e., AppUI.addLog)
      → EventLog.addEntry()
```

The controller's `setEventListener(callback)` method stores the UI's `addLog` function. Whenever the simulation generates an event, it flows through the controller to the event log automatically. The UI never polls the simulation for events.

---

## 13. Decision Justifications and Rejected Alternatives

### 13.1 Why Forward Checking, Not AC-3?

| Approach | Pros | Cons |
|----------|------|------|
| Forward Checking | Simple to implement, sufficient for 10x10 grid with small building count | Less pruning power than AC-3 |
| AC-3 (Arc Consistency) | Maximum pruning power, catches all arc inconsistencies | Significantly more complex to code, harder to explain in viva, overkill for our problem size |

**Decision:** Forward checking. It catches the violations that matter before descending into dead-end branches, and is 10× simpler to explain. For our problem size, the pruning difference is negligible.

### 13.2 Why Approximate LCV (LCV_SAMPLE = 8)?

Full LCV would score every candidate cell (up to 100 for a 10×10 grid) by temporarily placing a building, evaluating how many options remain for other types, then reverting. With 6 building types and potentially 100 cells per type, this becomes expensive inside a backtracking search that may explore thousands of branches.

**Decision:** Score only the first 8 shuffled candidates, append the rest unscored. The heuristic ordering still beats random placement, and correctness is never compromised because forward checking and leaf validation still gate every full assignment.

### 13.3 Why Remove Full Route A Path for Route B?

| Approach | Result | Risk |
|----------|--------|------|
| Remove 1 edge | Route B shares 80%+ of edges with Route A | One flood can block both |
| Remove all Route A edges | Route B shares 0 edges with Route A | Higher path cost, true independence |

**Decision:** Remove all Route A edges. The safety guarantee of "no single flood can disconnect the hospital from the depot" is the actual project requirement. The higher cost is the price of genuine independence.

### 13.4 Why Dijkstra in GA Fitness, Not BFS?

| Approach | Edge weights | Correctness |
|----------|-------------|-------------|
| BFS | Assumes all edges = 1 | Wrong when edges have different costs (0.8 vs 1.0) and risk multipliers (1.25×, 1.75×, 2.5×) |
| Dijkstra | Handles weighted edges | Correct for all edge weights |

**Decision:** Dijkstra. A high-crime edge costs 2.5× more to traverse. BFS would treat it as equal to a safe residential road, giving wrong distances and making the GA optimize for the wrong metric.

### 13.5 Why GA Runs Once, Not Per Step?

| Approach | Per-step cost | Simulation feel |
|----------|-------------|-----------------|
| Full GA each step | 30 chromosomes × 60 generations × Dijkstra = ~1800 Dijkstra runs | Multi-second freeze between steps |
| Initial GA + greedy reposition | 1 GA run (initial) + periodic cheap hill-climb | Smooth 100ms ticks |

**Decision:** GA runs once for optimal initial placement. Mid-simulation risk shifts trigger a cheap greedy local hill-climb (at most 15 Dijkstra runs per event) instead of a full GA rerun. Two strategies demonstrated -- optimal static + reactive local -- which is academically stronger.

### 13.6 Why Manhattan Distance × 0.8 as A* Heuristic?

**Problem:** Standard Manhattan distance `|dx| + |dy|` counts each step as cost 1.0. But residential roads cost 0.8. On a path of 5 residential steps, Manhattan estimates 5.0 while true cost is 4.0 -- an overestimate, breaking admissibility. A* loses its shortest-path guarantee.

**Fix:** Scale by the minimum possible edge cost: `0.8 × (|dx| + |dy|)`. Now 5 residential steps estimates as 4.0, which equals the true minimum cost. The heuristic is admissible on all edges.

**Alternative rejected:** Unscaled Manhattan with the argument "it's admissible on standard-cost edges." This is a weaker defence -- the heuristic demonstrably overestimates on residential paths.

### 13.7 Why Sequential Single-Goal A* Runs?

A* is fundamentally a single-source, single-goal algorithm. It does not natively handle multi-goal routing.

**Alternative considered:** Run Dijkstra once from the team's position and extract paths to all civilians. This gives multi-goal distances but doesn't respect the sequential constraint (the team must visit civilians in order).

**Decision:** Sequential A* runs -- reach civilian 1, then re-run from civilian 1 to civilian 2. Simple, correct, and easy to explain. The "visit in given order" constraint is satisfied naturally.

### 13.8 Why K-Means k=3, Not Elbow Method?

**Decision:** k=3 maps directly to the 3 risk levels (Low/Medium/High) required by the downstream KNN classifier. The elbow method would find the "natural" number of clusters in the data, which might not be 3, creating a mapping problem. k=3 is simple, deterministic, and exactly matches the spec.

### 13.9 Why tkinter, Not pygame?

| Framework | Pros | Cons |
|-----------|------|------|
| Tkinter | Built into Python, supports forms AND 2D canvas, scrollable text, sliders, buttons natively | Slightly clunkier 2D API |
| Pygame | Excellent 2D rendering, smooth animation | No native form widgets, no scrollable text, requires separate window or hacky integrations |

**Decision:** Tkinter (single window). The project needs both a grid canvas AND form controls. Tkinter handles both in one library with one window. Pygame was removed in the refactor because Tk's Canvas does everything we need for grid sizes up to 20×20 at 100ms ticks.

### 13.10 Why Three-Tier Spatial Partition Strategy?

The code uses a specific pattern for determining cell visuals:

```
if overlayMode == "coverage":     → Dijkstra-based heatmap
elif overlayMode == "crime":      → riskIndex gradient
else:                              → sprite-based rendering (normal mode)
```

This keeps each overlay's rendering logic isolated and avoids expensive recomputation when toggling. Coverage distances are re-fetched every render frame (cheap with controller's cached Dijkstra), but the crime risk gradient reads from node data that was set once during setup (plus periodic risk shifts).

### 13.11 Why Civilians are Connectivity-Validated

`_generateCivilians()` runs an A* path-finding check before selecting any node as a civilian target. This prevents placing civilians on nodes that are physically inaccessible from the Primary Hospital via the built road network. Without this check, up to 40% of civilians could start unreachable on a typical grid where only MST + route edges are built.

---

## 14. Viva Question Bank

### General Architecture

**Q: How does the system coordinate five AI modules on one shared graph?**

A: All modules receive the same `CityGraph` object by reference. When one module writes data (e.g., CSP sets a building type, crime sets a risk index, MST marks edges as built), every other module sees the change instantly because they all hold a reference to the same object. The `Simulation.setup()` method calls modules in dependency order: CSP → MST → Crime → GA → A*. The `step()` method then calls A*'s router and checks floods/risk-shifts on the same shared graph.

**Q: Why do you have a controller layer between the UI and simulation?**

A: It enforces a clean OOP boundary. The UI never directly mutates the graph or simulation state. All interactions go through `AppController` methods like `floodEdge()`, `addEmergency()`, `stepSimulation()`. This means we could replace the entire UI with a different framework without touching a single line of simulation or algorithm code. It also makes testing easier -- the controller can be tested without a GUI.

### Challenge 1 (CSP)

**Q: Walk me through your CSP solution.**

A: We use backtracking search with three heuristics:
1. **MRV** -- picks the building type with fewest valid placement options, reducing branching
2. **Approximate LCV** -- scores only 8 candidate cells per choice, picking the one that leaves the most options for others
3. **Forward Checking** -- after each assignment, verifies all remaining types still have valid cells; prunes immediately if not

Constraints C2 (Residential within 3 hops of Hospital) and C3 (PowerPlant within 2 hops of Industrial) are checked only at the leaf via BFS, because they're expensive to check during search. Constraint C1 (Industrial adjacency) is checked during search via `getValidCells`.

**Q: What happens if no valid layout exists?**

A: We run `identifyWorstConstraint()` which counts violations for each of the 3 constraints and identifies which one caused the failure. Then `greedyPlace()` places buildings ignoring constraints to give the user a minimum-conflict layout. A clear message tells the user which constraint failed and suggests adjusting building counts.

**Q: Why forward checking and not AC-3?**

A: Forward checking checks only the directly affected types after each assignment. AC-3 maintains full arc consistency across the entire constraint graph. For a 10×10 grid with ~25 buildings, forward checking catches the same violations before dead-end branches, and is significantly simpler to code and explain. AC-3 would add complexity with marginal pruning benefit at our problem size.

**Q: Your LCV is approximate -- how does that affect correctness?**

A: It doesn't. LCV is a heuristic for ordering -- it tells us which cell to try first. Even if the heuristic ordering is approximate, forward checking still catches constraint violations, and the leaf proximity validation (BFS for C2/C3) still gates every full assignment. A wrong LCV order just means we might explore more branches before finding the solution, but we'll never accept an invalid one.

### Challenge 2 (MST)

**Q: Why does Route B need zero shared edges with Route A?**

A: The project demands two "completely independent" emergency corridors between the Primary Hospital and Primary Depot. If Route B shares edges with Route A, a single flood on a shared edge blocks both routes simultaneously. By blocking all of Route A's edges during the Route B search, we force A* to find a path that shares zero edges -- a genuinely independent backup. One flood can never disconnect the hospital from the depot.

**Q: How do you pick the Primary Hospital?**

A: Euclidean distance from each Hospital node to the geometric centre of the grid. The closest wins. Tiebreaker: lower row, then lower column. Same rule for Primary Depot. This is deterministic, reflects real urban planning (central hospital serves the widest area), and requires no user input.

**Q: Why Kruskal's and not Prim's?**

A: Both produce the same MST. Kruskal's is simpler to implement on our graph representation because we already store edges in a canonical key format and can sort them directly. With Union-Find (path compression + union by rank), the edge-sorting dominates at O(E log E) which is fast enough for 180 edges on a 10×10 grid.

### Challenge 3 (GA)

**Q: Why can ambulances be placed on any node, not just AmbulanceDepot nodes?**

A: Restricting to depot nodes would make the GA's search space trivially small (often 1-2 depots) and defeat the purpose of optimization. The project says "positioned at locations on the grid" -- any accessible node qualifies. The AmbulanceDepot type represents the home base, not the only valid position.

**Q: How does your fitness function work?**

A: For each chromosome (3 ambulance positions), we run Dijkstra from each ambulance to compute weighted distances to every accessible node. For each node, we take the minimum distance to the nearest ambulance. The fitness score is the maximum of these values -- the worst-case response time. Lower is better. We use Dijkstra because edges have different weights (0.8 residential, 1.0 standard, scaled by riskIndex).

**Q: How do ambulances respond to changing risk weights mid-simulation?**

A: Every 5 steps, `_maybeShiftRisk()` bumps riskIndex on 3 random nodes by +0.25 to simulate a crime wave. Then `_greedyAmbulanceReposition()` runs a local hill-climb: each ambulance checks its adjacent neighbours, computes Dijkstra from each neighbour, and moves if doing so improves worst-case coverage. This is cheap (at most 15 Dijkstra runs) compared to the full GA (1800 Dijkstra runs), so the simulation stays smooth.

### Challenge 4 (A*)

**Q: Is your A* heuristic admissible? Prove it.**

A: Yes. Our heuristic is `0.8 × (|dx| + |dy|)`. The minimum possible edge cost in our graph is 0.8 (residential-discounted roads). Since every path from the current node to the goal must cross at least `|dx| + |dy|` edges, and each edge costs at minimum 0.8, the true minimum cost is at least `0.8 × (|dx| + |dy|)`. The heuristic equals this minimum bound, so it never overestimates the true cost. The heuristic is admissible, guaranteeing A* finds the shortest path.

**Q: Why did you scale by 0.8?**

A: Without scaling, Manhattan distance counts each step as 1.0. On a path through 5 residential roads (cost 0.8 each), Manhattan estimates 5.0 while the true cost is 4.0. That's an overestimate -- the heuristic would not be admissible. Scaling by the minimum edge cost (0.8) fixes this: 5 × 0.8 = 4.0, which never exceeds the true minimum.

**Q: How do you handle multiple civilians with A*?**

A: A* is a single-source, single-goal algorithm. We route the team to civilians sequentially: run A* from the current position to civilian 1, follow the path step-by-step, then run A* from civilian 1's position to civilian 2, and so on. The order is fixed (the order civilians were selected). This keeps the logic simple and correct.

**Q: What happens if a flood blocks the team's current path?**

A: `stepRouter` checks the next cell before moving. If it's blocked (edge flooded or node inaccessible), it immediately re-runs A* from the current position to the target civilian. If A* now finds a different path, the team continues. If A* finds no path at all, the civilian is marked as unreachable, skipped, and the team moves to the next civilian.

### Challenge 5 (Crime)

**Q: Walk me through your three-stage crime pipeline.**

A:
1. **K-Means (unsupervised):** Clusters all nodes on `[population, proximityToIndustrial]` into 3 groups. Clusters are labelled High/Medium/Low by sorting centroid population density.
2. **Synthetic formula (supervised ground truth):** `score = (pop × 0.6) + (1/(proximity+1) × 0.4)`. Normalized to [0,1], thresholded at 0.66 and 0.33. This creates a labelled dataset based on urban crime theory.
3. **KNN (k=5, supervised):** Trained on the synthetic labels, predicts risk for all nodes. Risk levels are written back as `riskIndex` multipliers (1.25, 1.75, 2.5) into the shared graph.

We also cross-validate: the code logs the agreement percentage between K-Means clusters and synthetic labels, showing the unsupervised clusters align with our formula.

**Q: Why k=3 for K-Means?**

A: The downstream KNN predicts exactly 3 labels. Using k=3 means the clusters map directly to Low/Medium/High with no ambiguity. An elbow method would find the "natural" number of clusters, which might not be 3, making mapping to our 3 risk labels messy.

**Q: How do police officers work?**

A: After crime analysis, `deployPoliceOfficers()` selects the top-10 nodes with the highest `riskIndex` values and stores them on `graph.policeOfficers`. They render as small blue "P" badges in the cell corners. This is a static deployment based on the initial risk snapshot -- they don't move during simulation.

### Simulation

**Q: What happens if the simulation reaches step 20 but civilians are still pending?**

A: `isFinished()` only returns True when `currentStep >= totalSteps` AND there are zero pending civilians, capped at +30 extra steps. The status bar shows `"Step X/20 +N (extended)"` and the summary reports the actual step count, not the nominal total.

**Q: How do floods work technically?**

A: `graph.floodEdge(nodeA, nodeB)` sets `edge["blocked"] = True` on the canonical edge key. Since all modules reference the same graph object, the blocked edge is immediately invisible to `getAccessibleNeighbours()` and returns `float('inf')` from `getEdgeCost()`. Both A* and GA Dijkstra respect this instantly. Floods are symmetric -- one call to `floodEdge` blocks travel in both directions.

**Q: How does the risk shift work technically?**

A: `_maybeShiftRisk()` fires when `currentStep % 5 == 0`. It picks 3 random non-empty accessible nodes, reads their current `riskIndex`, adds 0.25 (capped at 3.0), and calls `graph.setRiskIndex()`. Since all modules share the same graph, the A* router and coverage Dijkstra immediately use the new weights.

### UI

**Q: How does the UI render the grid efficiently?**

A: The entire canvas is cleared and redrawn every 100ms tick via `_render()`. For a 10×10 grid (100 nodes + 180 edges), this is trivially cheap in Tkinter Canvas. All sprites are pre-loaded and cached as `PhotoImage` objects. The coverage overlay re-fetches multi-source Dijkstra distances each render frame via `controller.getCoverageDistances()` -- this is the only non-trivial computation per frame, and it runs in under a millisecond on our grid sizes.

**Q: How do manual tools (Flood, Emergency) work?**

A: The UI handles click detection and routing (`_onCanvasClick` maps pixel coordinates to (row, col) via integer division). It then calls `controller.floodEdge()` or `controller.addEmergency()`. The controller validates the request (adjacency check, accessibility check, duplicate check) and mutates the shared graph only if valid. Event strings flow back through the controller's event listener into the event log.

**Q: How are sprites managed?**

A: All sprite images are loaded once in `_loadSprites()` and cached as instance attributes. When cell size changes (on Generate City), sprites are reloaded at the new size. If a PNG file is missing, the code catches the exception and falls back to coloured rectangles or drawn shapes (ambulance cross, MED square). The animated tree strip is sliced at load time into 39 individual `PhotoImage` frames; the current frame is selected by `_treeFrameIndex` which advances each tick.

### Live Modification

**Q: How does the Constraints panel work?**

A: The panel exposes three CSP parameters: Residential hop limit, PowerPlant hop limit, and Industrial adjacency toggle. When the user changes these and clicks "Generate City", the UI reads the values, packages them into the settings dict, and the controller threads them through `Simulation.rebuild()` to `csp.runCSP(residentialHops=, powerplantHops=, industrialAdjacencyRule=)`. The CSP globals are saved and restored per run so overrides don't leak across "Generate City" clicks.

**Q: What else is live-modifiable?**

A: Grid size (5-20), all 6 building counts, flood probability (0-100%), step delay (0-2s). Changes take effect on the next "Generate City" click, which wipes the graph and rebuilds everything.

### Design and Style

**Q: Why are getters and setters at the bottom of every class?**

A: It's a consistent style rule: constructor and core operations at the top, read/write surface at the bottom. Any developer (or examiner) can find the public API surface instantly by scrolling to the bottom of any class. This pattern is applied in `CityGraph`, `Simulation`, `AppController`, and `AppUI`.

**Q: Why is there no "tentative" naming in the A* code?**

A: A specific style rule. Instead of `tentativeG` or `tentativeCost`, we use `nextCost` for the candidate g-score of a neighbour node. The name is concrete and tells you what it is (the next cost being considered), not how it was derived.

**Q: Why are all `lambda` functions and complex comprehensions removed?**

A: The codebase targets beginner readability. A first-year CS student should be able to follow any function in 30 seconds. Named helper functions, explicit loops, and spelled-out variable names (e.g., `centreX` not `cx`, `neighbour` not `nb`) make the code self-documenting.

---
*End of CityMind Viva/Demo Reference*
