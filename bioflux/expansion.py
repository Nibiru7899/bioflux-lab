"""Measured, recorded gate for the genome-scale extension."""
import time
import math

from bioflux.dataset import generate, load_dataset
from bioflux.storage import ROOT, Budget, project_bytes, read_json, write_json


def expansion_gate(config, budget=None):
    budget = budget or Budget(config['max_hours'], config['max_disk_gb'])
    core = ROOT / 'runs/e_coli_core/report/artifact_manifest.json'
    if not core.exists():
        raise ValueError('Complete the core workflow and report before genome expansion.')
    pilot_name = 'iML1515_pilot_200'
    pilot_dir = ROOT / 'data' / pilot_name
    if not (pilot_dir / 'manifest.json').exists():
        generate(config, 'iML1515', 200, budget, pilot_name)
    pilot = read_json(pilot_dir / 'manifest.json')
    if not pilot['complete'] or pilot['scenarios'] != 200:
        raise ValueError('The genome pilot must contain exactly 200 completed scenarios.')
    seconds_per_scenario = pilot['generation_seconds'] / pilot['scenarios']
    projected_generation = seconds_per_scenario * 10000 * 2  # Conservative cold-start margin.
    total_bytes = project_bytes()
    remaining_seconds = budget.seconds - (time.monotonic() - budget.start)
    # Reserve two thirds of remaining time for training/evaluation; 2 GB for artifacts.
    accepted = projected_generation < remaining_seconds / 3 and total_bytes + 2 * 1024 ** 3 < budget.disk_bytes
    gate = dict(pilot_scenarios=pilot['scenarios'], pilot_seconds=pilot['generation_seconds'],
                projected_generation_seconds=projected_generation, remaining_seconds=remaining_seconds,
                project_bytes=total_bytes, accepted=accepted, generation_accepted=accepted,
                dataset_limit=10000 if accepted else 0,
                reason='Measured generation fits with training and disk headroom' if accepted
                       else 'Conservative runtime or disk headroom gate failed')
    write_json(ROOT / 'runs/iML1515/expansion_gate.json', gate)
    return gate


def benchmark_training(config, name, remaining_seconds):
    """Measure the actual full graph before committing to the ensemble workload."""
    import torch
    from bioflux.neural import BipartiteMPNN, seed_all
    from bioflux.simulator import Simulator
    frame, x, masks, manifest = load_dataset(name)
    seed_all(71)
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    if device.type == 'cuda':
        torch.cuda.reset_peak_memory_stats()
    sim = Simulator(manifest['model_id'], config['growth_fraction'])
    if sim.model_sha256 != manifest['design']['model_sha256']:
        raise ValueError('Resource benchmark model differs from the frozen dataset model.')
    network = BipartiteMPNN(sim.stoich, config['hidden_dim']).to(device)
    batch = config['batch_size']
    tx, tm = torch.tensor(x[:batch], device=device), torch.tensor(masks[:batch], device=device)
    optimizer = torch.optim.AdamW(network.parameters(), lr=0.003)
    for _ in range(3):
        optimizer.zero_grad(set_to_none=True)
        network(tx, tm).square().mean().backward()
        optimizer.step()
    if device.type == 'cuda':
        torch.cuda.synchronize()
    started = time.perf_counter()
    for _ in range(10):
        optimizer.zero_grad(set_to_none=True)
        network(tx, tm).square().mean().backward()
        optimizer.step()
    if device.type == 'cuda':
        torch.cuda.synchronize()
    seconds_per_step = (time.perf_counter() - started) / 10
    valid = frame.status.isin(['optimal', 'below_growth_requirement', 'infeasible'])
    steps = sum(math.ceil(int((valid & (frame[panel + '_split'] == 'train')).sum()) / batch)
                for panel in ['environment', 'combination']) * config['ensemble_members'] * config['epochs']
    projected = seconds_per_step * steps * 1.5 + 1800
    accepted = projected < remaining_seconds
    if accepted and device.type == 'cuda':
        network.eval()
        with torch.no_grad():
            network(torch.tensor(x[:128], device=device), torch.tensor(masks[:128], device=device))
        torch.cuda.synchronize()
    info = dict(device=str(device), torch_version=torch.__version__, batch_size=batch,
                model_sha256=sim.model_sha256, reactions=len(sim.reactions),
                metabolites=sim.stoich.shape[0], configured_epochs=config['epochs'],
                seconds_per_step=seconds_per_step, projected_training_seconds=projected,
                remaining_seconds=remaining_seconds, accepted=accepted,
                device_name=torch.cuda.get_device_name(0) if device.type == 'cuda' else 'CPU',
                peak_cuda_allocated_bytes=torch.cuda.max_memory_allocated() if device.type == 'cuda' else 0,
                total_gpu_bytes=torch.cuda.get_device_properties(0).total_memory if device.type == 'cuda' else 0,
                note='Full graph; 3 warmup/10 measured backward steps; all configured ensemble epochs, 50% margin and 30-minute reserve.')
    write_json(ROOT / 'runs' / name / f'training_benchmark_{device.type}.json', info)
    return info


def expand(config, budget=None):
    budget = budget or Budget(config['max_hours'], config['max_disk_gb'])
    gate = expansion_gate(config, budget)
    if not gate['accepted']:
        return gate
    genome_config = dict(config, batch_size=min(config['batch_size'], 16), scenario_limit=10000)
    write_json(ROOT / 'runs/iML1515/config.json', genome_config)
    generate(genome_config, 'iML1515', 10000, budget, 'iML1515')
    remaining = budget.seconds - (time.monotonic() - budget.start)
    gate['dataset_generated'] = True
    gate['training_gate'] = benchmark_training(genome_config, 'iML1515', remaining)
    gate['accepted'] = gate['training_gate']['accepted']
    if not gate['accepted']:
        gate['reason'] = 'Dataset retained; measured full-graph training exceeds remaining compute budget.'
    write_json(ROOT / 'runs/iML1515/expansion_gate.json', gate)
    if not gate['accepted']:
        return gate
    from bioflux.training import train
    from bioflux.search import discover
    from bioflux.report import report
    train(genome_config, 'iML1515', budget)
    discover(genome_config, 'iML1515', budget)
    report('iML1515')
    return gate
