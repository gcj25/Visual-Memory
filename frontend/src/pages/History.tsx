import { useCallback, useEffect, useState } from "react";
import { RefreshCw } from "lucide-react";
import { api, assetUrl } from "../api/client";
import type { ObservationSummary } from "../types";

export default function History({ onOpenReport }: { onOpenReport: (id: string) => void }) {
  const [items, setItems] = useState<ObservationSummary[] | null>(null);
  const [warnings, setWarnings] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [sel, setSel] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try { const r = await api.observations(); setItems(r.observations); setWarnings(r.warnings); }
    catch (e) { setError(e instanceof Error ? e.message : "Could not load history."); }
  }, []);
  useEffect(() => { void load(); }, [load]);

  const current = items?.find((o) => o.observation_id === sel) ?? null;

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold">Observation history</h1>
          <p className="mt-1 max-w-2xl text-sm text-mist-300">Every comparison stores its images’ detections locally as JSON. Records persist between restarts.</p>
        </div>
        <button type="button" className="btn-quiet" onClick={() => void load()}><RefreshCw size={16} aria-hidden /> Refresh</button>
      </header>
      {error && <p role="alert" className="panel border-gone/40 p-4 text-sm text-gone">{error}</p>}
      {warnings.length > 0 && <ul role="status" className="panel border-moved/30 p-4 text-sm text-moved">{warnings.map((w) => <li key={w}>{w}</li>)}</ul>}
      {items === null && !error && <p className="text-sm text-mist-500">Loading…</p>}
      {items?.length === 0 && <p className="panel p-6 text-sm text-mist-300">No observations stored yet. Run a comparison and its images will appear here.</p>}
      {items && items.length > 0 && (
        <div className="grid gap-4 lg:grid-cols-[1fr_22rem]">
          <ul className="panel divide-y divide-ink-700">
            {items.map((o) => (
              <li key={o.observation_id}>
                <button type="button" onClick={() => setSel(o.observation_id)} aria-pressed={sel === o.observation_id}
                        className={`flex w-full items-center justify-between gap-3 p-3 text-left text-sm hover:bg-ink-700/40 ${sel === o.observation_id ? "bg-ink-700/60" : ""}`}>
                  <span className="min-w-0">
                    <span className="block truncate font-medium">{o.image?.filename ?? o.observation_id}</span>
                    <span className="block text-xs text-mist-500">{new Date(o.timestamp).toLocaleString()} · {o.role}</span>
                  </span>
                  <span className="shrink-0 text-xs tabular-nums text-mist-300">{o.detection_count} detection{o.detection_count === 1 ? "" : "s"}</span>
                </button>
              </li>
            ))}
          </ul>
          <aside className="panel p-4 text-sm" aria-live="polite">
            {!current ? <p className="text-mist-500">Select an observation to see its stored details.</p> : (
              <div className="space-y-3">
                {current.image?.stored_file && <img src={assetUrl(`/api/images/${current.image.stored_file}`)} alt={`Stored image ${current.image.filename}`} className="w-full rounded bg-ink-900" />}
                <dl className="space-y-1 text-mist-300">
                  <div><dt className="inline text-mist-500">Observation </dt><dd className="inline font-mono text-xs">{current.observation_id}</dd></div>
                  <div><dt className="inline text-mist-500">Image </dt><dd className="inline font-mono text-xs">{current.image?.image_id}</dd></div>
                  <div><dt className="inline text-mist-500">Size </dt><dd className="inline">{current.image?.width} × {current.image?.height}</dd></div>
                  <div><dt className="inline text-mist-500">Recorded </dt><dd className="inline">{new Date(current.timestamp).toLocaleString()}</dd></div>
                </dl>
                {current.comparison ? (
                  <div>
                    <p className="text-mist-300">Compared with a reference: {current.comparison.summary.total} findings, {current.comparison.summary.uncertain} uncertain.</p>
                    <button type="button" className="btn-quiet mt-2" onClick={() => onOpenReport(current.comparison!.report_id)}>Open this report</button>
                  </div>
                ) : <p className="text-mist-500">No comparison is attached to this observation.</p>}
              </div>
            )}
          </aside>
        </div>
      )}
    </div>
  );
}
