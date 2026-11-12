"""Audit actual study artifacts, including scientific invariants and model identity."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
import pandas as pd

from bioflux.dataset import load_dataset
from bioflux.storage import ROOT, read_json, sha256, write_json, utc_now


def audit(name):
    frame, x, masks, manifest = load_dataset(name)
    failures = []

    def check(condition, message):
        if not condition:
            failures.append(message)

    check(frame.scenario_id.is_unique, 'Duplicate scenario identities')
    check(np.isfinite(x).all(), 'Non-finite predictive features')
    check(frame.model_sha256.nunique() == 1, 'Mixed model identities')
    check(frame.model_sha256.iloc[0] == manifest['design']['model_sha256'], 'Dataset model identity mismatch')
    model_id = manifest.get('model_id', name)
    source = read_json(ROOT / 'data/models' / f'{model_id}.manifest.json')
    check(sha256(ROOT / 'data/models' / f'{model_id}.json') == source['sha256'], 'Normalized source model checksum mismatch')
    if source.get('source_sha256'):
        check(sha256(ROOT / 'data/models' / f'{model_id}.source.json') == source['source_sha256'], 'Original model response checksum mismatch')
    check(sha256(ROOT / source['license_notice']) == source['license_notice_sha256'], 'Publisher usage notice checksum mismatch')
    feasible = frame[frame.feasible]
    check((feasible.product_min <= feasible.product_max + 1e-6).all(), 'Invalid production range')
    check((feasible.growth + 1e-6 >= feasible.growth_requirement).all(), 'Growth floor violated')
    check((feasible.mass_balance_residual < 1e-5).all(), 'Mass balance residual failed')
    check(frame.loc[~frame.feasible, 'product_min'].isna().all(), 'Infeasible minimum labels are fabricated')
    check(frame.groupby('environment_id').environment_split.nunique().max() == 1, 'Environment split leakage')
    check(frame.groupby('intervention_id').combination_split.nunique().max() == 1, 'Combination split leakage')
    profiles = pd.DataFrame(dict(profile=[np.packbits(mask.astype(bool)).tobytes().hex() for mask in masks],
                                 split=frame.combination_split))
    check(profiles.groupby('profile').split.nunique().max() == 1, 'Equivalent reaction-mask split leakage')
    profiles['environment'] = frame.environment_id
    profiles['minimum'] = frame.product_min
    for _, group in profiles.groupby(['profile', 'environment']):
        observed = group.minimum.dropna()
        check(len(observed) == 0 or observed.max() - observed.min() < 1e-6,
              'Equivalent intervention effects disagree beyond solver tolerance')
    wt = frame[frame.intervention_id == 'WT'].set_index('environment_id')
    for _, group in feasible.groupby('environment_id'):
        control = wt.loc[group.environment_id.iloc[0]]
        maximum = control.product_max
        check((group.product_max <= maximum + 1e-5).all(), 'Deletion improves the fixed-constraint maximum')
        check((group.product_min + 1e-5 >= control.product_min).all(), 'Deletion lowers the fixed-constraint minimum')
        check((group.growth <= control.growth + 1e-5).all(), 'Deletion improves unconstrained maximum growth')
    training = ROOT / 'runs' / name / 'training'
    training_manifest = read_json(training / 'manifest.json')
    check(training_manifest['complete'], 'Training did not complete')
    check(sha256(training / 'predictions.csv') == training_manifest['predictions_sha256'], 'Derived prediction hash mismatch')
    check(sha256(training / 'metrics.csv') == training_manifest['metrics_sha256'], 'Predictive metric hash mismatch')
    networks = read_json(training / 'networks.json')
    for panel in ['environment', 'combination']:
        check(len(networks[panel + '_gnn']) == 3, f'{panel} ensemble does not have three members')
        split = read_json(training / f'{panel}_split.json')
        check(not set(split['train']) & set(split['test']), 'Train/test scenario leakage')
        for member, metadata in enumerate(networks[panel + '_gnn']):
            check(sha256(training / f'{panel}_gnn_{member}.safetensors') == metadata['checkpoint_sha256'], 'Checkpoint hash mismatch')
    curves = pd.read_csv(ROOT / 'runs' / name / 'search/curves.csv')
    search_manifest = read_json(ROOT / 'runs' / name / 'search/manifest.json')
    check(search_manifest['source_predictions_sha256'] == sha256(training / 'predictions.csv'), 'Search used stale prior predictions')
    selections = pd.read_json(ROOT / 'runs' / name / 'search/verifications.jsonl', lines=True)
    check(not selections.duplicated(['environment', 'seed', 'method', 'scenario_id']).any(), 'Search repeated a candidate')
    check(selections[selections.step == 1].scenario_id.str.endswith('__WT').all(), 'Unmodified control was not first and charged')
    for _, group in selections.groupby(['environment', 'seed']):
        initials = [tuple(method.sort_values('step').head(8).scenario_id) for _, method in group.groupby('method')]
        check(len(set(initials)) == 1, 'Methods did not share initial observations')
    check((curves.total_solver_calls >= curves.online_solver_calls).all(), 'Solver accounting is inconsistent')
    for relative, checksum in read_json(ROOT / 'runs' / name / 'report/artifact_manifest.json')['files'].items():
        check(sha256(ROOT / relative) == checksum, f'Artifact checksum mismatch: {relative}')
    result = dict(dataset=name, audited_at=utc_now(), passed=not failures, failures=failures,
                  scenarios=len(frame), feasible=len(feasible), search_verifications=len(selections),
                  positive_minimum_scenarios=int((feasible.product_min > 1e-7).sum()))
    write_json(ROOT / 'runs' / name / 'audit.json', result)
    return result


if __name__ == '__main__':
    result = audit(sys.argv[1] if len(sys.argv) > 1 else 'e_coli_core')
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result['passed'] else 1)
