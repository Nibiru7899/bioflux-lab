"""Load only locally generated safetensors; construct features without solving."""
import numpy as np
from safetensors.torch import load_file

from bioflux.neural import BipartiteMPNN, predict_network
from bioflux.storage import ROOT, read_json, sha256


def predict(simulator, glucose, oxygen, genes, name='e_coli_core'):
    directory = ROOT / 'runs' / name / 'training'
    metadata = read_json(directory / 'networks.json')['environment_gnn']
    manifest = read_json(directory / 'manifest.json')
    if simulator.model_sha256 != manifest['dataset_manifest']['design']['model_sha256']:
        raise ValueError('The checkpoint and simulator use different metabolic models.')
    if simulator.growth_fraction != manifest['dataset_manifest']['design']['growth_fraction']:
        raise ValueError('The checkpoint and simulator use different growth requirements.')
    genes = set(genes)
    mask = simulator.disabled_reactions(genes)
    x = np.array([[glucose / 12, oxygen / 20, len(genes) / 2,
                   *(float(g in genes) for g in simulator.genes), *mask]], np.float32)
    values = []
    for member, meta in enumerate(metadata):
        checkpoint = directory / f'environment_gnn_{member}.safetensors'
        if sha256(checkpoint) != meta['checkpoint_sha256']:
            raise ValueError('Checkpoint checksum mismatch.')
        network = BipartiteMPNN(simulator.stoich, meta['hidden_dim'])
        network.load_state_dict(load_file(str(checkpoint)))
        values.append(predict_network(network, x, mask[None], meta['scales'])[0])
    values = np.array(values)
    return dict(growth=float(values[:, 0].mean()), product_max=float(values[:, 1].mean()),
                product_min=float(values[:, 2].mean()), feasibility_probability=float(values[:, 3].mean()),
                product_min_std=float(values[:, 2].std()), members=len(values), solver_calls=0)
