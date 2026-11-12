import numpy as np
import pytest

from bioflux.simulator import Simulator


@pytest.fixture
def sim():
    return Simulator()


def test_repeatability_restoration_mass_balance_and_counts(sim):
    bounds = [r.bounds for r in sim.model.reactions]
    objective = str(sim.model.objective.expression)
    first = sim.simulate(10, 20, ranges=True)
    second = sim.simulate(10, 20, ranges=True)
    assert first['feasible'] and second['feasible']
    assert first['solver_calls'] == 4  # WT, mutant growth, maximum, minimum
    assert second['solver_calls'] == 3  # Cached WT only, still solve all three objectives
    assert first['growth'] == pytest.approx(second['growth'], abs=1e-7)
    assert first['product_min'] <= first['product_max'] + 1e-7
    assert first['mass_balance_residual'] < 1e-7
    assert [r.bounds for r in sim.model.reactions] == bounds
    assert str(sim.model.objective.expression) == objective
    assert sim.model.objective_direction == 'max'


def test_medium_signs_and_no_product_import(sim):
    with sim.model:
        sim.environment(6, 2)
        assert sim.model.reactions.EX_glc__D_e.lower_bound == -6
        assert sim.model.reactions.EX_o2_e.lower_bound == -2
        assert sim.model.reactions.EX_succ_e.lower_bound == 0
        assert sim.model.reactions.EX_ac_e.lower_bound == 0


def test_fixed_growth_floor_and_monotonic_production_potential(sim):
    baseline = sim.simulate(10, 20, ranges=True)
    knockout = sim.simulate(10, 20, ['b1779'], ranges=True)
    assert baseline['growth_requirement'] == pytest.approx(knockout['growth_requirement'])
    if knockout['feasible']:
        assert knockout['product_max'] <= baseline['product_max'] + 1e-6


def test_gene_rule_isozymes_are_not_independent_reaction_deletions(sim):
    with sim.model:
        pgi = sim.model.reactions.PGI
        assert pgi.functional
        sim.model.genes.b4025.knock_out()
        assert not pgi.functional
        assert pgi.bounds == (0, 0)
    with sim.model:
        # Acetaldehyde dehydrogenase can be catalyzed by alternative genes.
        rule = sim.model.reactions.ACALD
        assert ' or ' in rule.gene_reaction_rule
        gene = next(iter(rule.genes))
        gene.knock_out()
        assert rule.functional
        for other in rule.genes:
            other.knock_out()
        assert not rule.functional


def test_invalid_inputs_do_not_solve(sim):
    before = sim.calls
    with pytest.raises(ValueError, match='Unknown genes'):
        sim.simulate(10, 20, ['invented'])
    for glucose, oxygen in [(0, 1), (10, -1), (np.nan, 2)]:
        with pytest.raises(ValueError):
            sim.simulate(glucose, oxygen)
    assert sim.calls == before


def test_lethal_intervention_never_returns_fabricated_product(sim):
    outcome = sim.simulate(10, 20, ['b2779'], ranges=True)
    assert not outcome['feasible']
    assert outcome['product_min'] is None and outcome['product_max'] is None


def test_envelope_has_consistent_growth_reference(sim):
    rows = sim.envelope(10, 20, points=4)
    assert len(rows) == 4
    assert len({r['wildtype_growth'] for r in rows}) == 1
    maxima = [r['product_max'] for r in rows if r['feasible']]
    assert all(a + 1e-6 >= b for a, b in zip(maxima, maxima[1:]))


def test_failed_minimum_solve_is_not_a_verified_range(sim, monkeypatch):
    from types import SimpleNamespace
    solve = sim._solve
    def fail_minimum():
        if sim.model.objective_direction == 'min':
            sim.calls += 1
            return SimpleNamespace(status='time_limit')
        return solve()
    monkeypatch.setattr(sim, '_solve', fail_minimum)
    outcome = sim.simulate(10, 20, ranges=True)
    assert not outcome['feasible']
    assert outcome['status'] == 'range_time_limit'
    assert outcome['product_min'] is None


def test_model_identity_drift_is_rejected_before_loading(monkeypatch):
    monkeypatch.setattr('bioflux.simulator.sha256', lambda path: '0' * 64)
    with pytest.raises(ValueError, match='checksum'):
        Simulator()
