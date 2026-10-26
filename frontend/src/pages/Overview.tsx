import { useEffect, useState } from "react";
import { api } from "../api/client";
import { ChangeBadge } from "../components/StatusBadge";
import type { ChangeType, Health, ReportListItem } from "../types";

interface Props { onNavigate: (v: "compare" | "history") => void; onOpenReport: (id: string) => void }

export default function Overview({ onNavigate, onOpenReport }: Props) {
  const [health, setHealth] = useState<Health | null>(null);
  const [count, setCount] = useState<number | null>(null);
  const [latest, setLatest] = useState<ReportListItem | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const [h, o, r] = await Promise.all([api.health(), api.observations(), api.reports()]);
        if (!alive) return;
        setHealth(h); setCount(o.count); setLatest(r.reports[0] ?? null);
      } catch (e) { if (alive) setError(e instanceof Error ? e.message : "Backend unreachable."); }
    })();
    return () => { alive = false; };
  }, []);

  return (
    <div className="space-y-8">
      <header className="max-w-3xl">
        <h1 className="text-3xl font-semibold leading-tight">Visual Memory</h1>
        <p className="mt-1 text-lg text-mist-300">An uncertainty-aware spatial and temporal intelligence system for visual scene change detection.</p>
        <p className="mt-4 text-sm leading-relaxed text-mist-300">
          Compare two images of the same indoor space. A pretrained detector finds ten kinds of everyday objects, Hungarian assignment links them across the images,
          and each finding is classified as unchanged, possibly relocated, newly observed or not observed. When the evidence is weak the finding is marked uncertain, with the reasons listed.
          “Not observed” means the detector found no match; it does not mean an object was removed.
        </p>
        <button type="button" className="btn-primary mt-5" onClick={() => onNavigate("compare")}>Compare two images</button>
      </header>

      {error && <p role="alert" className="panel border-gone/40 p-4 text-sm text-gone">{error}</p>}

      <section className="grid gap-4 md:grid-cols-3" aria-label="Status">
        <div className="panel p-4">
          <p className="text-xs text-mist-500">Backend</p>
          <p className="mt-1 text-lg font-semibold">{health ? (health.detector.initialized ? "Detector loaded" : "Detector loads on first use") : error ? "Unreachable" : "Checking…"}</p>
          {health && <p className="mt-1 text-xs text-mist-500">Model {health.detector.model}{health.detector.error ? ` · ${health.detector.error}` : ""}</p>}
        </div>
        <div className="panel p-4">
          <p className="text-xs text-mist-500">Stored observations</p>
          <p className="mt-1 text-lg font-semibold tabular-nums">{count ?? "—"}</p>
          <button type="button" className="mt-1 text-xs text-accent hover:underline" onClick={() => onNavigate("history")}>Open history</button>
        </div>
        <div className="panel p-4">
          <p className="text-xs text-mist-500">Latest comparison</p>
          {latest ? (
            <>
              <p className="mt-1 text-lg font-semibold tabular-nums">{latest.summary.total} findings</p>
              <p className="text-xs text-mist-500">{latest.summary.uncertain} uncertain · {new Date(latest.created_at).toLocaleString()}</p>
              <button type="button" className="mt-1 text-xs text-accent hover:underline" onClick={() => onOpenReport(latest.report_id)}>Open report</button>
            </>
          ) : <p className="mt-1 text-sm text-mist-500">None yet. Run a comparison to create one.</p>}
        </div>
      </section>

      {latest && (
        <section className="panel p-4" aria-label="Latest summary">
          <p className="mb-3 text-sm font-semibold">{latest.reference_image} → {latest.later_image}</p>
          <div className="flex flex-wrap gap-4">
            {(Object.entries(latest.summary.by_change_type) as [ChangeType, number][]).map(([t, n]) => (
              <span key={t} className="flex items-center gap-2"><ChangeBadge type={t} /><span className="tabular-nums text-sm text-mist-300">{n}</span></span>
            ))}
            {latest.summary.total === 0 && <span className="text-sm text-mist-500">No findings.</span>}
          </div>
        </section>
      )}

      <section className="max-w-3xl text-sm leading-relaxed text-mist-300" aria-label="Limits">
        <h2 className="mb-2 text-base font-semibold text-mist-100">What to keep in mind</h2>
        <ul className="list-disc space-y-1 pl-5">
          <li>Detector confidence is a model score, not the probability that an object is identified correctly.</li>
          <li>A monitor may be labelled “tv”, and desks or specialised equipment may go undetected.</li>
          <li>Matching two detections does not prove they are the same physical object.</li>
        </ul>
      </section>
    </div>
  );
}
