import pytest
from fastapi.testclient import TestClient

from bioflux.server import app


@pytest.fixture
def client():
    with TestClient(app) as client:
        yield client


@pytest.mark.parametrize('body', [
    {'genes': ['unknown']}, {'genes': ['b0115', 'b0115']},
    {'genes': ['b0115', 'b0767', 'b1779']}, {'glucose': 99},
    {'oxygen': -1}, {'growth_fraction': 0},
])
def test_invalid_scenarios_are_rejected(client, body):
    assert client.post('/api/simulate', json=body).status_code == 422


def test_requests_do_not_leak_mutant_state(client):
    first = client.post('/api/simulate', json={}).json()
    mutant = client.post('/api/simulate', json={'genes': ['b2779']}).json()
    last = client.post('/api/simulate', json={}).json()
    assert first['feasible'] and last['feasible']
    assert not mutant['feasible']
    assert first['growth'] == pytest.approx(last['growth'], abs=1e-7)
    assert first['model_sha256'] == last['model_sha256']


def test_graph_and_experiment_identity(client):
    model = client.get('/api/model').json()
    assert model['reactions'] == 95 and model['metabolites'] == 72
    assert len(model['graph']['nodes']) == 167
    assert len({n['id'] for n in model['graph']['nodes']}) == 167
    result = client.get('/api/results/e_coli_core').json()
    assert result['audit']['passed']
    assert len(result['metrics']) == 10
    assert result['audit']['search_verifications'] == len(result['curves']) == 3200
    assert client.get('/api/results/unknown').status_code == 422


def test_envelope_keeps_failed_production_labels_missing(client):
    rows = client.post('/api/envelope', json={'genes': ['b2779']}).json()
    assert len(rows) == 15
    assert all(not row['feasible'] and row['product_min'] is None for row in rows)
