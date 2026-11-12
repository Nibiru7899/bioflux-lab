"""Reproducible local commands; imports are delayed for data-only operations."""
import argparse
import importlib.metadata
import json
import platform
import time

from bioflux.storage import ROOT, Budget, read_json, sha256, utc_now, write_json


def main():
    parser = argparse.ArgumentParser(description='BioFlux Lab computational research pipeline')
    parser.add_argument('--config', default=str(ROOT / 'configs' / 'default.json'))
    commands = parser.add_subparsers(dest='command', required=True)
    for name in ['download', 'generate', 'train', 'evaluate', 'report', 'all', 'expand', 'study']:
        command = commands.add_parser(name)
        command.add_argument('--model', choices=['e_coli_core', 'iML1515'], default='e_coli_core')
        command.add_argument('--name', default=None, help='Dataset/run directory name')
        if name in ['generate', 'all', 'study']:
            command.add_argument('--limit', type=int, default=None)
    simulate = commands.add_parser('simulate')
    simulate.add_argument('--model', choices=['e_coli_core', 'iML1515'], default='e_coli_core')
    simulate.add_argument('--glucose', type=float, default=10)
    simulate.add_argument('--oxygen', type=float, default=20)
    simulate.add_argument('--genes', nargs='*', default=[])
    args = parser.parse_args()
    config = read_json(args.config)
    budget = Budget(config['max_hours'], config['max_disk_gb'])
    budget.check()
    if args.command == 'simulate':
        from bioflux.simulator import Simulator
        print(json.dumps(Simulator(args.model, config['growth_fraction']).simulate(
            args.glucose, args.oxygen, args.genes, ranges=True), indent=2))
        return
    name = args.name or args.model
    if args.command == 'study' and (args.model != 'e_coli_core' or name != 'e_coli_core'):
        parser.error('The full study starts with the default core model and dataset name.')
    if not name.replace('_', '').replace('-', '').isalnum():
        parser.error('Dataset names may contain only letters, digits, underscores and hyphens.')
    run_dir = ROOT / 'runs' / name
    state = dict(command=args.command, model=args.model, dataset=name, config=config,
                 scenario_limit_override=getattr(args, 'limit', None),
                 source_sha256={p.name: sha256(p) for p in sorted((ROOT / 'bioflux').glob('*.py'))},
                 started_at=utc_now(), status='running')
    started = time.perf_counter()
    history_name = state['started_at'].replace(':', '').replace('+', '_') + '_' + args.command + '.json'
    run_dir.mkdir(parents=True, exist_ok=True)
    write_json(run_dir / 'execution.json', state)
    try:
        if args.command == 'expand':
            from bioflux.expansion import expand
            print(json.dumps(expand(config, budget), indent=2), flush=True)
        if args.command in ['download', 'all', 'study']:
            from bioflux.downloads import download
            print(json.dumps(download(args.model), indent=2), flush=True)
        if args.command in ['generate', 'all', 'study']:
            from bioflux.dataset import generate
            generate(config, args.model, args.limit, budget, name)
        if args.command in ['train', 'all', 'study']:
            from bioflux.training import train
            train(config, name, budget)
        if args.command in ['evaluate', 'all', 'study']:
            from bioflux.search import discover
            discover(config, name, budget)
        if args.command in ['report', 'all', 'study']:
            from bioflux.report import report
            print(f'Report: {report(name)}', flush=True)
        if args.command == 'study':
            from bioflux.downloads import download
            download('iML1515')
            from bioflux.expansion import expand
            print(json.dumps(expand(config, budget), indent=2), flush=True)
        versions = {d.metadata['Name']: d.version for d in importlib.metadata.distributions()}
        environment = dict(python=platform.python_version(), platform=platform.platform(), packages=versions)
        write_json(run_dir / 'environment.json', environment)
        state['environment'] = environment
        state.update(status='complete', finished_at=utc_now())
    except Exception as error:
        state.update(status='failed', finished_at=utc_now(), error=f'{type(error).__name__}: {error}')
        raise
    finally:
        state['elapsed_seconds'] = time.perf_counter() - started
        write_json(run_dir / 'execution.json', state)
        write_json(run_dir / 'executions' / history_name, state)


if __name__ == '__main__':
    main()
