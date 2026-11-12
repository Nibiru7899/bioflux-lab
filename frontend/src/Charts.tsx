import { useEffect, useRef } from 'react';
import { init, use, type EChartsCoreOption } from 'echarts/core';
import { LineChart, BarChart } from 'echarts/charts';
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components';
import { SVGRenderer } from 'echarts/renderers';
import { useReducedMotion } from 'motion/react';
import type { Outcome, Row } from './types';

use([LineChart, BarChart, GridComponent, TooltipComponent, LegendComponent, SVGRenderer]);
const colors = ['#748fa8', '#886f9f', '#bd784e', '#177764'];
const methods = ['random', 'greedy', 'tree', 'gnn'];
const labels = ['Random', 'Local greedy', 'Tree search', 'Graph ensemble'];

function Chart({ option, label }: { option: EChartsCoreOption; label: string }) {
  const element = useRef<HTMLDivElement>(null);
  const reduced = useReducedMotion();
  useEffect(() => {
    if (!element.current) return;
    const chart = init(element.current, undefined, { renderer: 'svg' });
    chart.setOption({ ...option, animation: !reduced, animationDuration: 240, animationDurationUpdate: 180, animationEasing: 'cubicOut' });
    const resize = new ResizeObserver(() => chart.resize()); resize.observe(element.current);
    return () => { resize.disconnect(); chart.dispose(); };
  }, [option, reduced]);
  return <div ref={element} className="chart" role="img" aria-label={label} />;
}

const base = { color: colors, textStyle: { fontFamily: 'Manrope, sans-serif', color: '#526977', fontSize: 11 },
  grid: { left: 58, right: 24, top: 72, bottom: 52 },
  tooltip: { trigger: 'axis', backgroundColor: '#fff', borderColor: '#dce5e7', textStyle: { color: '#203647' },
    valueFormatter: (value: number) => Number.isFinite(value) ? value.toFixed(5) : 'Unavailable' },
  legend: { top: 0, left: 8, itemWidth: 15, itemHeight: 8, textStyle: { color: '#526977', fontSize: 11 } } };

export function EnvelopeChart({ rows }: { rows: Outcome[] }) {
  const option = { ...base, color: ['#177764', '#748fa8'],
    xAxis: { type: 'value', min: 0, max: 1, name: 'Required growth / unmodified maximum', nameLocation: 'middle', nameGap: 34, axisLabel: { formatter: (v: number) => `${Math.round(v * 100)}%` }, splitLine: { show: false } },
    yAxis: { type: 'value', name: 'mmol/gDW/h', splitLine: { lineStyle: { color: '#e7eded' } } },
    series: [['product_min', 'Forced minimum'], ['product_max', 'Potential maximum']].map(([key, name]) => ({
      name, type: 'line', connectNulls: false, symbolSize: 5, lineStyle: { width: 2.5 },
      data: rows.map(r => [r.growth_fraction, r[key as 'product_min' | 'product_max']]),
    })) };
  return <Chart option={option} label="Succinate minimum and maximum secretion across fifteen growth requirements. Exact values are in the table below." />;
}

export function DiscoveryChart({ rows, cost }: { rows: Row[]; cost: boolean }) {
  const series = methods.map((method, i) => {
    const grouped = new Map<number, Row[]>();
    rows.filter(r => r.method === method).forEach(r => { const n = Number(r.evaluations); grouped.set(n, [...(grouped.get(n) || []), r]); });
    return { name: labels[i], type: 'line', showSymbol: false, lineStyle: { width: 2.5, type: i === 0 ? 'dashed' : 'solid' },
      data: [...grouped].sort(([a], [b]) => a - b).map(([n, group]) => [cost ? group.reduce((sum, r) => sum + Number(r.total_solver_calls), 0) / group.length : n,
        group.reduce((sum, r) => sum + Number(r.best_gain_over_wildtype), 0) / group.length]) };
  });
  const option = { ...base,
    xAxis: { type: cost ? 'log' : 'value', name: cost ? 'Total LP solves · includes pretraining' : 'Verified candidate evaluations', nameLocation: 'middle', nameGap: 34, splitLine: { show: false } },
    yAxis: { type: 'value', name: 'Gain · mmol/gDW/h', splitLine: { lineStyle: { color: '#e7eded' } } }, series };
  return <Chart option={option} label="Mean verified secretion gain over the unmodified control by search method. Recorded numeric summaries are in the table below." />;
}

export function ErrorChart({ rows, metric }: { rows: Row[]; metric: string }) {
  const sorted = [...rows].sort((a, b) => Number(b[metric]) - Number(a[metric]));
  const option = { ...base, grid: { left: 65, right: 65, top: 20, bottom: 45 }, legend: { show: false },
    xAxis: { type: 'value', name: 'Mean absolute error · lower is better', nameLocation: 'middle', nameGap: 30, splitLine: { lineStyle: { color: '#e7eded' } } },
    yAxis: { type: 'category', data: sorted.map(r => String(r.model).toUpperCase()), axisLine: { show: false }, axisTick: { show: false } },
    series: [{ type: 'bar', barWidth: 15, label: { show: true, position: 'right', formatter: (p: { value: number }) => p.value.toFixed(4), color: '#526977' },
      data: sorted.map(r => ({ value: r[metric], itemStyle: { color: r.model === 'gnn' ? '#177764' : '#9bb1bf', borderRadius: [0, 3, 3, 0] } })) }] };
  return <Chart option={option} label="Held-out predictive mean absolute error by model. Exact metrics are in the table below." />;
}
