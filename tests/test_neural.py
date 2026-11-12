import numpy as np
import torch
from safetensors.torch import load_file

from bioflux.neural import MLP, BipartiteMPNN, predict_network, train_network


def test_checkpoint_roundtrip_and_missing_labels_do_not_train(tmp_path):
    rng = np.random.default_rng(71)
    x = rng.normal(size=(24, 7)).astype(np.float32)
    masks = np.zeros((24, 4), np.float32)
    y = np.abs(rng.normal(size=(24, 4))).astype(np.float32)
    y[:, 3] = np.arange(24) % 2
    observed = np.ones_like(y)
    observed[:12, 2] = 0
    altered = y.copy()
    altered[:12, 2] = 999
    config = dict(epochs=3, patience=3, batch_size=8, hidden_dim=8)
    train, validation = np.arange(18), np.arange(18, 24)
    stoich = np.array([[-1, 1, 0, 0], [1, -1, 1, -1]], np.float32)
    first, meta = train_network('mlp', x, masks, y, observed, train, validation,
                               stoich, config, 11, tmp_path / 'first.safetensors')
    second, _ = train_network('mlp', x, masks, altered, observed, train, validation,
                              stoich, config, 11, tmp_path / 'second.safetensors')
    expected = predict_network(first, x, masks, meta['scales'])
    actual = predict_network(second, x, masks, meta['scales'])
    np.testing.assert_allclose(actual, expected, atol=1e-6)
    loaded = MLP(x.shape[1])
    loaded.load_state_dict(load_file(str(tmp_path / 'first.safetensors')))
    np.testing.assert_allclose(predict_network(loaded, x, masks, meta['scales']), expected, atol=1e-6)


def test_genome_sparse_propagation_matches_dense_graph():
    matrix = np.zeros((6, 501), np.float32)
    matrix[0, :200] = -1
    matrix[1, :200] = 2
    matrix[2, 200:400] = -3
    matrix[3, 200:400] = 1
    network = BipartiteMPNN(matrix, hidden=8)
    values = torch.randn(3, 501, 8)
    sparse = network.propagate('positive', values)
    dense = network.positive @ values
    torch.testing.assert_close(sparse, dense, atol=1e-6, rtol=1e-5)
    x = torch.randn(3, 7)
    masks = torch.zeros(3, 501)
    output = network(x, masks)
    assert output.shape == (3, 4)
    assert torch.isfinite(output).all()
    output.sum().backward()
    assert network.reactions.grad is not None
