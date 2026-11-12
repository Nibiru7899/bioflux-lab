export type Scenario = { glucose: number; oxygen: number; genes: string[] };
export type Node = { id: string; label: string; name: string; kind: string; x: number; y: number; degree: number };
export type Model = { id: string; organism: string; model_sha256: string; reactions: number; metabolites: number;
  genes: { id: string; name: string }[]; graph: { nodes: Node[]; links: { source: string; target: string }[] } };
export type Outcome = { growth: number | null; product_min: number | null; product_max: number | null;
  feasibility_probability?: number; product_min_std?: number; feasible?: boolean; status?: string;
  wildtype_growth?: number; growth_requirement?: number | null; solver_calls: number; growth_fraction?: number };
export type Row = Record<string, number | string | null>;
export type Results = { model: string; metrics: Row[]; curves: Row[]; summary: Row[];
  audit: { passed: boolean; scenarios: number; feasible: number; search_verifications: number };
  model_manifest: Record<string, unknown> };

export async function api<T>(path: string, body?: Scenario, signal?: AbortSignal): Promise<T> {
  const response = await fetch(`/api/${path}`, { signal, ...(body ? { method: 'POST',
    headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) } : {}) });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(typeof error.detail === 'string' ? error.detail : 'The local request failed. Check the API and try again.');
  }
  return response.json();
}

export function download(value: unknown, filename: string) {
  const url = URL.createObjectURL(new Blob([JSON.stringify(value, null, 2)], { type: 'application/json' }));
  const link = document.createElement('a'); link.href = url; link.download = filename; link.click();
  URL.revokeObjectURL(url);
}
