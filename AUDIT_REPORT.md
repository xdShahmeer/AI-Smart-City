# CityMind — Comprehensive Code Audit Report

**Date:** 10th May 2026
**Scope:** All 11 Python source files, CLAUDE.md, Project Statement (DOCX), Phase 1 Report (PDF), and cross-module integration.

---

## Overall Verdict

The project is **demonstration-ready**. All five challenge algorithms are correctly implemented, the simulation loop wires them in the right order, and the UI is polished. There are **2 significant functional gaps** and 3 minor issues. None prevent the system from running end-to-end, but these should be patched for a strong viva defence.

---

## Per-Module Summary

| Module | Status | Issues |
|--------|--------|--------|
| `cityGraph.py` | PASS | None |
| `csp.py` | PASS | 1 low (unused parameter) |
| `mst.py` | PASS | 1 high (MST doesn't restrict navigation) |
| `crime.py` | PASS | None |
| `ga.py` | PASS | 1 high (static risk weights — see integration section) |
| `astar.py` | PASS | None |
| `simulation.py` | PASS | Integration gap (risk weights) |
| `appController.py` | PASS | None |
| `ui.py` | PASS | None |
| `eventLog.py` | PASS | None |
| `main.py` | PASS | None |

---

## Detailed Findings

### ISSUE #1 — HIGH — MST edges don't restrict the traversable road network

**Files:** `mst.py`, `cityGraph.py`

The graph creates ALL possible edges between adjacent nodes in `_buildGrid()`. `buildMST()` computes the minimum spanning tree, but its result is only used for a log message — the `mstEdges` list is never stored or used to restrict which edges are traversable. Every adjacent pair is navigable by the medical team and ambulances, making the MST result decorative rather than functional.

The project statement says: *"Your system must determine which roads should be built. The goal is to connect all locations using the minimum total road cost."*

**Proposed fix:** Add a `"built": False` field to edge data in `cityGraph.py`. Mark all MST edges AND Route A/Route B edges as `built=True` in `buildRoadNetwork()`. Add a `builtOnly` parameter to `getNeighbours()` and `getAccessibleNeighbours()` — when `True`, only return neighbours connected by a built edge. All routing modules should use `builtOnly=True`. This requires touching `cityGraph.py` (add the field and filter), `mst.py` (mark edges), and verifying all callers of `getNeighbours`/`getAccessibleNeighbours`.

**Effort:** ~30 min

---

### ISSUE #2 — HIGH — Risk weights do not shift mid-simulation; ambulances are not re-evaluated

**Files:** `simulation.py`, `ga.py`

The project statement (DOCX Section 4) says: *"As the simulation progresses, ambulance placements from Challenge 3 are re-evaluated as risk weights shift."*

Currently:
- `crime.runCrime()` sets `riskIndex` once during `Simulation.setup()`
- `ga.runGA()` runs once immediately after
- During the 20-step loop, `riskIndex` never changes
- Ambulances only move reactively when their node floods

**Proposed fix:** Add a risk-shift event to the simulation loop that fires periodically (e.g., every 5 steps):
1. Randomly bump `riskIndex` on 2-3 nodes by +0.25 to +0.50 (simulating a crime wave)
2. After the bump, run a **greedy local hill-climb** for each ambulance: check neighbouring nodes and the newly high-risk nodes; if a simple swap improves coverage (based on a quick Dijkstra re-evaluation of only the affected nodes), reposition the ambulance
3. Log: `[Step N] Risk weights shifted. Ambulance at (r,c) repositioned to (r',c').`

This is a cheap partial re-evaluation — not a full GA re-run — so it doesn't break the simulation flow. It satisfies the spec's "re-evaluated as risk weights shift" requirement and gives a strong live-modification talking point for the viva.

**Alternative (defence-only):** Argue that "risk weights shift" refers to the initial bake-in from 1.0 to the crime-predicted values, and the GA then re-evaluates placements based on those new weights during setup. This requires no code changes but is weaker under viva scrutiny.

**Effort:** 1-2 hours (recommended)

---

### ISSUE #3 — MEDIUM — CLAUDE.md GA parameters are inconsistent

**File:** `CLAUDE.md`, lines 351-359

The "How it works" section of the GA description still says *"Generate 50 random valid placements... Select top 50% (25 chromosomes)... Repeat for 100 generations."* The actual code uses `POPULATION_SIZE=30`, `NUM_GENERATIONS=60`, and `NUM_PARENTS=15`. The "Setup" section of CLAUDE.md (lines 340-343) is correct — only the "How it works" narrative is stale.

**Proposed fix:** Update lines 353-359 to match the code values.

**Effort:** 2 min

---

### ISSUE #4 — LOW — Unused `assignment` parameter in `getValidCells`

**File:** `csp.py`, line 99

```python
def getValidCells(graph, buildingType, assignment):
```

The `assignment` parameter is never used in the function body. All three call sites pass `None`:
- `pickMRV` line 137
- `lcvOrder` line 150
- `forwardCheck` line 196

**Proposed fix:** Remove the parameter from the function signature and update the three call sites.

**Effort:** 2 min

---

### ISSUE #5 — LOW — Road Network overlay doesn't distinguish MST vs non-MST edges

**File:** `ui.py`, `_drawRoads()` and `_roadColour()`

The "Road Network" overlay renders ALL edges — white for standard cost, yellow for residential-discounted, blue for flooded. There is no visual indicator of which edges belong to the MST versus which are just grid connections. This makes the Challenge 2 result invisible on the canvas.

**Proposed fix:** If Issue #1 is addressed (MST edges restrict navigation), render non-built edges as a faint dashed grey or not at all. Otherwise, store the MST edge list on the graph/simulation and use it for selective colouring.

**Effort:** ~20 min (depends on Issue #1)

---

## What Was Verified Correct (By Code Review)

- Grid: all nodes + all 4-directional edges + correct costs (0.8 residential, 1.0 standard)
- CSP: backtracking + MRV + approximate LCV + forward checking + all 3 constraints + minimum-conflict fallback
- CSP live-mod: residential hops, powerplant hops, industrial adjacency toggle all threaded through UI > Controller > Simulation
- MST: Kruskal's with Union-Find (path compression + union by rank) — algorithm correct
- Emergency routes: Route A found, edges blocked, Route B found => guaranteed independent. Edges restored after.
- Primary Hospital/Depot: Euclidean distance to grid centre + deterministic tiebreaker
- Crime: K-Means (k=3) > synthetic formula > KNN (k=5) > riskIndex write-back. Cross-validation logged.
- Police: Top-10 highest-risk nodes, rendered as blue "P" badges
- GA: Dijkstra-based worst-case fitness, 30 pop / 60 gen, fitness cache, elitism, fixDuplicates
- A*: Manhattan heuristic (admissible), `getWeightedCost` for crime multipliers, `getAccessibleNeighbours` for floods
- Dynamic reroute: checks next cell accessibility; re-runs A* if blocked; skips unreachable civilians
- Simulation: 20-step loop, extends past 20 while civilians pending (capped at +30)
- UI: 3-column layout, sprites, 3 overlay toggles, 3 mouse tools, status bar, event log
- OOP boundary: UI > Controller > Simulation/Graph — no direct access
- Animated trees: 39-frame strip sliced at runtime, ~1-in-7 empty cells

---

## Unused Assets

Three PNG files in `assets/` are not mapped: `bush.png`, `dirt.png`, `bee_hive.png`. These could be added to `GROUND_VARIETY` in `ui.py` for extra visual variety. Not a bug.

---

## Recommended Action Priority

1. **ISSUE #2** — Risk weight shift + ambulance re-evaluation (highest viva impact)
2. **ISSUE #1** — MST edges functionally restrict navigation (spec compliance)
3. **ISSUE #3** — Fix CLAUDE.md GA parameter docs (consistency)
4. **ISSUE #4** — Remove unused `assignment` parameter (code cleanliness)
5. **ISSUE #5** — Road Network overlay MST distinction (polish)
6. Add unused ground sprites to variety pool (cosmetic)
