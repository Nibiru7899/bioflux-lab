"""Independent environment and intervention generalization panels."""
import time

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.dummy import DummyClassifier, DummyRegressor
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import accuracy_score, brier_score_loss, mean_absolute_error, r2_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from bioflux.dataset import load_dataset
from bioflux.simulator import Simulator
from bioflux.storage import ROOT, sha256, write_json

TARGETS = ['growth', 'product_max', 'product_min']


def feasible_utility_moments(member_predictions):
    members = np.asarray(member_predictions)
    utility = members[:, :, 2] * members[:, :, 3]
    return utility.mean(axis=0), utility.std(axis=0)


def targets(frame):
    y = np.zeros((len(frame), 4), np.float32)
    observed = np.ones_like(y)
    for j, column in enumerate(TARGETS):
        values = pd.to_numeric(frame[column], errors='coerce').to_numpy(dtype=float)
        observed[:, j] = np.isfinite(values)
        y[:, j] = np.nan_to_num(values)
        y[np.abs(y[:, j]) < 1e-7, j] = 0
    y[:, 3] = frame.feasible.to_numpy(dtype=float)
    valid = frame.status.isin(['optimal', 'below_growth_requirement', 'infeasible']).to_numpy()
    return y, observed, valid


def fit_tabular(kind, x, y, observed, indices, seed):
    models = []
    for j in range(4):
        idx = indices[observed[indices, j] > 0]
        if not len(idx):
            raise ValueError(f'No observed training labels for target {j}')
        if j == 3:
            if kind == 'dummy' or len(np.unique(y[idx, j])) == 1:
                model = DummyClassifier(strategy='prior')
            elif kind == 'ridge':
                model = make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000, random_state=seed))
            else:
                model = HistGradientBoostingClassifier(max_iter=100, max_leaf_nodes=15,
                          l2_regularization=1, random_state=seed, early_stopping=False)
        elif kind == 'dummy':
            model = DummyRegressor(strategy='mean')
        elif kind == 'ridge':
            model = make_pipeline(StandardScaler(), Ridge(alpha=10))
        else:
            model = HistGradientBoostingRegressor(max_iter=100, max_leaf_nodes=15,
                      l2_regularization=1, random_state=seed, early_stopping=False)
        model.fit(x[idx], y[idx, j])
        models.append(model)
    return models


def predict_tabular(models, x):
    columns = [np.maximum(0, m.predict(x)) for m in models[:3]]
    classes = list(models[3].classes_)
    probability = models[3].predict_proba(x)
    columns.append(probability[:, classes.index(1)] if 1 in classes else np.zeros(len(x)))
    return np.column_stack(columns)


def metrics(frame, y, observed, prediction, indices):
    result = {}
    for j, name in enumerate(TARGETS):
        selected = indices[observed[indices, j] > 0]
        if len(selected):
            result[name + '_mae'] = float(mean_absolute_error(y[selected, j], prediction[selected, j]))
            result[name + '_r2'] = (float(r2_score(y[selected, j], prediction[selected, j]))
                                   if len(selected) > 1 and np.ptp(y[selected, j]) > 1e-7 else None)
        else:
            result[name + '_mae'] = result[name + '_r2'] = None
    result['feasibility_accuracy'] = float(accuracy_score(y[indices, 3], prediction[indices, 3] >= 0.5))
    result['feasibility_brier'] = float(brier_score_loss(y[indices, 3], prediction[indices, 3]))
    scores = y[:, 2] * y[:, 3]
    predicted_scores = prediction[:, 2] * prediction[:, 3]
    correlations, regrets = [], []
    for env in frame.iloc[indices].environment_id.unique():
        selected = indices[frame.iloc[indices].environment_id.to_numpy() == env]
        if np.ptp(scores[selected]) > 1e-8 and np.ptp(predicted_scores[selected]) > 1e-8:
            correlations.append(float(spearmanr(scores[selected], predicted_scores[selected]).statistic))
        choice = selected[np.argmax(predicted_scores[selected])]
        regrets.append(float(scores[selected].max() - scores[choice]))
    result.update(mean_environment_spearman=float(np.mean(correlations)) if correlations else None,
                  mean_top1_regret=float(np.mean(regrets)), test_scenarios=len(indices),
                  positive_minimum_test_scenarios=int((scores[indices] > 1e-7).sum()))
    return result


def train(config, name='e_coli_core', budget=None):
    frame, x, masks, manifest = load_dataset(name)
    if config['growth_fraction'] != manifest['design']['growth_fraction']:
        raise ValueError('Training growth fraction differs from the frozen dataset design.')
    y, observed, valid = targets(frame)
    model_id = manifest.get('model_id', 'iML1515' if name.startswith('iML1515') else 'e_coli_core')
    simulator = Simulator(model_id, config['growth_fraction'])
    if simulator.model_sha256 != manifest['design']['model_sha256']:
        raise ValueError('The current model differs from the frozen dataset model.')
    directory = ROOT / 'runs' / name / 'training'
    directory.mkdir(parents=True, exist_ok=True)
    write_json(directory / 'manifest.json', dict(complete=False, config=config))
    all_metrics, predictions, network_meta = [], [], {}
    for panel in ['environment', 'combination']:
        split = frame[panel + '_split'].to_numpy()
        indices = {part: np.flatnonzero(valid & (split == part)) for part in ['train', 'validation', 'test']}
        if any(len(v) == 0 for v in indices.values()):
            continue
        print(f'Training {name}/{panel}: ' + str({k: len(v) for k, v in indices.items()}), flush=True)
        write_json(directory / f'{panel}_split.json', {k: frame.iloc[v].scenario_id.tolist() for k, v in indices.items()})
        for kind in ['dummy', 'ridge', 'tree', 'mlp', 'gnn']:
            if budget:
                budget.check()
            started = time.perf_counter()
            member_predictions, metadata = [], []
            if kind in ['dummy', 'ridge', 'tree']:
                fitted = fit_tabular(kind, x, y, observed, indices['train'], config['seed'])
                fit_seconds = time.perf_counter() - started
                inference_start = time.perf_counter()
                prediction = predict_tabular(fitted, x)
                inference_seconds = time.perf_counter() - inference_start
            else:
                from bioflux.neural import predict_network, train_network
                for member in range(config['ensemble_members'] if kind == 'gnn' else 1):
                    checkpoint = directory / f'{panel}_{kind}_{member}.safetensors'
                    network, meta = train_network(kind, x, masks, y, observed,
                        indices['train'], indices['validation'], simulator.stoich, config,
                        config['seed'] + member, checkpoint, budget)
                    inference_start = time.perf_counter()
                    member_predictions.append(predict_network(network, x, masks, meta['scales']))
                    meta['inference_seconds'] = time.perf_counter() - inference_start
                    meta['checkpoint_sha256'] = sha256(checkpoint)
                    metadata.append(meta)
                    print(f'{panel}/{kind} member {member}: {meta["epochs"]} epochs, '
                          f'{meta["training_seconds"]:.1f}s on {meta["device"]}', flush=True)
                prediction = np.mean(member_predictions, axis=0)
                fit_seconds = sum(m['training_seconds'] for m in metadata)
                inference_seconds = sum(m['inference_seconds'] for m in metadata)
                network_meta[f'{panel}_{kind}'] = metadata
            uncertainty = (np.std(np.array(member_predictions)[:, :, 2], axis=0)
                           if len(member_predictions) > 1 else np.zeros(len(frame)))
            utility_mean, utility_std = feasible_utility_moments(member_predictions or [prediction])
            result = dict(panel=panel, model=kind, training_seconds=fit_seconds,
                          inference_seconds=inference_seconds,
                          **metrics(frame, y, observed, prediction, indices['test']))
            all_metrics.append(result)
            out = frame[['scenario_id', 'environment_id', panel + '_split']].copy()
            out.columns = ['scenario_id', 'environment_id', 'split']
            out['panel'], out['model'] = panel, kind
            for j, column in enumerate(TARGETS + ['feasibility_probability']):
                out['predicted_' + column] = prediction[:, j]
            out['product_min_std'] = uncertainty
            out['predicted_feasible_utility'] = utility_mean
            out['feasible_utility_std'] = utility_std
            predictions.append(out)
            pd.DataFrame(all_metrics).to_csv(directory / 'metrics.csv', index=False)
            pd.concat(predictions).to_csv(directory / 'predictions.csv', index=False)
            write_json(directory / 'networks.json', network_meta)
            print(f'{panel}/{kind}: minimum-production MAE={result["product_min_mae"]:.4f}', flush=True)
    write_json(directory / 'manifest.json', dict(config=config, dataset_manifest=manifest,
               complete=True, metrics_sha256=sha256(directory / 'metrics.csv'),
               predictions_sha256=sha256(directory / 'predictions.csv'),
               target_order=TARGETS + ['feasibility_probability']))
    return directory
