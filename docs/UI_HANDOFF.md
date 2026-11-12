# React interface

The primary interface is React 19 + TypeScript, built with Vite. FastAPI serves the built UI and API together at http://127.0.0.1:8000. The simulator, checkpoint inference, training data and benchmark results are the existing Python implementation. The redesign does not retrain models or change scientific constraints.

## Run

```powershell
# Run from the project root after the interface has been built.
.\start-lab.ps1
```

For a fresh install, install the pinned Python environment from the README, then use Node.js 22.12 or later:

```powershell
cd frontend
npm ci
npm run build
cd ..
.\start-lab.ps1
```

For frontend development, start the API on port 8000 and run `npm run dev` inside `frontend`. Vite proxies `/api` to that local service. The server binds only to 127.0.0.1. The previous Streamlit app remains optional on port 8501.

## Interface and evidence

- The metabolic canvas uses the actual core model's 167 nodes and reaction–metabolite connections. Drag, zoom, focus the succinate neighborhood, or inspect a node with the keyboard-accessible selector. Positions are visual layout; moving or highlighted edges do not represent measured flux.
- Experiment controls retain the original discrete nutrient capacities and two-gene limit. Gene rules determine disabled reactions through the same simulator. Changing a scenario clears results and rejects late responses from older requests.
- Predictions use the existing hash-checked three-member GNN checkpoints. Verification and the fifteen-point trade-off curve use fresh GLPK solves. Infeasible production values remain missing.
- Research views read audited core/iML1515 metrics and search curves. The cost view includes upstream GNN LP calls. Numeric tables remain available beside graphical summaries. Null and negative results are preserved.
- Motion is tied to interaction: button feedback, connection emphasis, result state changes and chart entry. Reduced-motion preferences remove spatial movement. There is no perpetual ornamental network movement.
- The cell artwork is generated conceptual imagery, explicitly labeled. Its exact generation prompt is embedded and retained in a sidecar. Manrope is self-hosted from the official Google Fonts repository with source hashes and OFL license. No image/font request is sent to an external service at runtime.

`npm run build` passes TypeScript checking. The chart bundle is loaded on demand; Vite reports a size advisory for the 544 kB minified chart chunk (about 185 kB gzip), which is separate from the initial UI bundle.

The regression suite passed 37 tests, including API validation, solver request isolation, graph/artifact identity and missing labels on failed envelope solves. Browser verification exercised real prediction, verification, trade-off calculation, stale-result clearing, infeasible deletion, research model switching and the pretraining-cost axis. Desktop and 390px mobile checks found no document horizontal overflow. Screenshots and the independent visual review are under `.impeccable/review/react/`.

Known platform scope: a local research prototype, one core-model interactive lab, and both reconstructions in the offline research view. No new biological validation or discovery advantage is implied by the redesign.
