# BioFlux Lab

A local computational research prototype for uncertainty-guided, solver-verified metabolic intervention discovery. Python 3.12; Windows; an 8 GB GPU is optional. No paid API or cloud service.

## Start

From PowerShell in this directory:

```powershell
.\start-lab.ps1
```

The React/TypeScript lab opens at http://127.0.0.1:8000. Choose glucose, oxygen and up to two gene deletions. Predict with the graph ensemble, verify with GLPK, and calculate a growth–production curve. Research results reads the actual core and genome experiment artifacts. A small local FastAPI service calls the existing scientific implementation.

For a fresh checkout, install the Python dependencies described below, then build the interface once with Node.js 22.12+:

```powershell
cd frontend
npm ci
npm run build
cd ..
.\start-lab.ps1
```

For frontend development, run the API on port 8000 and `npm run dev` from `frontend/`; Vite proxies local API requests. No hosted service is required. The previous Streamlit interface remains available through `.venv\Scripts\python.exe -m streamlit run app.py` on port 8501.

The interactive graph uses E. coli core metabolism. Genome-scale iML1515 experiments use the same CLI pipeline and produce separate research reports under `runs/iML1515/`.

## Reproduce the experiment

```powershell
.\.venv\Scripts\python.exe -m bioflux.cli all
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe scripts/crosscheck_solver.py
.\.venv\Scripts\python.exe scripts/crosscheck_solver.py iML1515
```

Individual stages:

```powershell
.\.venv\Scripts\python.exe -m bioflux.cli download
.\.venv\Scripts\python.exe -m bioflux.cli generate
.\.venv\Scripts\python.exe -m bioflux.cli train
.\.venv\Scripts\python.exe -m bioflux.cli evaluate
.\.venv\Scripts\python.exe -m bioflux.cli report
.\.venv\Scripts\python.exe -m bioflux.cli simulate --glucose 10 --oxygen 20 --genes b1779
```

`--config configs/default.json` precedes the stage name. `generate --limit N --name NAME` creates a separate design. Existing dataset designs cannot silently change; generation resumes from its flushed journal. Training and search restart their stage when explicitly re-run. Do not run two writers for the same dataset at once.

For a fresh environment, create `.venv`, set `TEMP` and `TMP` to a writable project-local `.tmp` directory if necessary, install the pinned `requirements.lock.txt` from official PyPI, and install the pinned CUDA PyTorch wheel from `https://download.pytorch.org/whl/cu128` (or the official CPU wheel repository on machines without CUDA). The local module commands work without editable installation.

The vendor pins are in `requirements-torch-cpu.txt` and `requirements-torch-cuda.txt`; choose one. Install the ordinary dependencies first, then use `python -m pip install --no-deps -r requirements-torch-cpu.txt` (or its CUDA counterpart). An editable `python -m pip install --no-deps --no-build-isolation --no-index -e .` also installs the `bioflux` console command without another download.

## What the experiment measures

- Twenty-four nutrient environments; up to 6,000 baseline/single/double-gene-deletion scenarios for the core model.
- A fixed viability floor: 10% of unmodified maximum growth in the **same** environment. Source salts, maintenance and exchange capacity semantics are retained, other carbon uptake is closed.
- Maximum growth, maximum succinate potential, minimum feasible succinate secretion and feasibility.
- Dummy, ridge/logistic, histogram gradient boosting, MLP and a three-member bipartite message-passing GNN ensemble.
- Independent held-out environment and held-out gene-combination panels; no feature uses solved fluxes or label-derived quantities. Biochemically equivalent reaction-disable masks stay together in the combination split; effects already represented by unmodified/single-deletion scenarios remain in training.
- Five-seed discovery runs with random, local greedy, online tree and pretrained GNN/Bayesian residual search. Every candidate selected for discovery is solved again. The unmodified control is the first of eight charged initial observations; gains subtract its verified secretion minimum.

**Scientific correction to the original proposal:** deletions cannot increase the maximum of the same linear objective under the same fixed constraints. They only remove feasible solutions. Discovery therefore maximizes the **minimum feasible secretion**, with infeasible candidates assigned zero discovery utility. Maximum potential is still reported as a separate prediction task. Neither endpoint is a claim about what a living organism will secrete.

The GNN prior is pretrained; its online update is Bayesian residual correction, not full GNN retraining at every iteration. Ensemble disagreement is not calibrated uncertainty. Comparisons report both equal online evaluation counts and unequal end-to-end costs, including the GNN's training/early-stopping labels. Dataset construction is additional benchmark infrastructure and is separately counted. A zero-outcome design space is reported as a null result, never as evidence of effective discovery.

Timing tables distinguish measured online search time from accounted components (label solves, training loops, prior inference and online search). Data/graph/checkpoint loading is excluded from that sum. Unique records under each run's `executions/` preserve measured CLI command elapsed time without overwriting earlier invocations.

## Files and evidence

- `data/models/`: data-only metabolic models and source/checksum manifests.
- `data/e_coli_core/`: immutable design, frozen splits, raw solve journal, CSV and feature arrays.
- `runs/e_coli_core/training/`: held-out metrics, predictions, safetensors neural checkpoints and training histories.
- `runs/e_coli_core/search/`: complete candidate verification journal, curves, cost accounting and summaries.
- `runs/e_coli_core/report/FINDINGS.md`: findings, standalone scientific figures and artifact hashes.
- `docs/PRIOR_ART.md`: focused primary-source positioning, without a novelty claim.
- `SOURCE_MANIFEST.json`: delivery source hashes and references to experiment manifests; regenerate with `scripts/manifest_sources.py` after final verification.

Arrays load with `allow_pickle=False`; neural checkpoints use safetensors. No downloaded pickle/joblib checkpoints or dataset code is executed. Download URLs use TLS with certificate validation and an explicit host allowlist; redirects are checked before following. Model manifests identify source and SHA-256; a checksum records identity, not a guarantee of trust.

BiGG's publisher notice is retained in `docs/third_party/BIGG_NOTICE.txt` and copied alongside downloaded models. The verified source grants educational, research and nonprofit-use permission with notice retention; it is not labeled as a CC0 release. See the [publisher's terms](https://bigg.ucsd.edu/about) for the exact conditions.

## Resource and interpretation limits

Default active compute cap is six hours; project disk cap is 10 GB. Long stages check limits between batches/scenarios and preserve completed files. Each LP has a 30-second timeout; a single in-progress solve can delay a budget stop. These caps are cooperative, not OS-level quotas. Downloads and initial dependency installation precede experiment compute accounting.

Genome expansion first runs a 200-scenario iML1515 pilot. The recorded gate uses its runtime and available resources to decide whether to generate a separate dataset of at most 10,000 scenarios. Core checkpoints do not transfer directly to a differently sized graph.

```powershell
.\.venv\Scripts\python.exe -m bioflux.cli download --model iML1515
.\.venv\Scripts\python.exe -m bioflux.cli expand
.\.venv\Scripts\python.exe scripts/verify_artifacts.py
```

The expansion command requires a completed core report and records its decision in `runs/iML1515/expansion_gate.json`. It uses batch size 16 on the larger graph and sparse message propagation. Pilot and expanded datasets are distinct artifacts.

Expansion has two measured gates: pilot-based dataset generation, then full-graph training/inference benchmarking on the available device. If the full ensemble projection exceeds the remaining budget, the generated dataset is retained and training is explicitly declined rather than silently reducing the experiment.

`python -m bioflux.cli study` runs both models in sequence with one shared six-hour compute budget, subject to the recorded genome expansion gate. `all` runs only the selected model's complete workflow.

No wet-lab validation, strain construction, cross-species generalization or publication novelty is claimed. Exact OptKnock/bilevel optimization is not included. See the findings report for observed limitations rather than assuming ML outperforms GLPK.
