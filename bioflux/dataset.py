"""Frozen grouped splits and resumable solver-derived labels."""
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd

from bioflux.simulator import Simulator
from bioflux.storage import ROOT, read_json, sha256, utc_now, write_json


def intervention_key(genes):
    return '+'.join(sorted(genes)) or 'WT'


def interventions(genes, count, seed):
    rng = np.random.default_rng(seed)
    genes = sorted(genes)
    singles = [(), *((g,) for g in genes)]
    if count <= len(singles):
        # Preserve a mixture of singles/pairs even when all genome-scale singles do not fit.
        number_singles = max(0, count - 1) if count < 6 else (count - 1) * 2 // 3
        selected = rng.permutation(len(genes))[:number_singles]
        singles = [(), *((genes[i],) for i in sorted(selected))]
    pairs = set()
    target = min(count - len(singles), len(genes) * (len(genes) - 1) // 2)
    while len(pairs) < target:
        pair = tuple(sorted(rng.choice(genes, size=2, replace=False).tolist()))
        pairs.add(pair)
    return singles + sorted(pairs)


def split_groups(keys, seed):
    unique = sorted(set(keys))
    shuffled = np.random.default_rng(seed).permutation(unique)
    holdout = max(1, round(len(unique) / 6))
    if len(unique) < 3:
        raise ValueError('At least three distinct groups are required.')
    return {str(key): ('test' if i < holdout else 'validation' if i < 2 * holdout else 'train')
            for i, key in enumerate(shuffled)}


def combination_partitions(choices, masks, seed):
    profiles = {intervention_key(c): np.packbits(masks[intervention_key(c)].astype(bool)).tobytes().hex()
                for c in choices}
    familiar = {profiles[intervention_key(c)] for c in choices if len(c) < 2}
    novel = sorted(set(profiles.values()) - familiar)
    grouped = split_groups(novel, seed) if len(novel) >= 3 else {}
    return {key: grouped.get(profile, 'train') for key, profile in profiles.items()}


def generate(config, model_id='e_coli_core', limit=None, budget=None, name=None):
    simulator = Simulator(model_id, config['growth_fraction'])
    name = name or model_id
    directory = ROOT / 'data' / name
    directory.mkdir(parents=True, exist_ok=True)
    environments = [(g, o) for g in config['glucose'] for o in config['oxygen']]
    limit = config['scenario_limit'] if limit is None else limit
    if limit < len(environments):
        raise ValueError('The limit must cover every environment at least once.')
    per_environment = (limit + len(environments) - 1) // len(environments)
    choices = interventions(simulator.genes, per_environment, config['seed'])
    env_keys = [f'g{g}_o{o}' for g, o in environments]
    env_splits = split_groups(env_keys, config['seed'])
    masks = {intervention_key(c): simulator.disabled_reactions(c) for c in choices}
    combo_splits = combination_partitions(choices, masks, config['seed'] + 1)
    signature = dict(model_sha256=simulator.model_sha256,
                     growth_fraction=config['growth_fraction'], environments=environments,
                     interventions=[list(c) for c in choices], seed=config['seed'],
                     environment_splits=env_splits, combination_splits=combo_splits)
    if limit % len(environments):
        signature['environment_allocations'] = [limit // len(environments) + (i < limit % len(environments))
                                                for i in range(len(environments))]
    signature = json.loads(json.dumps(signature))
    manifest_path = directory / 'manifest.json'
    if manifest_path.exists() and read_json(manifest_path)['design'] != signature:
        raise ValueError('Dataset design changed. Use a new dataset name; existing labels are preserved.')
    write_json(manifest_path, dict(model_id=model_id, design=signature, complete=False, started_at=utc_now()))
    journal = directory / 'scenarios.jsonl'
    existing = {}
    if journal.exists():
        lines = journal.read_text().splitlines()
        for index, line in enumerate(lines):
            try:
                row = json.loads(line)
                existing[row['scenario_id']] = row
            except json.JSONDecodeError:
                if index != len(lines) - 1:
                    raise
                # Only a truncated last record is recoverable after interruption.
                journal.write_text('\n'.join(lines[:index]) + '\n', encoding='utf-8')
    started = time.perf_counter()
    with journal.open('a', encoding='utf-8') as output:
        for env_index, ((glucose, oxygen), env_key) in enumerate(zip(environments, env_keys)):
            if budget:
                budget.check()
            allocation = limit // len(environments) + (env_index < limit % len(environments))
            for genes in choices[:allocation]:
                key = intervention_key(genes)
                scenario_id = f'{env_key}__{key}'
                if scenario_id in existing:
                    continue
                if budget:
                    budget.check()
                try:
                    before = simulator.calls
                    row = simulator.simulate(glucose, oxygen, genes, ranges=True)
                except Exception as error:
                    row = dict(glucose=glucose, oxygen=oxygen, genes=list(genes),
                               feasible=False, growth=None, product_max=None,
                               status='solver_error', error=f'{type(error).__name__}: {error}',
                               model_sha256=simulator.model_sha256,
                               solver_calls=simulator.calls - before)
                row.update(scenario_id=scenario_id, environment_id=env_key,
                           intervention_id=key, environment_split=env_splits[env_key],
                           combination_split=combo_splits.get(key, 'train'))
                output.write(json.dumps(row, allow_nan=False) + '\n')
                output.flush()
                existing[scenario_id] = row
                if len(existing) % 250 == 0:
                    print(f'{name}: {len(existing)} scenarios, {simulator.calls} LP solves', flush=True)
                if budget and len(existing) % 50 == 0:
                    budget.check()
    rows = list(existing.values())
    frame = pd.DataFrame(rows)
    frame.to_csv(directory / 'scenarios.csv', index=False)
    features, reaction_masks = [], []
    for row in rows:
        gene_set = set(row['genes'])
        mask = masks[row['intervention_id']]
        features.append([row['glucose'] / 12, row['oxygen'] / 20, len(gene_set) / 2,
                         *(float(g in gene_set) for g in simulator.genes), *mask])
        reaction_masks.append(mask)
    np.savez_compressed(directory / 'features.npz', x=np.asarray(features, np.float32),
                        masks=np.asarray(reaction_masks, np.float32))
    write_json(manifest_path, dict(model_id=model_id, design=signature, complete=True, finished_at=utc_now(),
               scenarios=len(rows), unique_interventions=len(choices),
               label_solver_calls=int(frame.solver_calls.sum()),
               generation_seconds=float(frame.elapsed_seconds.sum()) if 'elapsed_seconds' in frame else None,
               this_invocation_seconds=time.perf_counter() - started,
               feasible=int(frame.feasible.sum()),
               excluded_environments=[k for k, v in frame.groupby('environment_id')
                                      if (v.status == 'wildtype_no_growth').all()],
               files={p.name: sha256(p) for p in [journal, directory / 'features.npz', directory / 'scenarios.csv']}))
    return directory


def load_dataset(name='e_coli_core'):
    directory = ROOT / 'data' / name
    manifest = read_json(directory / 'manifest.json')
    if not manifest['complete']:
        raise ValueError('Dataset generation is incomplete. Resume generation first.')
    for filename, checksum in manifest['files'].items():
        if sha256(directory / filename) != checksum:
            raise ValueError(f'Dataset checksum mismatch: {filename}')
    rows = [json.loads(line) for line in (directory / 'scenarios.jsonl').read_text().splitlines()]
    frame = pd.DataFrame(rows)
    with np.load(directory / 'features.npz', allow_pickle=False) as arrays:
        x, masks = arrays['x'].copy(), arrays['masks'].copy()
    if len(frame) != len(x):
        raise ValueError('Features and labels are misaligned.')
    return frame, x, masks, manifest
