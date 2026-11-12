"""Local React application API; delegates science to the existing simulator."""
from functools import lru_cache
from typing import Literal

import networkx as nx
import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, field_validator
from starlette.middleware.trustedhost import TrustedHostMiddleware

from bioflux.simulator import Simulator
from bioflux.storage import ROOT, read_json

app = FastAPI(title='BioFlux Lab', docs_url='/api/docs', redoc_url=None)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=['127.0.0.1', 'localhost', 'testserver'])
ModelName = Literal['e_coli_core', 'iML1515']


class Scenario(BaseModel):
    model_config = ConfigDict(extra='forbid')
    glucose: Literal[2, 4, 6, 8, 10, 12] = 10
    oxygen: Literal[0, 2, 10, 20] = 20
    genes: list[str] = Field(default_factory=list, max_length=2)

    @field_validator('genes')
    @classmethod
    def known_unique_genes(cls, genes):
        known = {g['id'] for g in model_info()['genes']}
        if len(set(genes)) != len(genes) or not set(genes) <= known:
            raise ValueError('Choose up to two distinct genes from the core model.')
        return genes


@lru_cache(maxsize=1)
def model_info():
    sim = Simulator()
    graph = nx.Graph()
    graph.add_nodes_from('m:' + m.id for m in sim.model.metabolites)
    graph.add_nodes_from('r:' + r.id for r in sim.model.reactions)
    currency = {'h_c', 'h2o_c', 'atp_c', 'adp_c', 'pi_c', 'nad_c', 'nadh_c', 'nadp_c', 'nadph_c'}
    links = []
    for reaction in sim.model.reactions:
        for metabolite in reaction.metabolites:
            a, b = 'r:' + reaction.id, 'm:' + metabolite.id
            graph.add_edge(a, b, weight=.12 if metabolite.id in currency else 1)
            links.append(dict(source=a, target=b))
    positions = nx.spring_layout(graph, seed=41, iterations=160, k=.3)
    nodes = []
    for kind, items in [('metabolite', sim.model.metabolites), ('reaction', sim.model.reactions)]:
        for item in items:
            node_id = ('m:' if kind == 'metabolite' else 'r:') + item.id
            nodes.append(dict(id=node_id, label=item.id, name=item.name, kind=kind,
                              x=float(positions[node_id][0]), y=float(positions[node_id][1]),
                              degree=int(graph.degree(node_id))))
    return dict(id='e_coli_core', organism='Escherichia coli', model_sha256=sim.model_sha256,
                reactions=len(sim.reactions), metabolites=len(sim.model.metabolites),
                genes=[dict(id=g.id, name=g.name or g.id) for g in sorted(sim.model.genes, key=lambda g: g.id)],
                graph=dict(nodes=nodes, links=links))


@app.get('/api/model')
def model() -> dict:
    return model_info()


@app.post('/api/intervention')
def intervention(scenario: Scenario) -> dict:
    sim = Simulator()
    disabled = sim.disabled_reactions(scenario.genes)
    return dict(disabled=[sim.reactions[i] for i in np.flatnonzero(disabled)])


@app.post('/api/simulate')
def simulate(scenario: Scenario) -> dict:
    return Simulator().simulate(scenario.glucose, scenario.oxygen, scenario.genes, ranges=True)


@app.post('/api/predict')
def predict(scenario: Scenario) -> dict:
    from bioflux.inference import predict as infer
    try:
        return infer(Simulator(), scenario.glucose, scenario.oxygen, scenario.genes)
    except (ValueError, OSError, KeyError) as error:
        raise HTTPException(status_code=503, detail='The local checkpoint is unavailable or does not match the model. Re-run training.') from error


@app.post('/api/envelope')
def envelope(scenario: Scenario) -> list[dict]:
    return Simulator().envelope(scenario.glucose, scenario.oxygen, scenario.genes)


def records(path):
    frame = pd.read_csv(path)
    return frame.astype(object).where(pd.notna(frame), None).to_dict('records')


@app.get('/api/results/{name}')
def results(name: ModelName) -> dict:
    run = ROOT / 'runs' / name
    if not (run / 'audit.json').exists():
        raise HTTPException(status_code=404, detail='No completed experiment is available for this reconstruction.')
    return dict(model=name, metrics=records(run / 'training/metrics.csv'),
                curves=records(run / 'search/curves.csv'), summary=records(run / 'search/summary.csv'),
                audit=read_json(run / 'audit.json'), model_manifest=read_json(ROOT / 'data/models' / f'{name}.manifest.json'))


@app.get('/api/findings/{name}')
def findings(name: ModelName):
    return FileResponse(ROOT / 'runs' / name / 'report/FINDINGS.md',
                        filename=f'BioFlux-{name}-FINDINGS.md', media_type='text/markdown')


# A built frontend and API share one origin; development uses Vite's local proxy.
frontend = ROOT / 'frontend/dist'
if frontend.is_dir():
    app.mount('/', StaticFiles(directory=frontend, html=True), name='frontend')
