# Visual Strategy Execution & Geometric Tap Algorithms

Technical documentation detailing the algorithmic coordinate generation, geometric perimeter sampling, and visual state handling utilized in RaidR.

---

## Perimeter Sampling Algorithms

The visual automation engine employs several geometric models to generate spatial input coordinates relative to the detected application resolution:

### 1. Diamond Perimeter (Upper Edges)
- Used for high-value entities requiring uniform spread across the top visual perimeter.
- Samples linear interpolation intervals between the anchor points `('left', 'top')` and `('top', 'right')`.
- Clamped with edge margins (`_EDRAG_CORNER_MARGIN`) to ensure coordinate generation remains strictly on valid interactive terrain.

### 2. Full Four-Edge Distribution
- Distributes discrete tap points uniformly across all four quadrants:
  - Top-Left: `('left', 'top')`
  - Top-Right: `('top', 'right')`
  - Bottom-Right: `('right', 'bottom')`
  - Bottom-Left: `('bottom', 'left')`
- Employs coordinate bounding clamps (`y >= 50` and `y <= 0.77 * height`) to strictly prevent input events from intersecting with top window borders or bottom HUD elements.

### 3. Custom Zone Clusters (Fast 5-Point)
- Evaluates predefined anchor matrices from `deploy_zones.json`.
- Scales reference coordinates dynamically to client aspect ratio (`16:9` and `16:10`).
- Applies Gaussian position jitter (`±8px` to `±12px`) for organic coordinate dispersion.

---

## Arc & Spline Placement

For targeted radius effects, points are mapped along geometric curves:

- **Arc Sampling:** Quadratic Bezier / 3-point circular arcs sampled across left, top, and right anchors.
- **Randomized Polygon Infill:** Derives a convex hull between the upper arc and horizontal threshold, populating randomized target points via point-in-polygon ray-casting tests.

---

## Visual Verification & Recovery Loop

1. **Template Matching:** Identifies target icons using normalized cross-correlation with threshold fallbacks (0.78 down to 0.62).
2. **Selection Confirmation:** Dispatches input click to select unit slot.
3. **Sequence Execution:** Iterates through configured count parameter using discrete input taps.
4. **State Interruption Checks:** Evaluates `_reward_checkpoint()` between sequence steps to handle modal dialogues or network interruptions gracefully.
