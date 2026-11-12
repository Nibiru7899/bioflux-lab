from bioflux import expansion


def test_declined_training_gate_preserves_dataset_and_stops_before_training(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(expansion, 'ROOT', tmp_path)
    monkeypatch.setattr(expansion, 'expansion_gate', lambda *args: {'accepted': True})
    monkeypatch.setattr(expansion, 'generate', lambda *args: calls.append('dataset'))
    monkeypatch.setattr(expansion, 'benchmark_training', lambda *args: {'accepted': False})
    def forbidden(*args, **kwargs):
        raise AssertionError('Training started despite the measured resource rejection')
    monkeypatch.setattr('bioflux.training.train', forbidden)
    result = expansion.expand(dict(max_hours=6, max_disk_gb=10, batch_size=64))
    assert calls == ['dataset']
    assert result['dataset_generated'] and not result['accepted']
    assert (tmp_path / 'runs/iML1515/expansion_gate.json').exists()
