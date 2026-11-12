"""Independent HiGHS numerical cross-check of GLPK labels on representative cases."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
from scipy.optimize import linprog

from bioflux.simulator import Simulator, clean_flux
from bioflux.storage import ROOT, utc_now, write_json


def compare(glucose, oxygen, genes, model_id='e_coli_core'):
    sim = Simulator(model_id)
    glpk = sim.simulate(glucose, oxygen, genes, ranges=True)
    biomass = sim.reactions.index(sim.biomass)
    product = sim.reactions.index(sim.product)
    growth_objective = np.zeros(len(sim.reactions))
    growth_objective[biomass] = -1
    product_objective = np.zeros(len(sim.reactions))
    product_objective[product] = 1
    independent = dict(growth=None, product_min=None, product_max=None, feasible=False)
    calls = 0
    def solve(objective, bounds):
        nonlocal calls
        calls += 1
        return linprog(objective, A_eq=sim.stoich, b_eq=np.zeros(sim.stoich.shape[0]),
                       bounds=bounds, method='highs', options={'time_limit': 30})
    with sim.model:
        sim.environment(glucose, oxygen)
        wt = solve(growth_objective, [r.bounds for r in sim.model.reactions])
        if wt.success and -wt.fun > 1e-7:
            requirement = -wt.fun * sim.growth_fraction
            for gene in genes:
                sim.model.genes.get_by_id(gene).knock_out()
            bounds = [r.bounds for r in sim.model.reactions]
            growth = solve(growth_objective, bounds)
            if growth.success:
                independent['growth'] = float(-growth.fun)
                if -growth.fun + 1e-7 >= requirement:
                    bounds[biomass] = (max(bounds[biomass][0], requirement), bounds[biomass][1])
                    minimum = solve(product_objective, bounds)
                    maximum = solve(-product_objective, bounds)
                    if minimum.success and maximum.success:
                        independent.update(feasible=True, product_min=clean_flux(minimum.fun),
                                           product_max=clean_flux(-maximum.fun))
    errors = {}
    for target in ['growth', 'product_min', 'product_max']:
        if glpk[target] is not None and independent[target] is not None:
            errors[target] = abs(glpk[target] - independent[target])
    passed = independent['feasible'] == glpk['feasible'] and all(v < 1e-5 for v in errors.values())
    return dict(glucose=glucose, oxygen=oxygen, genes=genes, passed=passed,
                absolute_errors=errors, glpk=glpk, highs=independent, highs_calls=calls)


if __name__ == '__main__':
    model_id = sys.argv[1] if len(sys.argv) > 1 else 'e_coli_core'
    if model_id not in {'e_coli_core', 'iML1515'}:
        raise ValueError('Select e_coli_core or iML1515.')
    cases = [compare(glucose, oxygen, genes, model_id) for glucose, oxygen, genes in [
        (10, 20, []), (10, 20, ['b4025']), (10, 20, ['b2779']),
        (8, 0, ['b0115', 'b0767']), (2, 0, [])]]
    result = dict(model_id=model_id, checked_at=utc_now(), passed=all(c['passed'] for c in cases), cases=cases,
                  note='Numerical solver cross-check; uses the same reconstruction and GPR/environment translation. Not biological validation.')
    write_json(ROOT / 'runs' / model_id / 'solver_crosscheck.json', result)
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result['passed'] else 1)
