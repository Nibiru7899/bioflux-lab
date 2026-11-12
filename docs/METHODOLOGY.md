# Experimental contract

## Model and environment

Only the downloaded, manifested E. coli core or iML1515 reconstruction defines the network. The biomass objective is read from the model; succinate exchange is `EX_succ_e`. The reference medium is copied, carbon-containing exchange uptake is closed, and glucose/oxygen uptake capacities are set explicitly. Succinate import is prohibited. Salt/water uptake, maintenance and source reaction bounds otherwise remain intact.

For environment e, solve unmodified maximum growth μWT(e). If it is not positive above 1e-7, retain the exclusion reason but do not use that environment in training or discovery. Every intervention is tested against the same requirement μ ≥ 0.1 μWT(e). This floor is not recomputed from the mutant.

An intervention is a set of zero, one or two gene identifiers. COBRApy evaluates the actual AND/OR gene–protein–reaction rule. An isozyme deletion does not automatically disable the whole reaction. Source model changes occur inside reversible contexts.

## Labels and numerical semantics

Solve maximum growth, then maximum and minimum succinate secretion under the growth requirement. Record the exact number of attempted LP optimizations, statuses, elapsed wall time and mass-balance residual at maximum production. Failed optimizations remain explicit; production labels for an infeasible scenario are missing. Missing labels never become regression targets. Flux values below 1e-7 are treated as numerical zero.

The two production endpoints bound a feasible flux set. Maximum production is potential. Minimum production is forced secretion **under these mathematical constraints**. Neither is a measurement of a real microorganism. Basic FBA lacks regulation, kinetics and adaptation.

Proof of objective choice: if a knockout adds constraints to feasible set F, then FKO is a subset of F. Therefore max(FKO, product) ≤ max(F, product), while min(FKO, product) ≥ min(F, product) whenever FKO is nonempty. Seeking improvements in maximum potential under an unchanged growth requirement would be a mathematically invalid discovery target. The primary search utility is minimum feasible secretion; a non-viable candidate has zero utility.

## Partitions and features

Environment partitioning is deterministic by environment identity, with 16/4/4 nominal train/validation/test environments before viability exclusions. Combination partitioning holds out novel effective reaction-disable profiles from sampled double deletions. Biochemically identical profiles share a partition across all environments and gene identifiers. Profiles already represented by baseline/single deletions remain in training. These are separate evaluation panels, not a claim of simultaneous environment-and-combination extrapolation.

Features are glucose capacity, oxygen capacity, deletion count, gene-deletion indicators and the reaction mask derived from GPR evaluation. No solved flux, objective value, feasibility result, reference growth or test statistic is an input. GNN reaction/metabolite identities and stoichiometry are static within one reconstruction. Learned identity embeddings make this a transductive model, not cross-model transfer.

The MPNN uses separate substrate/product stoichiometric channels, two rounds of bipartite message passing, global pooling and pooling over disabled reactions. The ensemble comprises three independently seeded members. The MLP uses the same pre-solve tabular features as ridge/tree baselines. Scales are fitted from observed training labels. Neural early stopping uses validation labels, never test labels. Three continuous heads predict growth, potential maximum and forced minimum; a fourth predicts feasibility. Independent heads may violate physical ordering; solver verification remains necessary.

## Discovery and accounting

All search methods share a candidate pool and eight initial candidates for each seed/environment: the unmodified control first, followed by seven seeded random candidates. Each receives up to forty candidate evaluations, including that control and the other initial observations. Every selected candidate is re-solved, even if it already exists in the offline dataset. Report gain over the verified unmodified minimum as well as absolute secretion; positive baseline secretion is not an intervention improvement. Selection is not permitted to read the unselected labels. Full offline labels enter only post-hoc regret/reference calculations.

- Random: uniform sampling without replacement.
- Greedy: choose an untested candidate closest in gene-set symmetric-difference distance to the best observed candidate, using seeded tie-breaking. This is a local heuristic, not an exact optimizer.
- Tree: refit ExtraTrees using only acquired utility labels; choose predicted mean plus tree disagreement.
- GNN: each frozen member predicts feasible utility as its minimum secretion multiplied by its feasibility probability. Aggregate mean and standard deviation of that same per-member utility, then refit a Bayesian residual model on acquired outcomes and choose its upper-confidence acquisition. This preserves production/feasibility dependence within members and assigns no utility disagreement when all members predict certain infeasibility. It is online calibration of a pretrained model, not full online GNN retraining.

Report candidate evaluations, online LP calls, upstream LP calls, total LP calls and online wall time. Accounted time adds label solves, neural training loops, prior inference and online search; it excludes data/graph/checkpoint loading and is not a direct end-to-end wall measurement. Immutable CLI execution histories record measured command elapsed time separately. GNN upstream charges include training labels and validation labels used for stopping. Random/greedy/tree have no pretrained-label charges. Offline benchmark construction is an additional separately recorded cost. Equal online evaluations do not establish equal total computational cost. Uncertainty is a heuristic acquisition signal, not calibrated coverage.

Report simple regret against the fully labeled sampled pool. This reference is not a free search algorithm or a globally optimal strain design. Seeds share environments and models; repeated runs are not independent biological experiments. Constant-outcome ranking statistics are undefined, and rare positive outcomes restrict conclusions.

## Scope of validation

Simulator agreement and conservation are computational checks. Held-out labels test surrogate approximation within the stated scenario design. No experimental mutant-fitness dataset, wet-lab validation, clinical application or biological performance claim is included. Focused prior-art review prevents broad novelty claims; a publication-ready novelty assessment and exact bilevel baseline remain future work.
