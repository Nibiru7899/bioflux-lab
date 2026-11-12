# BioFlux Lab handoff

The local simulator, dataset generation, baseline/graph training, budgeted discovery, reports and React/TypeScript interactive laboratory are implemented. Open http://127.0.0.1:8000 while the local API server runs. Restart from PowerShell with:

```powershell
.\start-lab.ps1
```

The virtual lab uses E. coli core. Both core and genome-scale iML1515 have completed offline experiments: 6,000 and 10,000 scenarios, respectively; five predictive approaches; two generalization panels; eight neural checkpoints per reconstruction; and 3,200 freshly solver-verified search observations each. Genome neural models trained on the RTX 4060 using official CUDA PyTorch, with measured memory below the available 8 GB.

The final CUDA-environment test suite passed **37 tests**. Both `runs/<model>/audit.json` files passed. Independent GLPK/HiGHS agreement checks passed five cases per reconstruction. `pip check` found no broken requirements. The final app's trained inference and solver verification were also checked in the browser; `.impeccable/review/react/desktop.png` records that view.

The results do not establish a GNN discovery advantage. In the core's one informative held-out environment, tree search found improvement in 2/5 seeds; random, greedy and GNN found none. No sampled genome-scale deletion improves over its unmodified control. Prediction results vary by endpoint and panel. These are model-specific simulation results, with no biological validation or novelty claim.

Read `runs/e_coli_core/report/FINDINGS.md` and `runs/iML1515/report/FINDINGS.md` for the actual metrics, costs, caveats and figures. `COMPLETION_AUDIT.md` maps the proposal to the delivered scope; `METHODOLOGY.md` explains constraints, splits and accounting. `SOURCE_MANIFEST.json` hashes delivered source and references twelve experiment manifests/audits.

Only official package registries/vendor sources and official BiGG model endpoints were used. The publisher notice is retained. The temporary CPU runtime and completed pip cache were removed; datasets, checkpoints, diagnostic archives and logs are preserved. The earlier acquisition calculation is archived explicitly as a diagnostic; both final searches use corrected joint feasible-utility ensemble moments. All sixteen checkpoint hashes and both marginal predictive metric files were preserved across that correction.
