# Delivery scope and evidence

This is a computational research prototype. The original proposal allowed changes to the plan; the implementation choices and limits below define the delivered scope.

| Requirement | Implementation and evidence | Limit |
| --- | --- | --- |
| Biochemical simulator | `bioflux/simulator.py`; core and iML1515; real gene-rule deletion semantics, nutrient bounds, fixed growth floor, growth and secretion ranges | FBA assumptions, not living-organism validation |
| Trustworthy labels | 6,000 core and 10,000 genome scenarios; model/source hashes, solver status and LP accounting in `data/`; independent HiGHS/GLPK cross-checks under both run directories | Cross-checks share the same reconstruction |
| Graph learning | Stoichiometric bipartite message-passing ensemble implemented directly in PyTorch; three members per panel, safe checkpoints | One MPNN architecture, not an exhaustive GCN/GAT comparison; no PyTorch Geometric dependency needed |
| Competitive prediction baselines | Dummy, ridge/logistic, histogram gradient boosting and MLP; ten metric rows per model across two held-out panels | Histogram boosting replaces XGBoost; predictive outcomes are mixed |
| Generalization | Frozen environment and effective intervention-profile combination splits | Many gene deletions have identical constraint effects; productive core combination test cases are absent |
| Uncertainty-guided discovery | Ensemble joint feasible-utility moments and Bayesian residual updates; random, local greedy and online ExtraTrees/UCB baselines | Ensemble disagreement is uncalibrated; no exact OptKnock implementation or optimality claim |
| Fair verification | Five seeds, four held-out environments, four methods, 40 charged observations each; 3,200 fresh verifications per reconstruction | Pretraining has additional labeling and compute costs; accounted component timing is not complete end-to-end time |
| Interactive laboratory | Local Streamlit app: metabolic graph, environment/deletions, predictions, solver verification and 15-point growth–production curve | Interactive graph uses the core model; genome experiments are available through CLI and reports |
| Resource control | Cooperative disk/time budgets and measured expansion/training gates; genome training executed on an 8 GB RTX 4060 | Limits are cooperative; downloads/installation are outside active experiment timing |
| Reproducibility and trust | Pinned dependencies, safetensors, non-pickle arrays, model/download manifests, immutable execution histories, source manifest and artifact audits | Hashes identify files; they do not independently certify scientific correctness |
| Research interpretation | `PRIOR_ART.md`, `METHODOLOGY.md` and per-model `report/FINDINGS.md` | No experimental fitness dataset, wet-lab validation, publication novelty or GNN discovery superiority demonstrated |

Deletion constraints cannot improve a maximum under otherwise identical constraints. Discovery therefore targets increased **minimum** succinate secretion while retaining the same environment-specific growth floor. Maximum secretion remains a separate potential-production prediction.

The archived v1 search incorrectly combined marginal ensemble quantities for utility uncertainty. The final implementation uses each member's feasibility-weighted utility before computing ensemble moments. Fixed weights and marginal predictive metrics were preserved; derived utility predictions and both search experiments were rerun. The archive is diagnostic evidence, not the final benchmark. Additional development reruns are outside the final experiment's reported costs.
