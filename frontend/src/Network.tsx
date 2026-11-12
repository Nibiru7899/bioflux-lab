import { memo, useMemo, useRef, useState } from 'react';
import { Focus, Minus, Plus, ScanLine } from 'lucide-react';
import type { Model, Node } from './types';

export default memo(function Network({ model, disabled }: { model: Model; disabled: string[] }) {
  const [focus, setFocus] = useState(false);
  const [pointerNode, setPointerNode] = useState<Node | null>(null);
  const [selectedNode, setSelectedNode] = useState<Node | null>(null);
  const hovered = pointerNode || selectedNode;
  const [view, setView] = useState({ scale: 1, x: 0, y: 0 });
  const drag = useRef<{ x: number; y: number; vx: number; vy: number } | null>(null);
  const svg = useRef<SVGSVGElement>(null);
  const disabledSet = useMemo(() => new Set(disabled.map(id => 'r:' + id)), [disabled]);
  const { nodes, links, byId, neighborhood } = useMemo(() => {
    const byId = new Map(model.graph.nodes.map(n => [n.id, n]));
    const neighborhood = new Set(['m:succ_c', 'm:succ_e']);
    model.graph.links.forEach(l => { if (l.target.startsWith('m:succ_')) neighborhood.add(l.source); });
    model.graph.links.forEach(l => { if (neighborhood.has(l.source)) neighborhood.add(l.target); });
    return { ...model.graph, byId, neighborhood };
  }, [model]);
  const visibleNodes = focus ? nodes.filter(n => neighborhood.has(n.id)) : nodes;
  const visibleLinks = focus ? links.filter(l => neighborhood.has(l.source) && neighborhood.has(l.target)) : links;
  const linked = new Set(hovered ? links.filter(l => l.source === hovered.id || l.target === hovered.id).flatMap(l => [l.source, l.target]) : []);
  const bounds = { minX: Math.min(...visibleNodes.map(n => n.x)), maxX: Math.max(...visibleNodes.map(n => n.x)),
    minY: Math.min(...visibleNodes.map(n => n.y)), maxY: Math.max(...visibleNodes.map(n => n.y)) };
  const point = (n: Node) => [60 + (n.x - bounds.minX) / (bounds.maxX - bounds.minX || 1) * 720,
    55 + (n.y - bounds.minY) / (bounds.maxY - bounds.minY || 1) * 355];
  const color = (n: Node) => disabledSet.has(n.id) ? '#f29c86' : n.label.startsWith('succ_') ? '#e7c087' : n.kind === 'reaction' ? '#9bd9c9' : '#87a8c8';
  const reset = () => setView({ scale: 1, x: 0, y: 0 });
  return <section className="network-panel" aria-label="Interactive metabolic network">
    <div className="network-head"><div><h2>Metabolic network</h2><p>{model.reactions} reactions <span>·</span> {model.metabolites} metabolites</p></div><ScanLine size={21} aria-hidden="true" /></div>
    <div className="network-toolbar"><div className="segmented dark" aria-label="Network scope">
      <button aria-pressed={!focus} onClick={() => { setFocus(false); reset(); }}>Whole network</button>
      <button aria-pressed={focus} onClick={() => { setFocus(true); reset(); }}>Succinate neighborhood</button>
    </div><span className="graph-hint">Drag to explore</span></div>
    <svg ref={svg} viewBox="0 0 840 470" className="network-svg" role="img" aria-label={`${focus ? 'Succinate neighborhood' : 'Core metabolic network'}; ${disabled.length} reactions disabled. Connectivity, not measured flux.`}
      onPointerDown={e => { if (e.button !== 0) return; e.currentTarget.setPointerCapture(e.pointerId); drag.current = { x: e.clientX, y: e.clientY, vx: view.x, vy: view.y }; }}
      onPointerMove={e => { if (!drag.current || !svg.current) return; const ratio = 840 / svg.current.getBoundingClientRect().width;
        setView(v => ({ ...v, x: drag.current!.vx + (e.clientX - drag.current!.x) * ratio, y: drag.current!.vy + (e.clientY - drag.current!.y) * ratio })); }}
      onPointerUp={() => { drag.current = null; }} onPointerCancel={() => { drag.current = null; }}>
      <title>E. coli core stoichiometric connectivity</title>
      <g transform={`translate(${view.x} ${view.y}) translate(420 235) scale(${view.scale}) translate(-420 -235)`}>
        {visibleLinks.map((l, i) => { const a = point(byId.get(l.source)!); const b = point(byId.get(l.target)!);
          const active = hovered && (l.source === hovered.id || l.target === hovered.id);
          const target = l.target.startsWith('m:succ_');
          return <line key={i} x1={a[0]} y1={a[1]} x2={b[0]} y2={b[1]} stroke={active ? '#d1ece3' : target ? '#bd9e73' : '#3c566d'}
            strokeWidth={active ? 1.8 : target ? 1.3 : .7} className="network-link" opacity={hovered && !active ? .15 : .8} />; })}
        {visibleNodes.map(n => { const [x, y] = point(n); const special = n.label.startsWith('succ_'); const off = disabledSet.has(n.id);
          return <g key={n.id} onPointerEnter={() => { if (!drag.current) setPointerNode(n); }} onPointerLeave={() => setPointerNode(null)}
            className="network-node" opacity={hovered && !linked.has(n.id) ? .28 : 1}>
            <title>{n.label}: {n.name}{off ? ' — disabled by selected gene rules' : ''}</title>
            {n.kind === 'reaction' ? <rect x={x - 3.8} y={y - 3.8} width={7.6} height={7.6} rx="1.3" fill={color(n)} stroke={off ? '#ffcebe' : '#101f30'} /> :
              <circle cx={x} cy={y} r={special ? 7 : 3.3} fill={color(n)} stroke={special ? '#ffe3b8' : '#101f30'} strokeWidth={special ? 1.5 : 1} />}
            {special && <><line x1={x} y1={y + (n.label === 'succ_c' ? 11 : -11)} x2={x} y2={y + (n.label === 'succ_c' ? 28 : -28)} stroke="#e7c087" strokeWidth=".8" />
              <text x={x} y={y + (n.label === 'succ_c' ? 40 : -34)} textAnchor="middle" fill="#f3d7af" fontSize="11" paintOrder="stroke" stroke="#101f30" strokeWidth="4">{n.label === 'succ_c' ? 'Succinate · cytosol' : 'Succinate · extracellular'}</text></>}
          </g>; })}
      </g>
    </svg>
    <div className="graph-inspect"><div aria-live="polite">{hovered ? <><strong>{hovered.label}</strong><span>{hovered.name}</span></> : <><strong>{disabled.length ? `${disabled.length} disabled reactions` : 'An interconnected system'}</strong><span>Hover a node to inspect its identity and connections.</span></>}</div>
      <select aria-label="Inspect a network node" value={selectedNode?.id || ''} onChange={e => setSelectedNode(byId.get(e.target.value) || null)}><option value="">Inspect a node…</option>{visibleNodes.map(n => <option value={n.id} key={n.id}>{n.label} · {n.name}</option>)}</select></div>
    <div className="network-bottom"><div className="legend"><span><i className="dot metabolite" />Metabolite</span><span><i className="square reaction" />Reaction</span><span><i className="dot target" />Succinate</span>{disabled.length > 0 && <span><i className="square disabled" />Disabled</span>}</div>
      <div className="zoom-controls"><button aria-label="Zoom out" onClick={() => setView(v => ({ ...v, scale: Math.max(.65, v.scale - .2) }))}><Minus size={15} /></button>
        <button aria-label="Reset network view" onClick={reset}><Focus size={15} /></button>
        <button aria-label="Zoom in" onClick={() => setView(v => ({ ...v, scale: Math.min(3, v.scale + .2) }))}><Plus size={15} /></button></div></div>
    <p className="network-note">Connections show model topology, not measured flux. Node positions are for visualization.</p>
  </section>;
});
