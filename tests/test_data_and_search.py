import numpy as np
import pandas as pd
import pytest

from bioflux.dataset import interventions, split_groups, combination_partitions
from bioflux.search import choose_next
from bioflux.training import targets, feasible_utility_moments


def test_frozen_grouped_splits_and_unique_interventions():
    choices = interventions([f'g{i}' for i in range(20)], 100, 71)
    assert choices == interventions([f'g{i}' for i in range(20)], 100, 71)
    assert len(choices) == len(set(choices)) == 100
    assert all(len(set(c)) == len(c) for c in choices)
    splits = split_groups([str(i) for i in range(24)], 11)
    assert list(splits.values()).count('train') == 16
    assert list(splits.values()).count('test') == 4
    assert list(splits.values()).count('validation') == 4
    pilot = interventions([f'g{i}' for i in range(1500)], 9, 71)
    assert any(len(c) == 1 for c in pilot) and any(len(c) == 2 for c in pilot)


def test_missing_infeasible_labels_are_masked_not_regressed_as_zero():
    frame = pd.DataFrame(dict(growth=[1, 0, None], product_max=[3, None, None],
        product_min=[0.5, None, None], feasible=[True, False, False],
        status=['optimal', 'below_growth_requirement', 'time_limit']))
    y, observed, valid = targets(frame)
    assert observed[:, 2].tolist() == [1, 0, 0]
    assert valid.tolist() == [True, True, False]
    assert y[:, 3].tolist() == [1, 0, 0]


def test_biochemically_equivalent_interventions_never_cross_splits():
    choices = [(), ('a',), ('b',), ('a', 'b'), ('a', 'c'), ('a', 'd'), ('b', 'c'), ('b', 'd')]
    masks = {key: np.array(value, np.float32) for key, value in {
        'WT': [0, 0, 0, 0], 'a': [1, 0, 0, 0], 'b': [0, 1, 0, 0],
        'a+b': [1, 1, 0, 0], 'a+c': [1, 1, 0, 0], 'a+d': [1, 0, 1, 0],
        'b+c': [0, 1, 1, 0], 'b+d': [0, 1, 0, 0]}.items()}
    split = combination_partitions(choices, masks, 71)
    assert split['a+b'] == split['a+c']
    assert split['b+d'] == split['b'] == 'train'


def test_training_and_search_reject_changed_growth_semantics():
    from bioflux.training import train
    from bioflux.search import discover
    for command in [train, discover]:
        with pytest.raises(ValueError, match='growth fraction differs'):
            command({'growth_fraction': 0.2})


def test_utility_uncertainty_vanishes_for_certain_infeasibility():
    members = np.array([[[1, 2, 1, 0]], [[1, 2, 10, 0]]], dtype=float)
    mean, std = feasible_utility_moments(members)
    np.testing.assert_array_equal(mean, [0])
    np.testing.assert_array_equal(std, [0])


def test_utility_aggregation_preserves_member_feasibility_production_dependence():
    # Neither member predicts feasible production; multiplying marginal means invents it.
    members = np.array([[[1, 2, 0, 1]], [[1, 2, 10, 0]]], dtype=float)
    mean, std = feasible_utility_moments(members)
    np.testing.assert_array_equal(mean, [0])
    np.testing.assert_array_equal(std, [0])


@pytest.mark.parametrize('method', ['random', 'greedy', 'tree', 'gnn'])
def test_acquisition_uses_only_acquired_scores_and_never_repeats(method):
    x = np.random.default_rng(5).normal(size=(12, 5))
    indices, outcomes = [0, 1, 2, 3], [0.0, 0.5, 0.2, 0.0]
    remaining = np.arange(4, 12)
    genes = [[f'g{i}'] for i in range(12)]
    priors, std = np.linspace(0, 1, 12), np.ones(12) * 0.2
    first = choose_next(method, x, indices, outcomes, remaining,
                        np.random.default_rng(11), genes, priors, std)
    second = choose_next(method, x, indices, outcomes, remaining,
                         np.random.default_rng(11), genes, priors, std)
    assert first in remaining and first == second
