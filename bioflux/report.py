"""Generate an evidence-led report and standalone scientific figures."""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from bioflux.dataset import load_dataset
from bioflux.storage import ROOT, read_json, sha256, utc_now, write_json


def markdown_table(frame):
    columns = list(frame.columns)
    lines = ['| ' + ' | '.join(columns) + ' |', '| ' + ' | '.join(['---'] * len(columns)) + ' |']
    for row in frame.itertuples(index=False, name=None):
        values = [f'{value:.4g}' if isinstance(value, float) else str(value) for value in row]
        lines.append('| ' + ' | '.join(values) + ' |')
    return '\n'.join(lines)


def report(name='e_coli_core'):
    frame, _, masks, dataset_manifest = load_dataset(name)
    unique_effects = len({np.packbits(mask.astype(bool)).tobytes() for mask in masks})
    directory = ROOT / 'runs' / name
    report_dir = directory / 'report'
    report_dir.mkdir(parents=True, exist_ok=True)
    metrics = pd.read_csv(directory / 'training' / 'metrics.csv')
    curves = pd.read_csv(directory / 'search' / 'curves.csv')
    summary = pd.read_csv(directory / 'search' / 'summary.csv')
    environment_summary = pd.read_csv(directory / 'search' / 'environment_summary.csv')
    informative = environment_summary[environment_summary.pool_best_gain > 1e-7]
    diagnostic_note = ('The archived v1 run used inconsistent marginal utility moments and is retained '
                       'only as a diagnostic.' if (ROOT / 'runs/archive/v1_unweighted_uncertainty').exists() else '')
    colors = dict(random='#687f92', greedy='#b37d24', tree='#387ead', gnn='#16645f')
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5), constrained_layout=True)
    for method, values in curves.groupby('method'):
        grouped = values.groupby('evaluations').best_gain_over_wildtype.agg(['mean', 'std', 'count'])
        error = grouped['std'].fillna(0)
        axes[0].plot(grouped.index, grouped['mean'], label=method, color=colors[method])
        axes[0].fill_between(grouped.index, grouped['mean'] - error, grouped['mean'] + error,
                             alpha=0.12, color=colors[method])
        representative = values.groupby('evaluations').agg(
            calls=('total_solver_calls', 'mean'), score=('best_gain_over_wildtype', 'mean'))
        axes[1].plot(representative.calls, representative.score, label=method, color=colors[method])
    axes[0].set(xlabel='Online candidate evaluations', ylabel='Gain over control, mmol/gDW/hour',
                title='Equal online budgets; shaded ±1 SD across runs')
    axes[1].set(xlabel='LP solves including upstream GNN labels',
                ylabel='Gain over control, mmol/gDW/hour', title='Upstream training cost is charged')
    axes[1].set_xscale('log')
    for ax in axes:
        ax.spines[['top', 'right']].set_visible(False)
        ax.legend(frameon=False)
    fig.savefig(report_dir / 'discovery.png', dpi=180)
    plt.close(fig)
    wt_minima = frame[frame.intervention_id == 'WT'].set_index('environment_id').product_min
    frame['wildtype_minimum'] = frame.environment_id.map(wt_minima)
    frame['gain_over_wildtype'] = (frame.product_min - frame.wildtype_minimum).clip(lower=0)
    frame.loc[frame.gain_over_wildtype < 1e-7, 'gain_over_wildtype'] = 0.0
    feasible = frame[frame.feasible]
    fig, ax = plt.subplots(figsize=(7, 4.5), constrained_layout=True)
    ax.scatter(feasible.product_max, feasible.product_min, s=8, alpha=0.3, color='#16645f')
    ax.set(xlabel='Maximum secretion, mmol/gDW/hour', ylabel='Minimum secretion, mmol/gDW/hour',
           title='Potential production versus forced production')
    ax.spines[['top', 'right']].set_visible(False)
    fig.savefig(report_dir / 'production_ranges.png', dpi=180)
    plt.close(fig)
    best = feasible.sort_values(['gain_over_wildtype', 'product_min', 'growth'], ascending=False).head(10)
    best = best.assign(evidence_source='full_offline_labeled_pool')
    best[['scenario_id', 'environment_split', 'combination_split', 'glucose', 'oxygen', 'growth',
          'product_min', 'product_max', 'wildtype_minimum', 'gain_over_wildtype', 'evidence_source']].to_csv(
        report_dir / 'leading_candidates.csv', index=False)
    null = not (feasible.gain_over_wildtype > 1e-7).any()
    crosscheck_path = directory / 'solver_crosscheck.json'
    crosscheck_note = ('An independent SciPy/HiGHS cross-check agreed with GLPK within 1e-5 '
                       'on five representative cases in this reconstruction, including a core-derived pair, '
                       'gene deletions and an excluded environment. This checks numerical '
                       'agreement using the same reconstruction, not biological validity.'
                       if crosscheck_path.exists() and read_json(crosscheck_path)['passed']
                       else 'No independent numerical solver cross-check is recorded.')
    finding = ('No sampled deletion improved minimum succinate secretion over its unmodified control. '
               'Any positive baseline secretion is not an intervention gain; these curves cannot establish useful intervention discovery.'
               if null else 'Some sampled deletions increased forced secretion over the unmodified control. '
               'Compare the recorded search results and total LP costs before interpreting an advantage.')
    gnn_result = summary[summary.method == 'gnn'].iloc[0]
    conventional = summary[summary.method != 'gnn'].sort_values('mean_best', ascending=False).iloc[0]
    if gnn_result.mean_best + 1e-7 < conventional.mean_best:
        finding += (f' At the equal online budget, {conventional.method} search achieved a higher mean '
                    f'best verified minimum ({conventional.mean_best:.6g}) than GNN search '
                    f'({gnn_result.mean_best:.6g}). This run does not support GNN superiority.')
    elif abs(gnn_result.mean_best - conventional.mean_best) < 1e-7:
        finding += ' GNN search tied the best conventional result at the online budget; no quality advantage was demonstrated.'
    else:
        finding += (' GNN search achieved a higher observed mean at the online budget; '
                    'that is not evidence of an end-to-end advantage without the upstream cost comparison.')
    report_text = f'''# BioFlux Lab findings: {name}

Generated {utc_now()}. These are computational model results, not experimentally validated biology.

## Main finding

{finding}

Deletion constraints cannot increase maximum production over the unmodified model under identical nutrient and growth constraints. The search therefore ranks **minimum feasible secretion**, while retaining a fixed floor of 10% of each environment's unmodified maximum growth. Maximum secretion remains a potential, not a guaranteed biological outcome. A positive minimum is a mathematical property of this model and these constraints.

## Dataset and provenance

- Model SHA-256: `{dataset_manifest['design']['model_sha256']}`.
- Scenarios: {len(frame)}; feasible: {int(frame.feasible.sum())}.
- Distinct GPR-derived intervention-effect profiles: {unique_effects}. Raw gene-intervention scenarios are not independent constraint systems; many share the same effective reaction mask.
- Scenarios with minimum secretion above 1e-7: {int((feasible.product_min > 1e-7).sum())}. Smaller numerical residuals are treated as zero in learning and discovery.
- Scenarios improving minimum secretion over the unmodified control by more than 1e-7: {int((feasible.gain_over_wildtype > 1e-7).sum())}.
- Dataset LP solves: {dataset_manifest['label_solver_calls']}. Search re-verification is additional.
- Environments: glucose/oxygen grid, source medium salts and maintenance retained; other carbon uptake closed.
- Solver: GLPK through COBRApy; feasibility tolerance 1e-7; timeout 30 seconds per optimization.
- Frozen environment and combination splits; preprocessing and early stopping use training/validation data only.
- In the combination panel, equivalent GPR-derived reaction-disable profiles stay in one partition. Effects already represented by baseline/single deletions remain in training. There are {int((frame.combination_split == 'test').sum())} raw held-out combination scenarios, of which {int(((frame.combination_split == 'test') & (frame.product_min > 1e-7)).sum())} have positive minimum secretion. This limits conclusions about discovering unseen productive combinations.
- Flux units: mmol/gDW/hour; biomass flux is conventionally 1/hour. Uptake values are positive capacity limits, translated to exchange bounds by COBRApy.

{crosscheck_note}

## Held-out predictive results

Here `tree` denotes histogram gradient boosting, `ridge` pairs ridge regression with logistic feasibility classification, and `gnn` is the three-member bipartite MPNN ensemble. The discovery `tree` strategy below is a separate online ExtraTrees/UCB baseline.

{markdown_table(metrics[['panel', 'model', 'growth_mae', 'product_max_mae', 'product_min_mae', 'feasibility_accuracy', 'mean_top1_regret', 'training_seconds', 'inference_seconds']])}

Regression errors use only observed labels. Infeasible production labels are missing, not fabricated zero targets. Search utility is defined as zero for an infeasible candidate. Ranking correlation is undefined when all outcomes tie.

## Budgeted discovery

{markdown_table(summary)}

Only {informative.environment.nunique()} held-out environment(s) in this sampled pool contain any improvement over the unmodified control. Results for those informative environments:

{markdown_table(informative)}

All methods first verify the unmodified control and then the same seven seeded random candidates; all eight count in the online budget. Reported gains subtract that verified control, not a free reference label. Random, greedy and tree search start without upstream labels. GNN search uses a pretrained ensemble and updates a Bayesian residual model with acquired outcomes. Its training **and early-stopping validation** LP costs are included in total costs. Equal online budgets do not imply equal end-to-end budgets. The full offline benchmark dataset is evaluation infrastructure, separately charged in the manifests. Five seeds crossed with four held-out environments are not twenty independent biological experiments.

`accounted_seconds` sums recorded label-solve, training-loop, prior-inference and online-search time. It excludes data loading, graph/checkpoint loading and preprocessing outside those timers, including the simulator's preliminary GPR validation. Measured CLI execution elapsed times are recorded separately in `executions/`; these component sums are not presented as direct end-to-end wall measurements.

Lower online LP counts can reflect early rejection of infeasible candidates. Interpret them alongside infeasible-recommendation counts and verified gain, rather than treating fewer LPs alone as improved discovery.

The pretrained GNN and cold-start online tree have different upstream information. This search comparison measures those complete strategies; the predictive panels use matched training labels to compare representation quality. The GNN prior's mean and disagreement are computed from each member's minimum secretion multiplied by its feasibility probability before aggregation.

Costs describe the defined final experiment. Development diagnostics and superseded protocol reruns are additional. {diagnostic_note}

![Discovery curves](discovery.png)

![Production ranges](production_ranges.png)

## Limits and interpretation

- No claim of novelty, wet-lab validation, calibrated uncertainty or production readiness.
- Uncertainty is ensemble disagreement plus Bayesian residual uncertainty, not a confidence guarantee.
- Models are transductive within one metabolic reconstruction; this does not prove cross-organism or cross-model transfer.
- The greedy baseline is local mutation search; it is not OptKnock or an exact strain-design algorithm.
- Sampled single/double deletions do not exhaust the intervention space. No GNN superiority is assumed.
- FBA omits regulation, kinetics and adaptation; environmental generalization is measured only on the specified grid.
- Timing is local wall time for the named components, with exclusions stated above, and is not a hardware-independent benchmark.

## Reproduction

See the root README and `configs/default.json`. Raw scenarios, feature arrays, model manifests, safe neural checkpoints, training histories, predictions and search verification journals are retained locally.

`leading_candidates.csv` ranks the full offline labeled pool, including training scenarios. It is an oracle reference, not a list credited to any search method; row-level split and evidence-source fields make that distinction explicit.
'''
    (report_dir / 'FINDINGS.md').write_text(report_text, encoding='utf-8')
    artifacts = {str(p.relative_to(ROOT)): sha256(p) for p in directory.rglob('*')
                 if p.is_file() and p.suffix != '.log'
                 and p.name not in {'artifact_manifest.json', 'execution.json', 'audit.json', 'environment.json'}}
    write_json(report_dir / 'artifact_manifest.json', dict(created_at=utc_now(), files=artifacts))
    return report_dir
