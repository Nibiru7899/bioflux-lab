# BioFlux implementation checkpoint

Final verification completed on 28 October 2026 (Asia/Kolkata). Both experiments, corrected discovery reruns, reports and artifact audits are complete. The 28-test CUDA-environment suite passed. See the final checkpoint below and `docs/HANDOFF.md`. Earlier sections are retained as historical implementation checkpoints; their active-process and remaining-work descriptions are superseded by the final checkpoint.

## Completed and verified

- Data-only core and iML1515 models downloaded from official BiGG HTTPS endpoints; original responses and normalized JSON both have hashes. Model identities/counts are in `data/models/*.manifest.json`.
- The fixed-growth-floor simulator, GPR evaluation, production min/max, status/call accounting, feature generation, grouped splits, five predictive approaches, ensemble inference, budgeted search and report commands are implemented.
- Core: 6,000 scenarios; 16,098 generation LP calls; 5,162 feasible; five positive minimum-secretion scenarios. One environment (`g2_o0`) cannot support unmodified growth and is excluded from learning/search.
- Core full training, ten model/panel evaluations, eight neural checkpoints, 3,200 freshly solved search candidates and findings/figures are complete. `runs/e_coli_core/audit.json` passed.
- Core has 250 raw gene interventions but 62 distinct effective reaction-disable profiles. Equivalent profiles stay in one combination split. The combination test has no positive forced-secretion case; claims are explicitly limited.
- Current core discovery protocol first charges the unmodified control, then seven shared random observations. In its one informative held-out environment, tree search found the productive pair in 2/5 seeds; random, greedy and GNN found it in 0/5. An earlier all-random initial-design run had different counts; it is superseded. Upstream GNN LP and prior-inference costs are charged separately.
- Independent HiGHS/GLPK numerical cross-check passed on five representative core cases. This is not biological validation.
- Full test suite passed: 25 tests in the normal installed CPU environment, including checksum/configuration-drift guards, the 15-point trade-off action and stale-curve clearing. The installed `bioflux` entrypoint and simulation command work. Final GPU-environment tests still need running after installation.
- Browser prediction/verification worked. Desktop/mobile screenshots are in `.impeccable/review/`. Skill finish reviewer marked the sole contrast fix resolved/ship at that scope. DESIGN.md and `.impeccable/design.json` were written and inspected. Detector ran once and returned no findings.
- Genome pilot: 200 mixed single/double-deletion scenarios, 551 LP calls, approximately 13.9 seconds of simulation. Recorded expansion gate accepted.
- Genome dataset: 10,000 scenarios, 25,091 generation LP calls, 7,742 feasible; generation has finished. It has 1,683 positive minimum-secretion scenarios but **no sampled deletion improves over its unmodified control**. GPU training is now running; environment-panel dummy/ridge/tree/MLP and the first two GNN members have finished. GNN members: 22 epochs/140.5 seconds and 42 epochs/280.7 seconds. First member peak allocated CUDA memory: 552,055,296 bytes.
- Timing now includes prior inference in accounted components, with measured CLI elapsed time preserved separately in unique `executions/` histories. New histories also record source hashes. Report gains subtract a charged WT control; plot bands show descriptive SD rather than inferential standard errors.
- Corrected an earlier unverified CC0 license label. The actual BiGG educational/research/nonprofit permission and required copyright paragraphs are retained in `docs/third_party/BIGG_NOTICE.txt`, copied to data/models, and hashed in both model manifests. Model contents/hashes did not change.
- Independent GLPK/HiGHS checks now pass for both reconstructions. The core-derived b0115+b0767 pair does not improve over WT in the checked genome environment; b2779 is viable in the genome reconstruction despite being lethal in the core reconstruction. Keep claims model-specific.
- The full-graph training resource benchmark is now shipped in `bioflux.expansion.benchmark_training`, used by `expand` and by the current GPU waiting helper. Its measured CPU projection (using actual split sizes) is about 13.1 hours, still above the 5.5-hour genome cap. The earlier coarser CPU estimate was 24.5 hours.

## Active processes at this checkpoint

These tool session IDs are observations from this chat, not proof of future liveness. Poll the same session before deciding that work stopped; never restart solely on observation timeout.

- `9794`: CUDA installation succeeded and is terminal. `.venv` now contains official PyTorch 2.11.0+cu128. `runs/torch-cuda-install.json` records the vendor URL/hash; pip check passed. The completed `.tmp/pip-cache` was safely removed after installer exit; project disk use fell from 8.4 to 5.55 GiB.
- `86740`: current live `.tmp/complete_genome.ps1` pipeline. CUDA smoke test and the full-graph gate passed; training is running. It will continue train → evaluate → report → artifact audit. Transcript: `runs/iML1515/pipeline.log`. It is the sole genome writer. Revalidate this handle before deciding training stopped.
- `65447`: local Streamlit server on 127.0.0.1:8501, currently launched with the temporary CPU runtime on PYTHONPATH. It should be restarted against the final installed CUDA environment after installation/cleanup, if needed.

The initial CUDA installer `27020` returned a dependency DNS/network failure after its wheel transfer, and initial waiting job `35305` timed out. Both are terminal. A later waiting job `79826` was deliberately stopped before training so its replacement could include the full-graph GPU gate. Do not revive any of these old jobs.

The core was intentionally trained on CPU using official PyTorch 2.11.0+cpu under `.tmp/cpu_runtime`. The normal `.venv` has since been upgraded to CUDA; no PYTHONPATH override is needed for normal commands. The old Streamlit server still uses the temporary CPU runtime, so do not remove that directory before stopping/restarting it. CPU resource gates failed; the actual GPU gate passed with 0.01283 seconds/backward step, a 7,370.8-second conservative projection (including margin/reserve), and 508,067,328 peak allocated CUDA bytes on the 8,585,216,000-byte RTX 4060. New GPU member metadata records actual device, torch build and peak CUDA memory. Do not confuse the original core CPU training with current genome GPU execution.

## Remaining work

1. Revalidate/poll the original CUDA installer and queued genome pipeline. Correct actual failures surgically; do not start duplicate writers.
2. Inspect genome metrics, search verification logs, findings, plots and artifact audit. Preserve negative/null outcomes. Assess actual GPU memory and timings.
3. Run the final complete suite in `.venv` after CUDA installation, plus artifact audits for both datasets. Install the local CLI entrypoint without fetching new dependencies and test its help/commands.
4. Refresh `requirements.lock.txt` after all packages are installed (torch installed separately from its official vendor index). Add final source/file provenance and a concise handoff linking the real findings.
5. Safely remove only superseded installation scratch/cache and the temporary CPU runtime after no live server uses it; verify resolved cleanup targets stay inside this workspace. Keep models, datasets, checkpoints, evidence and run logs.
6. Verify the objective requirement by requirement before calling the goal complete. Do not mark complete while the genome pipeline or final audit remains unverified.

## Important implementation notes

- Original maximum-potential discovery was corrected: deletion constraints cannot increase the maximum under an unchanged growth requirement. Primary discovery utility is minimum feasible secretion at 10% of environment-specific WT growth. Product maximum remains a separate prediction/display task.
- `bioflux.cli study` supports the core and gated expansion with a shared cooperative six-hour budget. The current execution uses separately observed stages; downloads/installation precede compute accounting.
- `scripts/verify_artifacts.py` checks data identity, split leakage including effective profiles, scientific invariants, checkpoint hashes and search accounting. Mutable execution status, environment snapshots and active `.log` transcripts are excluded from static report artifact hashes.
- Windows atomic JSON replacement has a bounded retry for observed transient file-watcher locks. Disk measurements tolerate disappearing installer temporary files.
- The workspace began empty and is not a Git repository. No unrelated source, hosted service, credentials, system driver or wet-lab work was changed.

## Final checkpoint — 28 October 2026, 10:55 IST

- Genome pipeline session 86740 completed successfully. All eight neural checkpoints, ten predictive metric rows, reports and independent solver cross-checks are present for each reconstruction. Genome training used CUDA; the core's original training used CPU. Actual genome CUDA allocation stayed below 8 GB.
- Final acquisition audit exposed an incorrect combination of marginal ensemble quantities. Archived v1 source/predictions/search/reports under `runs/archive/v1_unweighted_uncertainty/` with a hash manifest. Corrected utility moments to compute each member's minimum-secretion prediction times its feasibility probability before ensemble mean/std; added two regression tests. No labels or weights were retrained or changed.
- Refreshed derived utility predictions from fixed checkpoints and charged additional inference time. Independently checked that all sixteen checkpoint hashes and both marginal metric CSV hashes match the archived metadata/files.
- Corrected evaluation/report/audit session 69067 completed with exit 0. Each model has 3,200 fresh search verifications. Core tree succeeds in 2/5 seeds in its sole informative held-out environment; other methods in 0/5. Genome has no sampled intervention gain. No GNN superiority is claimed.
- Regenerated the final core report after explanatory text changes. Both artifact audits passed again at 05:23 UTC. Both discovery plots and the genome production-range plot were visually inspected; null outcomes are retained.
- Final normal-environment full suite: **28 passed**, two third-party SWIG deprecation warnings, 12.95 seconds. `pip check`: no broken requirements.
- Old server session 65447 is terminal. Verified no Python process used the temporary CPU runtime; removed only that resolved project-local directory. The completed pip cache had already been removed after installation. Models, labels, checkpoints, execution histories and diagnostic archives remain.
- Final local server session 68472 runs normal `.venv` on 127.0.0.1:8501. Browser verification showed actual trained GNN predictions and successful GLPK verification. Evidence: `.impeccable/review/final-verified.png`. The lab tab is marked as a deliverable.
- `docs/COMPLETION_AUDIT.md` records proposal coverage and substitutions/limits; `docs/HANDOFF.md` provides startup and findings. Source manifest generation and independent hash verification are the final delivery step.

## React redesign — 28 October 2026

The user requested a substantial UI redesign with imagery, motion and improved graphs, delegated taste, then explicitly requested a framework other than Streamlit. The primary interface is now React 19/TypeScript/Vite with a small local FastAPI service. The existing simulator, datasets, checkpoints and research results remain the source of truth. Legacy Streamlit source is retained; its old server session 68472 has stopped. Current React/API server session 28601 serves localhost port 8000.

- Implemented native nutrient/gene controls, actual SVG model topology with pan/zoom, succinate neighborhood and keyboard-accessible node inspection, prediction/solver result states, comparison, JSON export and the fifteen-point trade-off plot.
- Added core/genome research views with actual audited metrics, interactive cost/quality plots, MAE bars, numeric tables and findings downloads. Negative results remain explicit.
- Created a conceptual bacterial-cell raster through imagegen; embedded the exact prompt and retained its sidecar. Self-hosted Manrope and OFL license from official Google Fonts. All npm package resolved URLs are on registry.npmjs.org; FastAPI came from PyPI. No runtime external image/font service is needed.
- Motion uses short result transitions, button feedback, connection emphasis and chart rendering, with reduced-motion alternatives. Scientific topology does not masquerade as moving measured flux.
- React production build and TypeScript check pass. Chart code is lazy-loaded; Vite retains an advisory for its 544 kB minified chunk (about 185 kB gzip).
- Complete Python suite: **37 passed**, 9.06 seconds; warnings are third-party SWIG and Starlette/httpx deprecations. Nine new API cases cover rejected inputs, request isolation, graph/evidence identity and missing production labels for failed solves. `pip check` passes.
- Real browser actions verified trained inference, GLPK verification, envelope calculation, stale clearing, infeasible b2779, research reconstruction switching and pretraining LP cost display. 390px mobile drawer and desktop checks found no document horizontal overflow. Valid viewport captures/continuations are under `.impeccable/review/react/` (full-page capture unavailable in this browser).
- Impeccable detector ran once: no findings. Raster scan: one image, zero missing provenance. The old design-system font warning is handled by updating the system to the chosen self-hosted Manrope, without rule suppression.
- Fresh finish reviewer accepted the direction and requested four text-contrast fixes. Changed them to measured 5.24:1 and 5.13:1 combinations; reviewer scored all four resolved and returned `ship` at the fix-list scope. Final documenter updates the current design tokens.
- Both scientific artifact audits passed again after adding the UI. No experiment retraining or benchmark search rerun occurred. `start-lab.ps1`, README and `docs/UI_HANDOFF.md` document the new startup workflow. Source manifest is regenerated after documentation.
- Final documentation validation: the documenter wrote current token-bearing DESIGN.md and `.impeccable/design.json` before its usage-limit interruption. Parent completed validation in-thread: YAML/JSON parsing, canonical section order, supported component properties, resolved token references and actual React source match. All twelve pre-existing scientific module hashes match the previous delivery. Local API liveness check returned HTTP 200. The review and its scoped verdict are preserved in `.impeccable/review/react/REVIEW.md`.
