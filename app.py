"""Run with: .venv/Scripts/python.exe -m streamlit run app.py"""
import json

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from bioflux.simulator import Simulator
from bioflux.storage import ROOT, read_json

st.set_page_config(page_title='BioFlux Lab', page_icon=None, layout='wide')
st.markdown('''<style>
.block-container {max-width: 1280px; padding-top: 2rem;}
h1,h2,h3 {color: #16313e; letter-spacing: -.02em;}
::selection {background: #b9ddd7; color: #16313e;}
button:focus-visible {outline: 2px solid #16645f; outline-offset: 3px;}
[data-testid="stMetricValue"] {font-variant-numeric: tabular-nums;}
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p {opacity: 1; color: #526873;}
</style>''', unsafe_allow_html=True)


@st.cache_data
def graph_positions(checksum):
    import networkx as nx
    sim = Simulator()
    graph = nx.Graph()
    graph.add_nodes_from(['m:' + m.id for m in sim.model.metabolites])
    graph.add_nodes_from(['r:' + r.id for r in sim.model.reactions])
    for reaction in sim.model.reactions:
        graph.add_edges_from(('r:' + reaction.id, 'm:' + m.id) for m in reaction.metabolites)
    positions = nx.spring_layout(graph, seed=41, iterations=80)
    return {key: value.tolist() for key, value in positions.items()}


def network_figure(sim, genes):
    positions = graph_positions(sim.model_sha256)
    mask = sim.disabled_reactions(genes)
    disabled = {sim.reactions[i] for i in np.flatnonzero(mask)}
    xs, ys = [], []
    for reaction in sim.model.reactions:
        for metabolite in reaction.metabolites:
            a, b = positions['r:' + reaction.id], positions['m:' + metabolite.id]
            xs.extend([a[0], b[0], None])
            ys.extend([a[1], b[1], None])
    fig = go.Figure(go.Scatter(x=xs, y=ys, mode='lines', line=dict(color='#bacbd1', width=0.7),
                               hoverinfo='skip', showlegend=False))
    for kind, ids, color, symbol, title in [
        ('m:', [m.id for m in sim.model.metabolites], '#7996aa', 'circle', 'Metabolite'),
        ('r:', sim.reactions, '#16645f', 'square', 'Reaction')]:
        fig.add_trace(go.Scatter(x=[positions[kind + i][0] for i in ids],
            y=[positions[kind + i][1] for i in ids], mode='markers', name=title,
            text=[i + (' · disabled by gene rule' if i in disabled else '') for i in ids],
            hovertemplate='%{text}<extra></extra>',
            marker=dict(size=8, symbol=symbol,
                        color=['#b37d24' if i in disabled else color for i in ids])))
    fig.update_layout(height=420, margin=dict(l=5, r=5, t=5, b=5),
        paper_bgcolor='#f6f8fa', plot_bgcolor='#f6f8fa',
        legend=dict(orientation='h', y=1.05),
        xaxis=dict(visible=False), yaxis=dict(visible=False))
    return fig


st.title('BioFlux Lab')
st.write('Explore a metabolic intervention. Compare a learned estimate with its feasible flux range.')
st.caption('Computational E. coli core model · Succinate · Simulation evidence only')
if not (ROOT / 'data/models/e_coli_core.json').exists():
    st.info('The model is not installed. Run `python -m bioflux.cli download` from the project environment, then reload.')
    st.stop()

sim = Simulator()
with st.sidebar:
    st.header('Experiment conditions')
    glucose = st.select_slider('Glucose uptake limit', options=[2, 4, 6, 8, 10, 12], value=10)
    oxygen = st.select_slider('Oxygen uptake limit', options=[0, 2, 10, 20], value=20)
    st.caption('Uptake limits: mmol/gDW/hour')
    genes = st.multiselect('Gene deletions', options=sim.genes, max_selections=2,
        format_func=lambda gene: f'{gene} · {sim.model.genes.get_by_id(gene).name or "unnamed"}')
    st.write('Minimum growth: **10% of unmodified growth** in this environment.')
    st.caption('Gene–reaction rules determine which reactions become unavailable. Deleting one isozyme may leave a reaction active.')

scenario_key = (glucose, oxygen, tuple(sorted(genes)))
if st.session_state.get('scenario_key') != scenario_key:
    for key in ['prediction', 'verification', 'envelope']:
        st.session_state.pop(key, None)
    st.session_state['scenario_key'] = scenario_key

lab, experiments, provenance = st.tabs(['Virtual laboratory', 'Research results', 'Sources & method'])
with lab:
    st.subheader('Intervention outcome')
    st.write('**' + (' + '.join(genes) if genes else 'Unmodified model') + '**' +
             f' · glucose ≤ {glucose} · oxygen ≤ {oxygen}')
    controls = st.columns(2)
    training_manifest = ROOT / 'runs/e_coli_core/training/manifest.json'
    trained = training_manifest.exists() and read_json(training_manifest).get('complete', False)
    if controls[0].button('Predict with graph ensemble', disabled=not trained, width='stretch'):
        from bioflux.inference import predict
        with st.spinner('Evaluating the local graph ensemble…'):
            try:
                st.session_state['prediction'] = predict(sim, glucose, oxygen, genes)
            except (ValueError, OSError, KeyError) as error:
                st.error(f'Prediction unavailable: {error}. Re-run training for the current model.')
    if controls[1].button('Verify with biochemical solver', type='primary', width='stretch'):
        with st.spinner('Solving growth and both ends of the production range…'):
            st.session_state['verification'] = sim.simulate(glucose, oxygen, genes, ranges=True)
    if not trained:
        st.info('The graph ensemble has not finished training. Solver verification is available.')
    prediction = st.session_state.get('prediction')
    verification = st.session_state.get('verification')
    if not prediction and not verification:
        st.info('Choose conditions and run a prediction or solver verification. Results appear here for the selected scenario.')
    comparison = []
    if prediction:
        comparison.append(dict(Source='Graph ensemble estimate', Growth=prediction['growth'],
             Minimum=prediction['product_min'], Maximum=prediction['product_max'],
             Feasibility=f'{prediction["feasibility_probability"]:.1%} predicted'))
        st.caption(f'Ensemble disagreement on minimum secretion: {prediction["product_min_std"]:.4f}; '
                   'not a calibrated confidence interval. Independent predictions may violate range ordering; verify before interpreting.')
    if verification:
        if verification['feasible']:
            st.success(f'Solver verified: growth constraint satisfied. '
                       f'{verification["solver_calls"]} LP optimizations, including environment setup.')
        else:
            st.warning(f'No verified feasible production range: {verification["status"]}. '
                       'Change the intervention or environment and verify again.')
        comparison.append(dict(Source='Solver verification', Growth=verification['growth'],
             Minimum=verification['product_min'], Maximum=verification['product_max'],
             Feasibility=verification['status']))
        st.caption(f'Unmodified growth: {verification["wildtype_growth"]:.4f}/hour; '
                   f'required growth: {verification["growth_requirement"]:.4f}/hour.'
                   if verification['growth_requirement'] is not None else 'The unmodified model cannot grow in this environment.')
    if comparison:
        st.dataframe(pd.DataFrame(comparison), hide_index=True, width='stretch')
        st.caption('Growth: maximum biomass flux, 1/hour. Minimum and maximum: feasible succinate secretion, mmol/gDW/hour, under the fixed growth floor.')
    left, right = st.columns([1.2, 1])
    with left:
        st.subheader('Metabolic graph')
        st.plotly_chart(network_figure(sim, genes), width='stretch', key='network')
        st.caption('Squares: reactions · Circles: metabolites · Amber: reactions disabled by the selected gene rules. Drag to pan; scroll to zoom.')
    with right:
        st.subheader('Growth–production trade-off')
        st.write('Minimum secretion describes what this constrained model must secrete. Maximum secretion describes what it could secrete.')
        if st.button('Calculate the trade-off curve', disabled=not verification or not verification['feasible']):
            with st.spinner('Solving 15 growth floors…'):
                st.session_state['envelope'] = sim.envelope(glucose, oxygen, genes)
        envelope = st.session_state.get('envelope')
        if envelope:
            table = pd.DataFrame(envelope)
            fig = go.Figure()
            for column, title, color in [('product_max', 'Potential maximum', '#7996aa'),
                                         ('product_min', 'Forced minimum', '#16645f')]:
                fig.add_trace(go.Scatter(x=table.growth_fraction, y=table[column], name=title,
                                         mode='lines+markers', line=dict(color=color)))
            fig.update_layout(xaxis_title='Fraction of unmodified maximum growth',
                              yaxis_title='Succinate, mmol/gDW/hour', height=300,
                              legend=dict(orientation='h', y=1.2), margin=dict(l=10, r=10, t=30, b=10))
            st.plotly_chart(fig, width='stretch', key='envelope')
            st.caption(f'{int(table.solver_calls.sum())} additional LP optimizations. Gaps indicate infeasible or failed solves.')
    if verification:
        st.download_button('Download this solver result', json.dumps(verification, indent=2),
                           file_name='bioflux-verification.json', mime='application/json')

with experiments:
    metrics_path = ROOT / 'runs/e_coli_core/training/metrics.csv'
    if metrics_path.exists():
        metrics = pd.read_csv(metrics_path)
        panel = st.radio('Generalization evaluation', ['environment', 'combination'], horizontal=True,
                         format_func=lambda value: 'Unseen nutrient conditions' if value == 'environment' else 'Unseen gene combinations')
        st.dataframe(metrics[metrics.panel == panel].drop(columns='panel'), hide_index=True, width='stretch')
        st.caption('Errors use held-out observed solver labels. R² and rank correlations can be undefined when outcomes are constant.')
    else:
        st.info('No completed predictive evaluation yet. Run the training command to populate this view.')
    curves_path = ROOT / 'runs/e_coli_core/search/curves.csv'
    if curves_path.exists():
        curves = pd.read_csv(curves_path)
        st.subheader('Discovery under a fixed online budget')
        st.line_chart(curves.groupby(['evaluations', 'method']).best_verified_minimum.mean().unstack(),
                      x_label='Candidate evaluations', y_label='Best verified minimum secretion')
        st.write('GNN search also pays for upstream training labels. Compare total LP calls before claiming efficiency.')
        st.dataframe(pd.read_csv(ROOT / 'runs/e_coli_core/search/summary.csv'), hide_index=True, width='stretch')
    findings = ROOT / 'runs/e_coli_core/report/FINDINGS.md'
    if findings.exists():
        st.download_button('Download the findings report', findings.read_text(encoding='utf-8'),
                           file_name='BioFlux-FINDINGS.md')

with provenance:
    st.subheader('A computational model, with explicit limits')
    st.write('Flux balance analysis assumes steady state and encoded constraints. It does not model all regulation, kinetics or evolutionary adaptation. These results are not experimental biological validation.')
    st.write('Deleting reactions shrinks the feasible space. It cannot improve maximum secretion under identical growth constraints. Discovery therefore measures minimum feasible secretion, with maximum secretion retained as a separate potential.')
    st.markdown('[BiGG Models](https://bigg.bio/) · [COBRApy documentation](https://cobrapy.readthedocs.io/)')
    st.json(read_json(ROOT / 'data/models/e_coli_core.manifest.json'), expanded=False)
    st.caption('All processing runs locally. No API keys, paid services or model downloads are required after setup.')
