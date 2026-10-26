import { useState } from "react";
import { Loader2, ScanSearch } from "lucide-react";
import clsx from "clsx";
import { api } from "../api/client";
import BaselineComparison from "../components/BaselineComparison";
import ComparisonView from "../components/ComparisonView";
import ExportPanel from "../components/ExportPanel";
import FindingsTable from "../components/FindingsTable";
import ImageUploader from "../components/ImageUploader";
import SpatialPanel from "../components/SpatialPanel";
import type { Report } from "../types";

type Tab = "comparison" | "findings" | "baseline" | "spatial" | "export";
const TABS: { id: Tab; label: string }[] = [
  { id: "comparison", label: "Annotated images" }, { id: "findings", label: "Findings" }, { id: "baseline", label: "Baseline" },
  { id: "spatial", label: "Spatial analysis" }, { id: "export", label: "Export" },
];

interface Props { report: Report | null; onReport: (r: Report) => void }

export default function Compare({ report, onReport }: Props) {
  const [ref, setRef] = useState<File | null>(null);
  const [later, setLater] = useState<File | null>(null);
  const [conf, setConf] = useState(0.25);
  const [align, setAlign] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab>("comparison");

  async function run() {
    if (!ref || !later) return;
    setLoading(true); setError(null);
    try {
      onReport(await api.compare(ref, later, { conf, align }));
      setTab("comparison");
    } catch (e) {
      setError(e instanceof Error ? e.message : "The comparison failed.");
    } finally { setLoading(false); }
  }

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-semibold">Compare two observations</h1>
        <p className="mt-1 max-w-2xl text-sm text-mist-300">Upload a reference image and a later image of the same scene, taken from a similar position. The backend detects supported objects, matches them across the images and reports candidate changes with the evidence behind each.</p>
      </header>

      <section aria-label="Inputs" className="space-y-4">
        <div className="grid gap-4 md:grid-cols-2">
          <ImageUploader label="Reference image" hint="Drop the earlier image here, or click to choose" file={ref} onChange={setRef} disabled={loading} />
          <ImageUploader label="Later image" hint="Drop the later image here, or click to choose" file={later} onChange={setLater} disabled={loading} />
        </div>
        <div className="panel flex flex-wrap items-end gap-x-8 gap-y-4 p-4">
          <label className="text-sm">
            <span className="mb-1 block text-mist-300">Detector confidence threshold: <span className="tabular-nums text-mist-100">{conf.toFixed(2)}</span></span>
            <input type="range" min={0.1} max={0.9} step={0.05} value={conf} disabled={loading} onChange={(e) => setConf(Number(e.target.value))} className="w-56 accent-[#8aa4ff]" />
          </label>
          <label className="flex items-center gap-2 text-sm text-mist-300">
            <input type="checkbox" checked={align} disabled={loading} onChange={(e) => setAlign(e.target.checked)} className="h-4 w-4 accent-[#8aa4ff]" />
            Align the reference to the later image (ORB + RANSAC)
          </label>
          <button type="button" className="btn-primary ml-auto" disabled={!ref || !later || loading} onClick={run}>
            {loading ? <Loader2 size={16} className="animate-spin" aria-hidden /> : <ScanSearch size={16} aria-hidden />}
            {loading ? "Analysing…" : "Run comparison"}
          </button>
        </div>
        {(!ref || !later) && !loading && <p className="text-xs text-mist-500">Choose both images to enable the comparison.</p>}
        {loading && <p role="status" className="text-sm text-mist-300">Running detection, alignment and matching. The first run loads the model and takes longer.</p>}
        {error && <p role="alert" className="panel border-gone/40 p-4 text-sm text-gone">{error}</p>}
      </section>

      {report && (
        <section aria-label="Results" className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3 border-t border-ink-700 pt-6">
            <h2 className="text-lg font-semibold">Results</h2>
            <p className="text-xs text-mist-500">{report.reference_image.filename} → {report.later_image.filename}</p>
          </div>
          <div role="tablist" aria-label="Result views" className="flex flex-wrap gap-1 border-b border-ink-700">
            {TABS.map((t) => (
              <button key={t.id} role="tab" aria-selected={tab === t.id} type="button" onClick={() => setTab(t.id)}
                      className={clsx("-mb-px border-b-2 px-3 py-2 text-sm", tab === t.id ? "border-accent text-mist-100" : "border-transparent text-mist-500 hover:text-mist-100")}>
                {t.label}{t.id === "findings" ? ` (${report.findings.length})` : ""}
              </button>
            ))}
          </div>
          <div role="tabpanel">
            {tab === "comparison" && <ComparisonView report={report} />}
            {tab === "findings" && <FindingsTable findings={report.findings} />}
            {tab === "baseline" && <BaselineComparison report={report} />}
            {tab === "spatial" && <SpatialPanel report={report} />}
            {tab === "export" && <ExportPanel report={report} />}
          </div>
        </section>
      )}
    </div>
  );
}
