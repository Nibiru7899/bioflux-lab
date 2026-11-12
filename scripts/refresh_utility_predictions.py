"""Recompute joint ensemble utility moments from fixed, verified checkpoints."""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
import pandas as pd
import torch
from safetensors.torch import load_file

from bioflux.dataset import load_dataset
from bioflux.neural import BipartiteMPNN, predict_network, seed_all
from bioflux.simulator import Simulator
from bioflux.storage import ROOT, read_json, sha256, utc_now, write_json
from bioflux.training import feasible_utility_moments


if __name__ == '__main__':
    name = sys.argv[1] if len(sys.argv) > 1 else 'e_coli_core'
    seed_all(71)
    frame, x, masks, dataset = load_dataset(name)
    sim = Simulator(dataset['model_id'], dataset['design']['growth_fraction'])
    directory = ROOT / 'runs' / name / 'training'
    manifest = read_json(directory / 'manifest.json')
    if not manifest['complete']:
        raise ValueError('Finish training before refreshing derived predictions.')
    prediction_path = directory / 'predictions.csv'
    old_hash = sha256(prediction_path)
    output = pd.read_csv(prediction_path, float_precision='round_trip')
    metadata = read_json(directory / 'networks.json')
    output['predicted_feasible_utility'] = output.predicted_product_min * output.predicted_feasibility_probability
    output['feasible_utility_std'] = 0.0
    refreshed = []
    for panel in ['environment', 'combination']:
        members = []
        for index, member in enumerate(metadata[panel + '_gnn']):
            checkpoint = directory / f'{panel}_gnn_{index}.safetensors'
            if sha256(checkpoint) != member['checkpoint_sha256']:
                raise ValueError('Checkpoint checksum mismatch.')
            model = BipartiteMPNN(sim.stoich, member['hidden_dim'])
            model.load_state_dict(load_file(str(checkpoint)))
            device = torch.device(member['device'])
            model.to(device)
            started = time.perf_counter()
            members.append(predict_network(model, x, masks, member['scales']))
            elapsed = time.perf_counter() - started
            member['utility_refresh_inference_seconds'] = member.get('utility_refresh_inference_seconds', 0) + elapsed
            refreshed.append(dict(panel=panel, member=index, device=str(device), seconds=elapsed,
                                  checkpoint_sha256=member['checkpoint_sha256']))
        mean, std = feasible_utility_moments(members)
        selected = (output.panel == panel) & (output.model == 'gnn')
        for column, values in [('predicted_feasible_utility', mean), ('feasible_utility_std', std)]:
            mapping = pd.Series(values, index=frame.scenario_id)
            output.loc[selected, column] = output.loc[selected, 'scenario_id'].map(mapping).to_numpy()
    if not np.isfinite(output[['predicted_feasible_utility', 'feasible_utility_std']]).all().all():
        raise ValueError('Derived utility moments contain non-finite values.')
    output.to_csv(prediction_path, index=False)
    write_json(directory / 'networks.json', metadata)
    manifest['predictions_sha256'] = sha256(prediction_path)
    manifest['utility_moments'] = 'Per-member minimum secretion multiplied by feasibility probability, then mean/std'
    write_json(directory / 'manifest.json', manifest)
    write_json(directory / 'utility_refresh.json', dict(refreshed_at=utc_now(),
        script_sha256=sha256(__file__), old_prediction_sha256=old_hash,
        new_prediction_sha256=manifest['predictions_sha256'], executions=refreshed,
        note='Only derived acquisition moments changed; trained weights, solver labels and marginal predictive metrics stayed fixed. Extra inference time is charged.'))
    print(f'{name}: refreshed joint feasible-utility moments from fixed checkpoints.')
