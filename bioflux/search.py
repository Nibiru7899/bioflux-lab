"""Budgeted online discovery. Selection receives only acquired outcomes."""
import json
import time

import numpy as np
import pandas as pd
from sklearn.ensemble import ExtraTreesRegressor
from sklearn.linear_model import BayesianRidge

from bioflux.dataset import load_dataset
from bioflux.simulator import Simulator, clean_flux
from bioflux.storage import ROOT, read_json, sha256, write_json


def choose_next(method, features, observed_indices, observed_scores, remaining,
                rng, genes, priors=None, prior_std=None):
    """No full label vector is accepted by this acquisition boundary."""
    if method == 'random':
        return int(rng.choice(remaining))
    if method == 'greedy':
        incumbent = observed_indices[int(np.argmax(observed_scores))]
        current = set(genes[incumbent])
        distances = np.array([len(current.symmetric_difference(genes[i])) for i in remaining])
        nearest = remaining[distances == distances.min()]
        return int(rng.choice(nearest))
    if method == 'tree':
        model = ExtraTreesRegressor(n_estimators=32, min_samples_leaf=2,
                                   random_state=int(rng.integers(2 ** 31)), n_jobs=1)
        model.fit(features[observed_indices], observed_scores)
        estimates = np.array([tree.predict(features[remaining]) for tree in model.estimators_])
        acquisition = estimates.mean(0) + estimates.std(0)
    elif method == 'gnn':
        # Frozen graph surrogate plus an online Bayesian residual correction.
        # The ensemble supplies a prior; only purchased labels update the residual model.
        residual = BayesianRidge()
        calibration_features = np.column_stack([features[:, :3], priors, prior_std])
        residual.fit(calibration_features[observed_indices],
                     np.array(observed_scores) - priors[observed_indices])
        correction, uncertainty = residual.predict(calibration_features[remaining], return_std=True)
        acquisition = priors[remaining] + correction + np.sqrt(uncertainty ** 2 + prior_std[remaining] ** 2)
    else:
        raise ValueError(f'Unknown search method: {method}')
    # Seeded tie-breaking avoids privileging alphabetical intervention order.
    tied = remaining[np.isclose(acquisition, acquisition.max(), rtol=1e-8, atol=1e-10)]
    return int(rng.choice(tied))


def discover(config, name='e_coli_core', budget=None):
    frame, x, _, manifest = load_dataset(name)
    if config['growth_fraction'] != manifest['design']['growth_fraction']:
        raise ValueError('Search growth fraction differs from the frozen dataset design.')
    directory = ROOT / 'runs' / name / 'search'
    directory.mkdir(parents=True, exist_ok=True)
    training_dir = ROOT / 'runs' / name / 'training'
    if not read_json(training_dir / 'manifest.json').get('complete'):
        raise ValueError('Complete surrogate training before running discovery.')
    predictions = pd.read_csv(training_dir / 'predictions.csv')
    priors_frame = predictions[(predictions.panel == 'environment') & (predictions.model == 'gnn')]
    priors_frame = priors_frame.set_index('scenario_id').loc[frame.scenario_id]
    if not {'predicted_feasible_utility', 'feasible_utility_std'} <= set(priors_frame.columns):
        raise ValueError('Predictions need joint feasible-utility moments; rerun training or refresh cached utility predictions.')
    priors = priors_frame.predicted_feasible_utility.to_numpy()
    prior_std = priors_frame.feasible_utility_std.to_numpy()
    simulator = Simulator(manifest.get('model_id', 'iML1515' if name.startswith('iML1515') else 'e_coli_core'), config['growth_fraction'])
    if simulator.model_sha256 != manifest['design']['model_sha256']:
        raise ValueError('The current model differs from the frozen dataset model.')
    training_manifest = read_json(training_dir / 'environment_split.json')
    # Validation labels were purchased for early stopping, so charge them too.
    upstream_ids = set(training_manifest['train'] + training_manifest['validation'])
    upstream = frame[frame.scenario_id.isin(upstream_ids)]
    upstream_calls = int(upstream.solver_calls.sum())
    upstream_seconds = float(upstream.elapsed_seconds.sum())
    network_metadata = read_json(training_dir / 'networks.json')['environment_gnn']
    upstream_seconds += sum(member['training_seconds'] + member['inference_seconds']
                            + member.get('utility_refresh_inference_seconds', 0)
                            for member in network_metadata)
    curves, verifications = [], []
    eligible = (frame.environment_split == 'test') & (frame.status != 'wildtype_no_growth')
    for environment in sorted(frame.loc[eligible, 'environment_id'].unique()):
        local = frame[frame.environment_id == environment].reset_index()
        global_indices = local['index'].to_numpy()
        features = x[global_indices]
        genes = [list(g) for g in local.genes]
        local_prior, local_std = priors[global_indices], prior_std[global_indices]
        for seed in config['search_seeds']:
            initial_rng = np.random.default_rng(seed)
            count = min(config['search_initial'], config['search_budget'], len(local))
            if count < 1:
                raise ValueError('Search requires a positive initial-observation and evaluation budget.')
            control = int(local.index[local.intervention_id == 'WT'][0])
            rest = np.setdiff1d(np.arange(len(local)), [control])
            initial = [control] + initial_rng.choice(rest, count - 1, replace=False).tolist()
            for method in ['random', 'greedy', 'tree', 'gnn']:
                if budget:
                    budget.check()
                rng = np.random.default_rng(seed)
                selected, scores = [], []
                online_calls, best, failed = 0, 0.0, 0
                wildtype_minimum = None
                simulator.baselines.clear()  # Equal per-run environment setup costs.
                started = time.perf_counter()
                for step in range(min(config['search_budget'], len(local))):
                    if budget:
                        budget.check()
                    if step < count:
                        candidate = initial[step]
                    else:
                        remaining = np.setdiff1d(np.arange(len(local)), selected)
                        candidate = choose_next(method, features, selected, scores, remaining,
                                                rng, genes, local_prior, local_std)
                    row = local.iloc[candidate]
                    outcome = simulator.simulate(row.glucose, row.oxygen, row.genes, ranges=True)
                    online_calls += outcome['solver_calls']
                    score = float(outcome['product_min'] or 0) if outcome['feasible'] else 0.0
                    if step == 0:
                        if not outcome['feasible']:
                            raise RuntimeError('The unmodified control could not be verified; discovery cannot assess gain.')
                        wildtype_minimum = score
                    failed += not outcome['feasible']
                    best = max(best, score)
                    selected.append(candidate)
                    scores.append(score)
                    verifications.append(dict(environment=environment, seed=seed, method=method,
                                              step=step + 1, scenario_id=row.scenario_id, **outcome))
                    curves.append(dict(environment=environment, seed=seed, method=method,
                         evaluations=step + 1, online_solver_calls=online_calls,
                         upstream_solver_calls=upstream_calls if method == 'gnn' else 0,
                         total_solver_calls=online_calls + (upstream_calls if method == 'gnn' else 0),
                         best_verified_minimum=best, infeasible_recommendations=failed,
                         wildtype_minimum=wildtype_minimum,
                         best_gain_over_wildtype=clean_flux(best - wildtype_minimum),
                         online_seconds=time.perf_counter() - started))
                print(f'{name}/{environment}/{seed}/{method}: best minimum={best:.5f}, '
                      f'{online_calls} online LP solves', flush=True)
                pd.DataFrame(curves).to_csv(directory / 'curves.csv', index=False)
                with (directory / 'verifications.jsonl').open('w', encoding='utf-8') as output:
                    for result in verifications:
                        output.write(json.dumps(result, allow_nan=False) + '\n')
    table = pd.DataFrame(curves)
    # Full outcomes enter only this post-hoc evaluation, after acquisition is finished.
    reference = frame.assign(score=np.where(frame.feasible,
                   pd.to_numeric(frame.product_min, errors='coerce').fillna(0), 0))
    reference.loc[reference.score < 1e-7, 'score'] = 0.0
    best_by_env = reference.groupby('environment_id').score.max()
    table['pool_best_minimum'] = table.environment.map(best_by_env)
    table['simple_regret'] = (table.pool_best_minimum - table.best_verified_minimum).clip(lower=0)
    table.loc[table.simple_regret < 1e-7, 'simple_regret'] = 0.0
    table['pool_best_gain'] = (table.pool_best_minimum - table.wildtype_minimum).map(clean_flux)
    table['accounted_seconds'] = table.online_seconds + np.where(table.method == 'gnn', upstream_seconds, 0)
    table.to_csv(directory / 'curves.csv', index=False)
    final = table[table.evaluations == table.evaluations.max()]
    summary = final.groupby('method').agg(
        mean_best=('best_verified_minimum', 'mean'), std_best=('best_verified_minimum', 'std'),
        mean_best_gain=('best_gain_over_wildtype', 'mean'),
        mean_online_calls=('online_solver_calls', 'mean'),
        mean_total_calls=('total_solver_calls', 'mean'), mean_seconds=('online_seconds', 'mean'),
        mean_infeasible=('infeasible_recommendations', 'mean'),
        mean_regret=('simple_regret', 'mean'),
        mean_accounted_seconds=('accounted_seconds', 'mean')).reset_index()
    summary.to_csv(directory / 'summary.csv', index=False)
    environment_summary = final.groupby(['environment', 'method']).agg(
        mean_best=('best_verified_minimum', 'mean'), std_best=('best_verified_minimum', 'std'),
        mean_best_gain=('best_gain_over_wildtype', 'mean'),
        baseline_minimum=('wildtype_minimum', 'mean'), pool_best_gain=('pool_best_gain', 'max'),
        pool_best=('pool_best_minimum', 'max'), mean_regret=('simple_regret', 'mean')).reset_index()
    environment_summary.to_csv(directory / 'environment_summary.csv', index=False)
    write_json(directory / 'manifest.json', dict(config=config, complete=True,
        acquisition='minimum secretion under fixed wildtype growth floor; UCB coefficient 1',
        gnn_update='Frozen pretrained ensemble with Bayesian residual correction on acquired labels',
        utility_moments='Mean and standard deviation of per-member minimum-secretion times feasibility probability',
        comparison='Equal online candidate budgets, unequal explicitly charged upstream training costs',
        initial_design='Unmodified control first, plus seven seeded random candidates; all eight count in the budget',
        source_predictions_sha256=sha256(training_dir / 'predictions.csv'),
        offline_evaluation_dataset_calls=manifest['label_solver_calls'],
        upstream_gnn_solver_calls=upstream_calls,
        timing_scope='Accounted seconds sum label solves, neural training loops, prior inference and online search. '
                     'They exclude data loading, graph construction and checkpoint loading; CLI execution histories '
                     'record measured command elapsed time separately.',
        note='Full held-out outcomes were used only for post-hoc evaluation, never acquisition. '
             'Search re-solves selected candidates; these calls are additional to dataset generation.'))
    return directory
