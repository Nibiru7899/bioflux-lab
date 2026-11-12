import { lazy, Suspense, useEffect, useRef, useState } from 'react';
import { AnimatePresence, motion, useReducedMotion } from 'motion/react';
import { Activity, ArrowDownToLine, ArrowRight, Atom, Beaker, BookOpen, Check, CheckCircle2, ChevronRight, Cpu, Dna, FlaskConical, Info, Loader2, Menu, RotateCcw, ShieldCheck, SlidersHorizontal, Sparkles, X } from 'lucide-react';
import Network from './Network';
import { api, download, type Model, type Outcome, type Scenario } from './types';

const Research = lazy(() => import('./Research'));
const EnvelopeChart = lazy(() => import('./Charts').then(m => ({ default: m.EnvelopeChart })));
const DEFAULT: Scenario = { glucose: 10, oxygen: 20, genes: [] };
const ease = [0.23, 1, 0.32, 1] as const;
const fmt = (n: number | null | undefined) => n == null ? '—' : n.toFixed(4);

function Wordmark() { return <span className="wordmark"><span className="brand-mark"><Atom size={24} strokeWidth={1.5} /></span>BioFlux<span>Lab</span></span>; }

function Parameters({ model, scenario, change, close }: { model: Model; scenario: Scenario; change: (s: Scenario) => void; close: () => void }) {
  return <><div className="sidebar-title"><h2><SlidersHorizontal size={17} />Experiment conditions</h2><button className="icon-button mobile-only" aria-label="Close experiment conditions" onClick={close}><X size={20} /></button></div>
    <p className="sidebar-intro">Shape the environment.<br />Explore an intervention.</p>
    <div className="parameter"><label htmlFor="glucose">Glucose uptake <span>{scenario.glucose}<small>mmol/gDW/h</small></span></label>
      <input id="glucose" type="range" min="0" max="5" value={[2, 4, 6, 8, 10, 12].indexOf(scenario.glucose)} aria-valuetext={`${scenario.glucose} mmol per gram dry weight per hour`}
        onChange={e => change({ ...scenario, glucose: [2, 4, 6, 8, 10, 12][+e.target.value] })} />
      <div className="range-ticks"><span>2</span><span>12</span></div></div>
    <div className="parameter"><label htmlFor="oxygen">Oxygen uptake <span>{scenario.oxygen}<small>mmol/gDW/h</small></span></label>
      <input id="oxygen" type="range" min="0" max="3" value={[0, 2, 10, 20].indexOf(scenario.oxygen)} aria-valuetext={`${scenario.oxygen} mmol per gram dry weight per hour`}
        onChange={e => change({ ...scenario, oxygen: [0, 2, 10, 20][+e.target.value] })} />
      <div className="range-ticks"><span>Anaerobic · 0</span><span>20</span></div></div>
    <div className="parameter genes"><label htmlFor="gene">Gene deletions <small>{scenario.genes.length} / 2</small></label>
      <select id="gene" value="" disabled={scenario.genes.length === 2} onChange={e => { if (e.target.value) change({ ...scenario, genes: [...scenario.genes, e.target.value] }); }}>
        <option value="">Select a gene…</option>{model.genes.filter(g => !scenario.genes.includes(g.id)).map(g => <option key={g.id} value={g.id}>{g.id} · {g.name}</option>)}</select>
      <div className="gene-tags">{scenario.genes.map(id => <span key={id}>{id}<button aria-label={`Remove ${id}`} onClick={() => change({ ...scenario, genes: scenario.genes.filter(g => g !== id) })}><X size={13} /></button></span>)}</div>
      <p className="muted">Gene–reaction rules determine which reactions become unavailable.</p></div>
    <div className="growth-rule"><ShieldCheck size={20} /><div><strong>Keep the organism viable</strong><p>Growth floor: 10% of the unmodified maximum in this environment.</p></div></div>
    <button className="text-button reset" onClick={() => change(DEFAULT)}><RotateCcw size={14} />Reset conditions</button>
    <figure className="cell-study"><img src="/cell-study.png" alt="Conceptual illustration of translucent bacterial cells" /><figcaption><span>E. coli</span>Conceptual illustration · AI generated</figcaption></figure>
    <div className="local-note"><span className="status-dot" /><span>Runs on your machine<br /><small>No cloud inference</small></span></div>
  </>;
}

function Result({ prediction, verified, busy, error, run }: { prediction: Outcome | null; verified: Outcome | null; busy: string | null; error: string; run: (action: string) => void }) {
  const reduced = useReducedMotion();
  const outcome = verified || prediction;
  return <section className="outcome-panel" aria-label="Intervention results"><div className="section-title"><h2>Intervention outcome</h2><span className="subtle-tag">{verified ? 'Verified' : prediction ? 'Estimated' : 'Ready to explore'}</span></div>
    <p className="muted">Learned estimates. Solver-backed answers.</p>
    <div className="action-stack"><button className="button primary" disabled={!!busy} onClick={() => run('simulate')}>{busy === 'simulate' ? <Loader2 className="spin" size={17} /> : <ShieldCheck size={17} />}Verify with solver<ArrowRight size={16} /></button>
      <button className="button secondary" disabled={!!busy} onClick={() => run('predict')}>{busy === 'predict' ? <Loader2 className="spin" size={17} /> : <Sparkles size={16} />}Predict with graph ensemble</button></div>
    <div className="workflow" aria-label="Experiment progress"><span className={prediction ? 'done' : ''}><Cpu size={13} />Predict</span><ChevronRight size={13} /><span className={verified ? 'done' : ''}><Check size={13} />Verify</span><ChevronRight size={13} /><span className={prediction && verified ? 'done' : ''}><Activity size={13} />Compare</span></div>
    {error && <div role="alert" className="error-message">{error}</div>}
    <AnimatePresence mode="wait" initial={false}><motion.div key={verified ? 'verified' : prediction ? 'predicted' : 'empty'}
      initial={{ opacity: .25, transform: reduced ? 'none' : 'translateY(8px)' }} animate={{ opacity: 1, transform: 'translateY(0px)' }} exit={{ opacity: 0 }} transition={{ duration: .24, ease }}>
      {outcome ? <><div className={`result-status ${verified && !verified.feasible ? 'warning' : ''}`} role="status">
        {verified ? verified.feasible ? <CheckCircle2 size={17} /> : <Info size={17} /> : <Cpu size={17} />}
        <span>{verified ? verified.feasible ? 'Growth constraint satisfied' : `No feasible production range · ${verified.status}` : 'Graph ensemble estimate'}</span></div>
        <div className="result-values">{[['growth', 'Maximum growth', 'h⁻¹'], ['product_min', 'Forced minimum', 'mmol/gDW/h'], ['product_max', 'Potential maximum', 'mmol/gDW/h']].map(([key, label, unit]) => <div key={key}><span>{label}</span><strong>{fmt(outcome[key as 'growth'])}<small>{unit}</small></strong></div>)}</div>
        {verified ? <p className="muted result-foot">{verified.solver_calls} LP optimizations, including setup.<br />{verified.growth_requirement != null ? `Required growth: ${fmt(verified.growth_requirement)} h⁻¹.` : 'Unmodified growth is unavailable in this environment.'}</p> : <p className="muted result-foot">{((prediction?.feasibility_probability || 0) * 100).toFixed(1)}% predicted feasibility. Ensemble disagreement: {fmt(prediction?.product_min_std)}. Not a calibrated interval; verify before interpreting.</p>}
      </> : <div className="empty-outcome"><FlaskConical size={27} strokeWidth={1.3} /><h3>Your next experiment starts here.</h3><p>Choose an environment and up to two deletions. Verify the feasible production range, or first ask the graph ensemble for an estimate.</p><div className="empty-values"><span>Growth</span><span>Minimum</span><span>Maximum</span><b>—</b><b>—</b><b>—</b></div></div>}
    </motion.div></AnimatePresence>
    {verified && prediction && <details className="comparison"><summary>Compare prediction and verification</summary><div className="table-scroll"><table><thead><tr><th>Source</th><th>Growth</th><th>Min.</th><th>Max.</th></tr></thead><tbody>{[['Prediction', prediction], ['Solver', verified]].map(([name, result]) => { const r = result as Outcome; return <tr key={String(name)}><th>{String(name)}</th><td>{fmt(r.growth)}</td><td>{fmt(r.product_min)}</td><td>{fmt(r.product_max)}</td></tr>; })}</tbody></table></div><p className="muted">Growth: h⁻¹. Secretion: mmol/gDW/h.</p></details>}
    {verified && <button className="text-button download" onClick={() => download(verified, 'bioflux-verification.json')}><ArrowDownToLine size={14} />Download solver result</button>}
  </section>;
}

function Method({ model }: { model: Model }) { return <div className="method-page"><div className="page-heading"><h1>Evidence comes first.</h1><p>What this laboratory measures, and where its answers stop.</p></div><div className="method-grid"><article><ShieldCheck size={25} /><h2>A model of metabolism</h2><p>Flux balance analysis assumes steady state and encoded reaction constraints. It does not capture all regulation, kinetics or adaptation. A feasible simulation is not experimental biological validation.</p><h2>Minimum is not maximum</h2><p>Maximum secretion describes what the constrained model could produce. Minimum secretion describes what it must secrete across feasible solutions. Discovery ranks improvements in that minimum while preserving the same growth floor.</p><h2>Predictions need verification</h2><p>The three-member graph ensemble estimates growth, production endpoints and feasibility. Disagreement is not calibrated uncertainty, and independently predicted endpoints can violate range ordering. The solver is the verification step.</p></article><aside><h2>Source identity</h2><dl><div><dt>Reconstruction</dt><dd>E. coli core · BiGG Models</dd></div><div><dt>Growth requirement</dt><dd>10% of environment-specific WT maximum</dd></div><div><dt>Model SHA-256</dt><dd className="checksum">{model.model_sha256}</dd></div><div><dt>Data permission</dt><dd>BiGG educational, research and nonprofit terms; publisher notice retained.</dd></div></dl><a href="https://bigg.ucsd.edu/about" target="_blank" rel="noreferrer">BiGG source and terms <ArrowRight size={14} /></a><a href="https://cobrapy.readthedocs.io/" target="_blank" rel="noreferrer">COBRApy documentation <ArrowRight size={14} /></a><p className="muted">The cell artwork is an AI-generated conceptual illustration. It is not microscopy or experiment evidence.</p></aside></div></div>; }

export default function App() {
  const [model, setModel] = useState<Model | null>(null);
  const [startupError, setStartupError] = useState('');
  const [page, setPage] = useState('lab');
  const [scenario, setScenario] = useState<Scenario>(DEFAULT);
  const [disabled, setDisabled] = useState<string[]>([]);
  const [graphError, setGraphError] = useState('');
  const [prediction, setPrediction] = useState<Outcome | null>(null);
  const [verified, setVerified] = useState<Outcome | null>(null);
  const [envelope, setEnvelope] = useState<Outcome[] | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState('');
  const [mobile, setMobile] = useState(false);
  const menuButton = useRef<HTMLButtonElement>(null);
  const sidebar = useRef<HTMLElement>(null);
  const request = useRef<AbortController | null>(null);
  const version = useRef(0);
  useEffect(() => { const controller = new AbortController(); api<Model>('model', undefined, controller.signal).then(setModel).catch(e => { if (!controller.signal.aborted) setStartupError(e.message); }); return () => { controller.abort(); request.current?.abort(); }; }, []);
  useEffect(() => {
    if (!mobile) return;
    const previous = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    const elements = () => Array.from(sidebar.current?.querySelectorAll<HTMLElement>('button:not(:disabled), select:not(:disabled), input') || []);
    elements()[0]?.focus();
    function keydown(e: KeyboardEvent) {
      if (e.key === 'Escape') { setMobile(false); return; }
      if (e.key !== 'Tab') return;
      const items = elements(); const first = items[0]; const last = items.at(-1);
      if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last?.focus(); }
      if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first?.focus(); }
    }
    document.addEventListener('keydown', keydown);
    return () => { document.body.style.overflow = previous; document.removeEventListener('keydown', keydown); menuButton.current?.focus(); };
  }, [mobile]);
  useEffect(() => { const controller = new AbortController(); setGraphError(''); setDisabled([]);
    api<{ disabled: string[] }>('intervention', scenario, controller.signal).then(r => { if (!controller.signal.aborted) setDisabled(r.disabled); }).catch(() => { if (!controller.signal.aborted) setGraphError('Reaction highlighting is unavailable. Try changing the intervention again.'); });
    return () => controller.abort(); }, [scenario]);
  function change(s: Scenario) { version.current++; request.current?.abort(); setScenario(s); setPrediction(null); setVerified(null); setEnvelope(null); setError(''); setBusy(null); }
  async function run(action: string) {
    request.current?.abort(); const controller = new AbortController(); request.current = controller;
    const current = version.current; setBusy(action); setError('');
    try { const result = await api<Outcome | Outcome[]>(action, scenario, controller.signal);
      if (controller.signal.aborted || current !== version.current) return;
      if (action === 'predict') setPrediction(result as Outcome); else if (action === 'simulate') setVerified(result as Outcome); else setEnvelope(result as Outcome[]);
    } catch (e) { if (!controller.signal.aborted && current === version.current) setError(e instanceof Error ? e.message : 'The operation failed. Please try again.'); }
    finally { if (!controller.signal.aborted && current === version.current) setBusy(null); }
  }
  if (!model) return <div className="startup"><Wordmark />{startupError ? <><h1>The local API is unavailable.</h1><p role="alert">{startupError}</p><p>Start the server with <code>python -m uvicorn bioflux.server:app --host 127.0.0.1 --port 8000</code>, then retry.</p><button className="button primary" onClick={() => location.reload()}>Retry connection</button></> : <><Loader2 className="spin" /><p>Opening your metabolic laboratory…</p></>}</div>;
  return <><a href="#workspace" className="skip-link">Skip to laboratory</a><header className="topbar"><a className="brand-link" href="#" aria-label="BioFlux Lab home" onClick={e => { e.preventDefault(); setPage('lab'); }}><Wordmark /></a>
    <nav aria-label="Main navigation">{[['lab', 'Laboratory', Beaker], ['research', 'Research results', Activity], ['method', 'Sources & method', BookOpen]].map(([id, title, Icon]) => { const NavIcon = Icon as typeof Beaker; return <button key={String(id)} className={page === id ? 'active' : ''} aria-current={page === id ? 'page' : undefined} onClick={() => setPage(String(id))}><NavIcon size={16} /><span>{String(title)}</span></button>; })}</nav>
    <div className="top-status"><span className="status-dot" />Local workspace</div><button ref={menuButton} className="icon-button mobile-only" onClick={() => setMobile(!mobile)} aria-label="Open experiment conditions" aria-expanded={mobile}><Menu size={22} /></button></header>
    {mobile && <button className="sidebar-scrim" aria-label="Close experiment conditions" onClick={() => setMobile(false)} />}
    <aside ref={sidebar} className={`sidebar ${mobile ? 'open' : ''}`} aria-label="Experiment parameters"><Parameters model={model} scenario={scenario} change={change} close={() => setMobile(false)} /></aside>
    <main id="workspace" inert={mobile}><div className="workspace-path"><span>Workspace</span><ChevronRight size={12} /><strong>{page === 'lab' ? 'Virtual laboratory' : page === 'research' ? 'Research results' : 'Sources & method'}</strong></div>
      {page === 'lab' ? <><div className="page-heading"><div><h1>Explore the possibilities.<br /><span>Respect the constraints.</span></h1><p>A computational laboratory for metabolic intervention discovery.</p></div><div className="organism-label"><Dna size={20} /><div><strong>Escherichia coli</strong><span>Core reconstruction · Succinate</span></div></div></div>
        <div className="scenario-bar"><span className="scenario-name"><FlaskConical size={16} />{scenario.genes.length ? scenario.genes.join(' + ') : 'Unmodified model'}</span><span>Glucose <b>≤ {scenario.glucose}</b></span><span>Oxygen <b>≤ {scenario.oxygen}</b></span><span className="simulation-tag"><Info size={13} />Simulation evidence only</span></div>
        {graphError && <p role="alert" className="error-message">{graphError}</p>}
        <div className="lab-grid"><Network model={model} disabled={disabled} /><Result prediction={prediction} verified={verified} busy={busy} error={error} run={run} /></div>
        <section className="tradeoff"><div className="tradeoff-copy"><span className="section-icon"><Activity size={21} /></span><h2>Growth meets production.</h2><p>See how the feasible succinate range changes as more resources are reserved for growth.</p><p className="muted">Minimum: what the model must secrete.<br />Maximum: what it could secrete.</p><button className="button secondary" disabled={!!busy || !verified?.feasible} onClick={() => run('envelope')}>{busy === 'envelope' ? <Loader2 className="spin" size={15} /> : <Activity size={15} />}Calculate trade-off curve</button>{!verified?.feasible && <p className="muted">Verify a feasible scenario to unlock this analysis.</p>}</div>
          <div className="tradeoff-chart">{envelope ? <><Suspense fallback={<div className="chart-loading">Loading visualization…</div>}><EnvelopeChart rows={envelope} /></Suspense><details><summary>Inspect the 15 solved growth floors</summary><div className="table-scroll"><table><thead><tr><th>Growth floor</th><th>Minimum</th><th>Maximum</th><th>Status</th></tr></thead><tbody>{envelope.map((r, i) => <tr key={i}><td>{((r.growth_fraction || 0) * 100).toFixed(0)}%</td><td>{fmt(r.product_min)}</td><td>{fmt(r.product_max)}</td><td>{r.status}</td></tr>)}</tbody></table></div></details><p className="muted">{envelope.reduce((s, r) => s + r.solver_calls, 0)} additional LP optimizations. Gaps represent failed or infeasible solves.</p></> : <div className="empty-chart"><svg viewBox="0 0 150 70" aria-hidden="true"><path d="M12 8v50h125" fill="none" stroke="currentColor" strokeWidth="1" /><path d="M20 18c30 0 50 6 65 17s20 12 40 17M20 53h105" fill="none" stroke="currentColor" strokeWidth="2" strokeDasharray="4 4" /></svg><strong>A range, not a promise.</strong><p>Your verified growth–production curve will appear here.</p><span>Illustrative placeholder · no simulated values</span></div>}</div></section>
      </> : page === 'research' ? <Suspense fallback={<div className="chart-loading">Opening recorded experiments…</div>}><Research /></Suspense> : <Method model={model} />}
      <footer><span><ShieldCheck size={14} />Solver verification precedes claims.</span><span>BioFlux Lab · Computational research prototype</span></footer>
    </main></>;
}
