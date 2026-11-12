"""Explicit growth-constrained production potential with counted LP solves."""
import time
import warnings

import cobra
import numpy as np
from cobra.util.array import create_stoichiometric_matrix
from cobra.util.solver import linear_reaction_coefficients

from bioflux.storage import ROOT, read_json, sha256

TOL = 1e-7


def clean_flux(value):
    value = max(0.0, float(value))
    return 0.0 if value < TOL else value


class Simulator:
    def __init__(self, model_id='e_coli_core', growth_fraction=0.1):
        if not 0 < growth_fraction <= 1:
            raise ValueError('growth_fraction must be in (0, 1].')
        self.path = ROOT / 'data' / 'models' / f'{model_id}.json'
        self.model_sha256 = sha256(self.path)
        if self.model_sha256 != read_json(self.path.with_suffix('.manifest.json'))['sha256']:
            raise ValueError('Metabolic model checksum differs from its source manifest.')
        self.model = cobra.io.load_json_model(str(self.path))
        self.model.solver = 'glpk'
        self.model.solver.configuration.timeout = 30
        self.model.solver.configuration.tolerances.feasibility = TOL
        biomass = list(linear_reaction_coefficients(self.model))
        if len(biomass) != 1:
            raise ValueError('Expected a single biomass objective in the source model.')
        self.biomass = biomass[0].id
        self.product = 'EX_succ_e'
        self.growth_fraction = growth_fraction
        self.genes = sorted(g.id for g in self.model.genes)
        self.reactions = [r.id for r in self.model.reactions]
        self.stoich = create_stoichiometric_matrix(self.model)
        self.calls = 0
        self.baselines = {}

    def environment(self, glucose, oxygen):
        if not np.isfinite([glucose, oxygen]).all() or glucose <= 0 or oxygen < 0:
            raise ValueError('Glucose must be positive and oxygen nonnegative, both finite.')
        # Preserve salts, water and maintenance from the source medium; close other carbon uptake.
        medium = self.model.medium
        for exchange in self.model.exchanges:
            metabolite = next(iter(exchange.metabolites))
            if metabolite.elements.get('C', 0) > 0:
                medium.pop(exchange.id, None)
        medium['EX_glc__D_e'] = float(glucose)
        medium['EX_o2_e'] = float(oxygen)
        self.model.medium = medium
        self.model.reactions.get_by_id(self.product).lower_bound = 0.0

    def _solve(self):
        self.calls += 1
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', UserWarning)
            return self.model.optimize()

    def wildtype(self, glucose, oxygen):
        key = (float(glucose), float(oxygen))
        if key not in self.baselines:
            with self.model:
                self.environment(*key)
                self.model.objective = self.biomass
                solution = self._solve()
                self.baselines[key] = float(solution.objective_value) if solution.status == 'optimal' else None
        return self.baselines[key]

    def disabled_reactions(self, genes):
        unknown = set(genes) - set(self.genes)
        if unknown:
            raise ValueError(f'Unknown genes: {sorted(unknown)}')
        with self.model:
            for gene in genes:
                self.model.genes.get_by_id(gene).knock_out()
            return np.array([not r.functional for r in self.model.reactions], dtype=np.float32)

    def simulate(self, glucose, oxygen, genes=(), ranges=False, growth_fraction=None):
        genes = tuple(sorted(set(genes)))
        self.disabled_reactions(genes)  # Validate before performing any LP.
        fraction = self.growth_fraction if growth_fraction is None else growth_fraction
        if not 0 < fraction <= 1:
            raise ValueError('growth_fraction must be in (0, 1].')
        started, before = time.perf_counter(), self.calls
        baseline = self.wildtype(glucose, oxygen)
        result = dict(glucose=float(glucose), oxygen=float(oxygen), genes=list(genes),
                      model_sha256=self.model_sha256, growth_fraction=fraction,
                      wildtype_growth=baseline, growth_requirement=None,
                      growth=None, product_max=None, product_min=None, feasible=False,
                      status='wildtype_no_growth', mass_balance_residual=None)
        if baseline is not None and baseline > TOL:
            requirement = fraction * baseline
            result['growth_requirement'] = requirement
            with self.model:
                self.environment(glucose, oxygen)
                for gene in genes:
                    self.model.genes.get_by_id(gene).knock_out()
                self.model.objective = self.biomass
                growth = self._solve()
                result['status'] = growth.status
                if growth.status == 'optimal':
                    result['growth'] = float(growth.objective_value)
                    if growth.objective_value + TOL >= requirement:
                        biomass = self.model.reactions.get_by_id(self.biomass)
                        biomass.lower_bound = max(biomass.lower_bound, requirement)
                        self.model.objective = self.product
                        self.model.objective_direction = 'max'
                        production = self._solve()
                        result['status'] = production.status
                        if production.status == 'optimal':
                            residual = float(np.abs(self.stoich @ production.fluxes.to_numpy()).max())
                            result.update(product_max=clean_flux(production.objective_value),
                                          mass_balance_residual=residual,
                                          feasible=residual < 1e-5)
                            if ranges:
                                self.model.objective_direction = 'min'
                                minimum = self._solve()
                                result['range_status'] = minimum.status
                                if minimum.status == 'optimal':
                                    result['product_min'] = clean_flux(minimum.objective_value)
                                else:
                                    result['status'] = 'range_' + minimum.status
                                    result['feasible'] = False
                    else:
                        result['status'] = 'below_growth_requirement'
        result['solver_calls'] = self.calls - before
        result['elapsed_seconds'] = time.perf_counter() - started
        return result

    def envelope(self, glucose, oxygen, genes=(), points=15):
        return [self.simulate(glucose, oxygen, genes, ranges=True, growth_fraction=float(f))
                for f in np.linspace(0.1, 1.0, points)]
