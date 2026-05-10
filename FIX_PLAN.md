# CityMind — Implementation Fix Plan

Derived from `AUDIT_REPORT.md`. Each fix references the relevant source files and the design decisions recorded in `CLAUDE.md`. Follow the tasks in the order listed below — some fixes unlock others.

---

## Contents

1. [Fix A — CLAUDE.md GA parameter correction (quick win)](#fix-a--claudemd-ga-parameter-correction-quick-win)
2. [Fix B — Remove unused `assignment` parameter in csp.py (quick win)](#fix-b--remove-unused-assignment-parameter-in-csppy-quick-win)
3. [Fix C — MST functional edge restriction](#fix-c--mst-functional-edge-restriction)
4. [Fix D — Road Network overlay MST distinction](#fix-d--road-network-overlay-mst-distinction)
5. [Fix E — Mid-simulation risk weight shift + ambulance re-evaluation](#fix-e--mid-simulation-risk-weight-shift--ambulance-re-evaluation)
6. [Fix F — Post-fix CLAUDE.md updates](#fix-f--post-fix-claudemd-updates)

---

## Fix A — CLAUDE.md GA parameter correction (quick win)

**Source audit issue:** ISSUE #3 (Medium)

**Problem:** `CLAUDE.md` lines 353–359 still say *"Generate 50 random valid placements... 25 chromosomes... 100 generations"* but the code at `ga.py:8-12` uses `POPULATION_SIZE=30`, `NUM_GENERATIONS=60`, `NUM_PARENTS=15`. The "Setup" section at lines 340-343 is already correct — only the "How it works" narrative is stale.

**Changes needed in `CLAUDE.md`:**

Replace lines 351-359 (the "How it works" subsection under Challenge 3) with the following. The current text reads:

```
1. Generate 50 random valid placements as initial population (all 3 positions must be accessible nodes)
2. For each generation: evaluate fitness of all 50 chromosomes using Dijkstra
3. Select top 50% (25 chromosomes) as parents — elitism keeps the best solutions
4. Crossover: pair up parents and split each chromosome at a random index to produce 25 children
5. Mutate: for each child, with 10% probability replace one ambulance position with a random accessible node
6. New generation = the 25 parents + 25 children (keeps population at 50)
7. Repeat for 100 generations, keep the chromosome with the lowest fitness score
```

Replace with:

```
1. Generate 30 random valid placements as initial population (all 3 positions must be accessible nodes)
2. For each generation: evaluate fitness of all 30 chromosomes using Dijkstra
3. Select top 50% (15 chromosomes) as parents — elitism keeps the best solutions
4. Crossover: pair up parents and split each chromosome at a random index to produce 15 children
5. Mutate: for each child, with 10% probability replace one ambulance position with a random accessible node
6. New generation = the 15 parents + 15 children (keeps population at 30)
7. Repeat for 60 generations, keep the chromosome with the lowest fitness score
```

**Verification:** `grep POPULATION_SIZE ga.py`, `grep NUM_GENERATIONS ga.py`, `grep NUM_PARENTS ga.py`.

**Risk:** None. Documentation-only change.

**Assignee:** Any.

---

## Fix B — Remove unused `assignment` parameter in csp.py (quick win)

**Source audit issue:** ISSUE #4 (Low)

**Problem:** `csp.py:99` defines `def getValidCells(graph, buildingType, assignment)` but `assignment` is never referenced in the function body. All three call sites pass `None` for this parameter.

**Changes needed in `csp.py`:**

1. **Line 99:** Change the function signature:
   ```python
   # Before
   def getValidCells(graph, buildingType, assignment):
   # After
   def getValidCells(graph, buildingType):
   ```

2. **Line 137** (`pickMRV`): Change `getValidCells(graph, buildingType, None)` to `getValidCells(graph, buildingType)`.

3. **Line 150** (`lcvOrder`): Change `getValidCells(graph, buildingType, None)` to `getValidCells(graph, buildingType)`.

4. **Line 172** (inside `lcvOrder` scoring loop): Change `getValidCells(graph, otherType, None)` to `getValidCells(graph, otherType)`.

5. **Line 196** (`forwardCheck`): Change `getValidCells(graph, buildingType, None)` to `getValidCells(graph, buildingType)`.

**Verification:** Search the file for `getValidCells` — all occurrences should have 2 arguments, not 3. Run `python -c "from csp import runCSP; print('ok')"`.

**Risk:** None. Pure dead-code removal.

**Assignee:** Any.

---

## Fix C — MST functional edge restriction

**Source audit issue:** ISSUE #1 (High)

**Problem:** The graph creates ALL possible 4-directional edges during `_buildGrid()`. The MST in `mst.py` is computed but never used to restrict which edges are traversable — the `mstEdges` list is returned from `buildMST()` but immediately discarded by `buildRoadNetwork()`. This means every adjacent pair of nodes is navigable, making the Challenge 2 result cosmetic.

The CLAUDE.md (line 322) says: *"Updated cityGraph with all road edges marked as built"* — but no "built" flag exists on edges.

### Step C1 — Add `"built"` field to edge data in `cityGraph.py`

**File:** `cityGraph.py`

**Lines 84-87** (`_buildGrid` → edge creation):
```python
# Before
self.edges[key] = {
    "cost":    self._calcCost(node, neighbour),
    "blocked": False,
}

# After
self.edges[key] = {
    "cost":    self._calcCost(node, neighbour),
    "blocked": False,
    "built":   False,    # <-- new field: only true for MST + route edges
}
```

### Step C2 — Store built edges on `CityGraph` and add a setter

After line 39 in `cityGraph.py` (in `__init__`), add a storage field:
```python
# After line 39 (self.policeOfficers = [])
self.builtEdges = []         # canonical edge keys for MST + routes
```

Add a setter method in the "Setters" section (after line 147):
```python
def setBuiltEdges(self, builtEdges):
    # Mark every edge in this list as built.
    self.builtEdges = list(builtEdges)
    for nodeA, nodeB in builtEdges:
        key = edgeKey(nodeA, nodeB)
        if key in self.edges:
            self.edges[key]["built"] = True
```

### Step C3 — Add `builtOnly` parameter to neighbour getters

In the "Getters" section of `cityGraph.py`:

**`getNeighbours` (line 153):** Add an optional parameter:
```python
def getNeighbours(self, node, builtOnly=False):
    allNeighbours = list(self.adjList[node])
    if not builtOnly:
        return allNeighbours
    result = []
    for neighbour in allNeighbours:
        key = edgeKey(node, neighbour)
        if key in self.edges and self.edges[key]["built"]:
            result.append(neighbour)
    return result
```

**`getAccessibleNeighbours` (line 157):** Add the same parameter:
```python
def getAccessibleNeighbours(self, node, builtOnly=False):
    result = []
    for neighbour in self.adjList[node]:
        key         = edgeKey(node, neighbour)
        edgeBlocked = self.edges[key]["blocked"]
        nodeOk      = self.nodes[neighbour]["accessible"]
        if not builtOnly or self.edges[key]["built"]:
            if not edgeBlocked and nodeOk:
                result.append(neighbour)
    return result
```

### Step C4 — Mark MST edges as built in `mst.py`

**File:** `mst.py`

In `buildRoadNetwork()` (line 159), after building the MST and before the Route A search, store the MST edges:

```python
# After line 190 (after mstEdges = buildMST(graph))
# Also after the route edges are computed (after Route B restored)

# After line 226 (after unfloodEdge loop), before return:
# Combine MST edges + Route A edges + Route B edges into one built set
allBuiltEdges = []
allBuiltEdges.extend(mstEdges)
allBuiltEdges.extend(routeA)
allBuiltEdges.extend(routeB)
graph.setBuiltEdges(allBuiltEdges)
```

This uses `setBuiltEdges` which marks the canonical key for each edge in the graph's edge dictionary.

### Step C5 — Update callers to use `builtOnly=True` where needed

Determine which modules should be restricted to built edges:

| Module | Should use built-only? | Reason |
|--------|----------------------|--------|
| `csp.py` — `bfsHops` / `getValidCells` | No | Runs during layout before MST exists. All edges are conceptually available. |
| `mst.py` — `astarPath` for Route A/B | Yes | Routes must be on built roads only. |
| `crime.py` — `getProximityToIndustrial` | No | Runs during setup after MST. But proximity checks should work with all edges (adjacency exists regardless of MST). |
| `ga.py` — `dijkstra` / `getAccessibleNeighbours` | Yes | Ambulances and civilians should only travel on built roads. |
| `astar.py` — `findPath` | Yes | Medical team should only travel on built roads. |

**Changes:**

1. **`mst.py:64-65`** — In `astarPath`, switch from `graph.getNeighbours(current)` to `graph.getNeighbours(current, builtOnly=True)` and the same for edge-checks. Actually, the MST's A* needs to work on the concept of "built roads" excluding temporary blockades. But the MST runs before the crime module, so at that point all edges have `"built": False` except the MST + routes just set. Actually, for Route A/B routing, we need to use `builtOnly=True` to ensure they only use MST + already marked routes. But wait — the MST edges are only set AFTER the MST is built. So Route A and Route B need MST edges + their own edges. This is a circular dependency during Route B computation.

**Better approach for Step C5:** Instead of marking MST edges before Route A/B, mark them AFTER all routes are computed. But we need Route A/B to be constrained. The cleanest approach:

- Route A: run A* on the FULL graph (no built restriction — at this point only MST edges exist conceptually, but since all edges exist, just let A* find the best path). This means Route A might use non-MST edges. 
- Actually, this defeats the purpose. Let me reconsider.

**Revised approach:** The MST should be the BASE road network. Route A and Route B are emergency CORRIDORS that are ADDITIONAL to the MST. So:

1. MST edges become the base built roads.
2. Route A is a path using any edges (could include non-MST edges). After finding Route A, those edges are also marked as built.
3. Route B is found after blocking Route A edges (so it must take a different path). After finding Route B, those edges are marked as built too.

So the sequence in `buildRoadNetwork` would be:
1. `buildMST(graph)` → gets MST edges
2. Mark MST edges as built via `graph.setBuiltEdges(mstEdges)` 
3. Find Route A using `astarPath` with `builtOnly=True` (so it uses MST edges)
4. Block Route A edges, mark Route A edges as built
5. Find Route B using `astarPath` with `builtOnly=True` (so it uses MST + Route A edges, but Route A edges are temporarily blocked)
6. Unblock Route A edges

Wait, that's a problem. If Route A is found using only MST edges, and Route A edges are then marked as built, then Route B is found with builtOnly=True but Route A is blocked temporarily. So Route B must use MST edges that are not part of Route A. This correctly forces independence.

Actually, looking at the current code: `astarPath` in `mst.py` already uses `graph.isEdgeBlocked` and `graph.getEdgeCost`. It doesn't use `getAccessibleNeighbours` — it iterates `graph.getNeighbours(current)` and checks `isEdgeBlocked` manually. So we'd need to also check `"built"` for those.

Let me simplify. For `mst.py`'s `astarPath`, we need a local modification to skip non-built edges. Since `astarPath` is used only within `mst.py`, we can add the check there:

```python
# In mst.py astarPath, after line 64-66:
for neighbour in graph.getNeighbours(current):
    if graph.isEdgeBlocked(current, neighbour):
        continue
    # Add this line:
    if not graph.edges[edgeKey(current, neighbour)].get("built", False):
        continue
    # ... rest of the loop
```

But this only works if the MST edges are already marked as built. The simplest sequence:

In `buildRoadNetwork()`:
1. `mstEdges = buildMST(graph)` — compute MST
2. `graph.setBuiltEdges(mstEdges)` — mark MST edges as built
3. Find Route A using `astarPath` (which now checks `"built"`)
4. Add Route A edges to built set
5. Block Route A edges temporarily
6. Find Route B using `astarPath` (which checks `"built"`; Route A is blocked)
7. Add Route B edges to built set
8. Unblock Route A edges
9. Final built set = MST + Route A + Route B

This is clean. The `astarPath` in `mst.py` would need to access the built field. Since `astarPath` doesn't currently use the graph's edge dictionary directly, we need to add that.

Actually, looking at `astarPath` more carefully:
```python
for neighbour in graph.getNeighbours(current):
    if graph.isEdgeBlocked(current, neighbour):
        continue
    edgeCost = graph.getEdgeCost(current, neighbour)
```

We need to add: `if not graph.edges[edgeKey(current, neighbour)]["built"]: continue`

But `astarPath` doesn't import `edgeKey`. Since `edgeKey` is imported at the top of `mst.py` (line 4: `from cityGraph import edgeKey`), we can use it.

OK, let me keep the plan clean and focused on what to change.

**File changes for Step C5:**

In `mst.py`:
- In `astarPath`, add a built-check after the blocked-check (around line 65-66):
  ```python
  if not graph.edges[edgeKey(current, neighbour)].get("built", True):
      continue
  ```
  Wait, we need backward compatibility. During `buildRoadNetwork`, after we call `graph.setBuiltEdges(mstEdges)`, only MST edges have `"built": True`. But what if someone calls `astarPath` before any built edges are set? In the existing code, `astarPath` is called once BEFORE the MST is marked as built (for events/initialization). Actually no, `astarPath` is called AFTER `buildMST` in `buildRoadNetwork`. So we should set the MST as built first, then `astarPath` will have built edges to work with.

  Actually, there's a cleaner approach: The `_buildGrid` creates all edges. Instead of defaulting to `"built": False`, we can default to `"built": True` for backward compatibility. Then `setBuiltEdges` marks the subset, and the rest stay `True` too. Hmm, that doesn't help.

  Actually, let me reconsider. The simplest approach that makes the MST meaningful without breaking anything:

  - Default all edges to `"built": False`
  - In `buildRoadNetwork`, mark MST edges + Route A + Route B as built
  - `getNeighbours(builtOnly=False)` by default — backward compatible
  - Only modules that should use built-only roads opt in: `ga.py`, `astar.py`

  But `mst.py`'s `astarPath` should also use built-only to ensure routes stay on MST roads. So:

  In `mst.py:astarPath`:
  ```python
  for neighbour in graph.getNeighbours(current):
      if graph.isEdgeBlocked(current, neighbour):
          continue
      # Check built status (edge must be part of the network)
      key = edgeKey(current, neighbour)
      if not graph.edges[key].get("built", False):
          continue
      edgeCost = graph.getEdgeCost(current, neighbour)
  ```

  And in `buildRoadNetwork`, sequence:
  1. `mstEdges = buildMST(graph)`
  2. `graph.setBuiltEdges(mstEdges)` — marks all MST edges as built
  3. Find Route A via `astarPath` (which will only traverse MST edges)
  4. `graph.setBuiltEdges(mstEdges + routeA)` — add Route A
  5. Block Route A edges
  6. Find Route B via `astarPath` (only traverses MST + Route A edges, but Route A is blocked)
  7. `graph.setBuiltEdges(mstEdges + routeA + routeB)` — add Route B
  8. Unblock Route A edges

**For `astar.py`:** Change `getAccessibleNeighbours(current)` to `getAccessibleNeighbours(current, builtOnly=True)`. Actually, `getAccessibleNeighbours` doesn't have a `builtOnly` parameter yet (from Step C3). We'd add it.

**For `ga.py`:** Same change — `getAccessibleNeighbours(node, builtOnly=True)` in `dijkstra`.

### Risk assessment for Fix C

**Medium risk.** This change alters the fundamental connectivity of the graph. If any edge that A* or GA needs is not in the built set, routing will fail with "no path." This would surface as:
- Medical team unable to reach civilians (paths become empty)
- GA producing suboptimal placements

**Testing:** After the fix, run a 20-step simulation. Verify:
1. The medical team can still reach civilians (paths exist on built roads).
2. Route A and Route B are visible and coloured (orange/green).
3. The Road Network overlay shows only built roads (or distinguishes them).
4. GA places ambulances with reasonable coverage.

**Fallback:** If routing fails, check whether the MST + routes actually cover all nodes. On a 10x10 grid with a reasonable building distribution, MST + routes should connect every node. If not, the city layout may need denser building placement or the built-edge strategy needs to include all grid edges (default `"built": True`).

---

## Fix D — Road Network overlay MST distinction

**Source audit issue:** ISSUE #5 (Low)

**Problem:** The "Road Network" overlay colours ALL edges the same way (white for standard, yellow for residential, blue for flooded). There is no visual distinction between MST edges and non-MST grid connections.

**Prerequisites:** Fix C MUST be completed first — the graph needs `"built"` edge metadata so we know which edges are part of the road network.

**Changes needed in `ui.py`:**

### Step D1 — Add a colour for non-built roads

In the `COLOURS` dictionary (around line 75 in `ui.py`), add:
```python
"road_not_built": "#3a3a5a",  # faint dark grey, visible but obviously secondary
```

### Step D2 — Modify `_roadColour` method

The current `_roadColour` (line 1005) returns the colour per edge. When the "roads" overlay is active, render non-built edges differently:

```python
def _roadColour(self, graph, nodeA, nodeB, edgeData):
    if edgeData["blocked"]:
        return COLOURS["road_flooded"]

    if self._overlayMode == "roads":
        # Distinguish built vs non-built edges
        if not edgeData.get("built", True):
            return COLOURS["road_not_built"]
        typeA = graph.nodes[nodeA]["type"]
        typeB = graph.nodes[nodeB]["type"]
        if typeA == "Residential" or typeB == "Residential":
            return COLOURS["road_residential"]
        return COLOURS["road"]

    return COLOURS["road"]
```

Note: `edgeData.get("built", True)` provides backward compatibility — if the `"built"` field doesn't exist on existing edges, it defaults to `True` so older graphs render normally.

### Step D3 — Optional: reduce non-built road width

In `_drawRoads` (line 989), reduce the line width for non-built edges so they appear thinner:
```python
def _drawRoads(self):
    graph = self._controller.getGraph()
    for edge in graph.edges:
        edgeData = graph.edges[edge]
        nodeA, nodeB = edge
        colour = self._roadColour(graph, nodeA, nodeB, edgeData)
        if colour is None:
            continue
        startX, startY = self._nodeCentre(nodeA)
        endX,   endY   = self._nodeCentre(nodeB)
        # Non-built edges thinner (when road overlay is on)
        if self._overlayMode == "roads" and not edgeData.get("built", True):
            lineWidth = 1
        else:
            lineWidth = 2
        self._canvas.create_line(
            startX, startY, endX, endY, fill=colour, width=lineWidth
        )
```

---

## Fix E — Mid-simulation risk weight shift + ambulance re-evaluation

**Source audit issue:** ISSUE #2 (High)

**Problem:** The project statement (DOCX Section 4) says: *"As the simulation progresses, ambulance placements from Challenge 3 are re-evaluated as risk weights shift."* Currently `riskIndex` is set once in `crime.runCrime()` and never changes. The GA runs once and ambulances only move reactively when flooded. This is the highest-priority gap for the viva.

The CLAUDE.md (lines 81, 106, 113) explicitly flags this as an open item and documents two options. We implement **Option A** here — periodic risk-shift events + greedy ambulance reposition.

### Step E1 — Add risk shift constants to `simulation.py`

At the top of `simulation.py` (after line 13, near `MAX_EXTRA_STEPS`), add:

```python
# Risk-shift event constants. Every RISK_SHIFT_INTERVAL steps, 2-3 random
# nodes get their riskIndex bumped by +0.25 to simulate a crime wave.
# Ambulances then perform a cheap local greedy reposition in response.
RISK_SHIFT_INTERVAL = 5
RISK_SHIFT_NODE_COUNT = 3
RISK_SHIFT_AMOUNT = 0.25
```

### Step E2 — Add risk shift method to `Simulation`

Add a new method `_maybeShiftRisk()` to the `Simulation` class (around line 129, before `_tryFloodEdge`):

```python
def _maybeShiftRisk(self):
    # Every RISK_SHIFT_INTERVAL steps, bump riskIndex on a few random
    # accessible nodes to simulate a shifting crime landscape.
    # Returns an event string, or None if no shift occurred.
    if self.currentStep % RISK_SHIFT_INTERVAL != 0:
        return None

    candidates = []
    for node in self.graph.getAccessibleNodes():
        nodeType = self.graph.nodes[node]["type"]
        if nodeType != "Empty":
            candidates.append(node)

    if len(candidates) < RISK_SHIFT_NODE_COUNT:
        return None

    chosen = random.sample(candidates, RISK_SHIFT_NODE_COUNT)
    for node in chosen:
        oldRisk = self.graph.nodes[node]["riskIndex"]
        newRisk = min(oldRisk + RISK_SHIFT_AMOUNT, 3.0)
        self.graph.setRiskIndex(node, newRisk)

    return (
        f"[Step {self.currentStep}] Risk weights shifted: "
        f"{len(chosen)} nodes increased by {RISK_SHIFT_AMOUNT}. "
        f"Re-evaluating ambulance positions..."
    )
```

### Step E3 — Add greedy ambulance reposition to `Simulation`

Add a new method `_greedyAmbulanceReposition()` (after `_tryFloodEdge`):

```python
def _greedyAmbulanceReposition(self):
    # Simple local hill-climb: for each ambulance, check if swapping
    # positions with an adjacent accessible node improves coverage
    # (reduces the worst-case distance). This is a cheap alternative
    # to rerunning the full GA.
    positions = self.graph.ambulancePositions
    if len(positions) == 0:
        return []

    events = []

    for index in range(len(positions)):
        currentPos = positions[index]
        neighbours = self.graph.getAccessibleNeighbours(currentPos)

        # Compute current worst-case distance from this ambulance's
        # perspective (weighted Dijkstra)
        from ga import dijkstra
        currentDist = dijkstra(self.graph, currentPos)
        currentWorst = 0.0
        for node in self.graph.getAccessibleNodes():
            if currentDist[node] > currentWorst:
                currentWorst = currentDist[node]

        # Try each neighbour: what would the worst-case be from there?
        bestNeighbour = None
        bestWorst = currentWorst

        for neighbour in neighbours:
            testDist = dijkstra(self.graph, neighbour)
            testWorst = 0.0
            for node in self.graph.getAccessibleNodes():
                if testDist[node] > testWorst:
                    testWorst = testDist[node]
            if testWorst < bestWorst:
                bestWorst = testWorst
                bestNeighbour = neighbour

        if bestNeighbour is not None:
            positions[index] = bestNeighbour
            events.append(
                f"[Step {self.currentStep}] Ambulance at {currentPos} "
                f"repositioned to {bestNeighbour} due to risk shift."
            )

    return events
```

**Performance note:** This runs Dijkstra from the ambulance's current position and from each candidate neighbour. For 3 ambulances with up to 4 neighbours each, that is at most 3 + 12 = 15 Dijkstra runs per risk-shift event. Each Dijkstra on a 20x20 grid (~400 nodes) takes a few milliseconds, so the total is under 100ms — acceptable during a single simulation step.

### Step E4 — Call risk shift + reposition from `Simulation.step()`

In `step()` (line 93), after the flood event check (line 107) and before the medical team moves (line 110), insert:

```python
# 1a. Risk shift event (every RISK_SHIFT_INTERVAL steps)
riskEvent = self._maybeShiftRisk()
if riskEvent is not None:
    events.append(riskEvent)
    # Reposition ambulances in response
    repositionEvents = self._greedyAmbulanceReposition()
    events.extend(repositionEvents)
```

So the final step order becomes:
1. Random flood event
2. **Risk shift event + ambulance reposition** (NEW)
3. Move medical team + reroute if needed
4. Relocate flooded ambulances

### Step E5 — Thread risk shift interval through `AppController`

In `appController.py`, the `startSimulation` and `resetSimulation` methods accept a `settings` dict. If we want the risk shift interval to be configurable, add:

```python
# In startSimulation, after reading other settings:
riskShiftInterval = settings.get("riskShiftInterval", 5)
```

And pass it to `Simulation.rebuild()`. However, for the MVP fix, a hardcoded constant in `simulation.py` (Step E1) is acceptable — the risk shift is a simulation-internal behaviour, not a UI toggle.

### Risk assessment for Fix E

**Low risk.** The risk shift bumps values by a small amount (+0.25, capped at 3.0 max). The greedy reposition only moves an ambulance if the neighbour provides strictly better coverage. Edge cases:
- **No accessible neighbours:** Ambulance stays put (safe).
- **All nodes already at max risk:** `min(oldRisk + 0.25, 3.0)` caps it, so no error.
- **Risk shift on step 5, 10, 15, 20:** The modulo check `currentStep % 5 == 0` fires at the right intervals.

### Viva defence for Fix E

When asked about "ambulance placements re-evaluated as risk weights shift" (CLAUDE.md line 367), you can now say: *"Every 5 steps, the simulation injects a local crime wave that bumps riskIndex on 2-3 nodes. Ambulances then perform a local greedy reposition — each one checks its neighbours to see if moving there would improve worst-case response time. This is a two-tier approach: the GA gives the optimal static placement, and the greedy hill-climb handles mid-simulation disruptions. The GA itself is not rerun because it is computationally expensive (30 chromosomes × 60 generations × 400 nodes), but the greedy step is cheap and demonstrates a second strategy."*

---

## Fix F — Post-fix CLAUDE.md updates

After all other fixes are implemented, update `CLAUDE.md` to reflect the changes:

### F1 — Mark risk shift as done

In the "Remaining / To Improve" section (line 81), change:
```
- [ ] **Risk weights shift mid-simulation** ...
```
to:
```
- [x] **Risk weights shift mid-simulation** — every 5 steps during the 20-step loop, 2-3 nodes get their riskIndex bumped by +0.25. A greedy local hill-climb repositions ambulances in response.
```

Similarly, update the "Still open" section (line 106):
```
- [x] **Risk weights never shift mid-simulation.** Implemented via `_maybeShiftRisk` + `_greedyAmbulanceReposition` in `simulation.py`. Every 5 steps, 2-3 non-empty nodes get riskIndex +0.25, and ambulances perform a local neighbour-swap evaluation.
```

### F2 — Add built-edge design decision

In the "Key Design Decisions" section (after line 591, "Why remove the full Route A path"), add:

```
**Why restrict navigation to MST + route edges only?**
The project says "determine which roads should be built." Allowing the medical team and ambulances to traverse every adjacent pair would make the MST irrelevant. By marking only MST + Route A + Route B edges as built, and configuring the A* and GA modules to ignore non-built edges, the road network decision is functionally enforced. Non-built edges remain visible on the overlay as faint dark lines so the user can see the full grid, but routing only respects the built subset.
```

### F3 — Update Implementation Status for `cityGraph.py` and `mst.py`

In the "Implementation Status" section:

**For `cityGraph.py`** (line 624): Add to the bullet list:
```
- Edges now carry a `"built"` boolean, set `False` by default and marked `True` for MST + route edges by `setBuiltEdges()`.
- `getNeighbours` and `getAccessibleNeighbours` accept an optional `builtOnly` parameter.
```

**For `mst.py`** (line 638): Update:
```
- `buildRoadNetwork` now marks MST + Route A + Route B edges as built on the graph via `graph.setBuiltEdges()`, so downstream modules only traverse the constructed road network.
```

---

## Implementation Order (Recommended)

| Order | Fix | File(s) | Effort | Dependencies |
|-------|-----|---------|--------|-------------|
| 1 | Fix A — CLAUDE.md GA params | `CLAUDE.md` | 2 min | None |
| 2 | Fix B — Unused parameter | `csp.py` | 2 min | None |
| 3 | Fix C — MST edge restriction | `cityGraph.py`, `mst.py`, `astar.py`, `ga.py` | 30 min | None |
| 4 | Fix D — Road overlay MST distinction | `ui.py` | 15 min | Fix C |
| 5 | Fix E — Risk shift mid-simulation | `simulation.py` | 1-2 hours | Fix C (optional, can be done independently) |
| 6 | Fix F — Post-fix CLAUDE.md updates | `CLAUDE.md` | 5 min | All of the above |

**Recommended pipeline:**
- **Before the viva (must-have):** Do Fixes A, B, C, and E. These address the functional gaps that an instructor is most likely to probe.
- **If time permits:** Fixes D and F for polish and documentation consistency.

---

## Rollback Strategy

If any fix introduces a regression, revert the affected file with git:

```bash
git checkout -- cityGraph.py     # revert MST built-edge changes
git checkout -- simulation.py    # revert risk-shift changes
git checkout -- CLAUDE.md       # revert doc changes
```

Test the simulation after each fix before moving to the next one:
1. `python main.py` (application launches, no import errors)
2. Click "Generate City" (CSP runs, MST builds, crime runs, GA places, A* initialises)
3. Click "Step" several times (simulation progresses, events log)
4. Toggle overlays (Road Network, Coverage, Crime Risk render correctly)
5. Test Flood tool (select two adjacent cells, road turns blue)
6. Test Emergency tool (click a cell, civilian added, red "!" marker appears)
