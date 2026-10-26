import { Fragment, useMemo, useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";
import type { ChangeType, Detection, Finding, Status } from "../types";
import { CHANGE_LABEL, ChangeBadge, StatusBadge } from "./StatusBadge";

const fmtBox = (d: Detection | null) => (d ? `[${d.bbox.map((v) => Math.round(v)).join(", ")}]` : "—");
const fmt = (v: number | null | undefined, digits = 2) => (v === null || v === undefined ? "—" : v.toFixed(digits));

export default function FindingsTable({ findings }: { findings: Finding[] }) {
  const [type, setType] = useState<ChangeType | "all">("all");
  const [status, setStatus] = useState<Status | "all">("all");
  const [cls, setCls] = useState("all");
  const [open, setOpen] = useState<string | null>(null);

  const classes = useMemo(() => Array.from(new Set(findings.map((f) => f.class_name))).sort(), [findings]);
  const rows = findings.filter((f) => (type === "all" || f.change_type === type) && (status === "all" || f.status === status) && (cls === "all" || f.class_name === cls));

  if (findings.length === 0) return <p className="panel p-6 text-sm text-mist-300">No findings: neither image contained a supported object, or none could be compared.</p>;

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-3 text-sm">
        <label className="flex items-center gap-2 text-mist-300">Change
          <select className="field" value={type} onChange={(e) => setType(e.target.value as ChangeType | "all")}>
            <option value="all">All</option>
            {(Object.keys(CHANGE_LABEL) as ChangeType[]).map((t) => <option key={t} value={t}>{CHANGE_LABEL[t]}</option>)}
          </select>
        </label>
        <label className="flex items-center gap-2 text-mist-300">Status
          <select className="field" value={status} onChange={(e) => setStatus(e.target.value as Status | "all")}>
            <option value="all">All</option><option value="supported">Supported</option><option value="uncertain">Uncertain</option>
          </select>
        </label>
        <label className="flex items-center gap-2 text-mist-300">Class
          <select className="field" value={cls} onChange={(e) => setCls(e.target.value)}>
            <option value="all">All</option>{classes.map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
        </label>
        <span className="self-center text-xs text-mist-500">{rows.length} of {findings.length} shown</span>
      </div>

      <div className="panel overflow-x-auto">
        <table className="w-full min-w-[820px] text-left text-sm">
          <thead className="border-b border-ink-700 text-xs text-mist-500">
            <tr>
              <th className="w-8 p-3"><span className="sr-only">Details</span></th>
              <th className="p-3 font-medium">Class</th><th className="p-3 font-medium">Change</th><th className="p-3 font-medium">Status</th>
              <th className="p-3 font-medium">Detector score (ref / later)</th><th className="p-3 font-medium">Match cost</th>
              <th className="p-3 font-medium">Displacement</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((f) => {
              const isOpen = open === f.finding_id;
              return (
                <Fragment key={f.finding_id}>
                  <tr className="border-b border-ink-700/70 align-top hover:bg-ink-700/30">
                    <td className="p-3">
                      <button type="button" aria-expanded={isOpen} aria-label={`${isOpen ? "Hide" : "Show"} evidence for ${f.finding_id}`}
                              onClick={() => setOpen(isOpen ? null : f.finding_id)} className="text-mist-500 hover:text-mist-100">
                        {isOpen ? <ChevronDown size={16} aria-hidden /> : <ChevronRight size={16} aria-hidden />}
                      </button>
                    </td>
                    <td className="p-3 font-medium">{f.class_name}</td>
                    <td className="p-3"><ChangeBadge type={f.change_type} /></td>
                    <td className="p-3"><StatusBadge status={f.status} /></td>
                    <td className="p-3 tabular-nums">{fmt(f.detector_confidence.reference)} / {fmt(f.detector_confidence.later)}</td>
                    <td className="p-3 tabular-nums">{fmt(f.association_quality?.match_cost)}</td>
                    <td className="p-3 tabular-nums">{fmt(f.displacement_norm, 3)}</td>
                  </tr>
                  {isOpen && (
                    <tr className="border-b border-ink-700/70 bg-ink-900/60">
                      <td />
                      <td colSpan={6} className="space-y-3 p-4 text-sm">
                        <p>{f.explanation}</p>
                        {f.evidence.length > 0 && (<div><p className="mb-1 font-semibold">Evidence</p><ul className="list-disc space-y-0.5 pl-5 text-mist-300">{f.evidence.map((e) => <li key={e}>{e}</li>)}</ul></div>)}
                        {f.uncertainty_reasons.length > 0 && (
                          <div><p className="mb-1 font-semibold text-accent">Why this is uncertain</p>
                            <ul className="list-disc space-y-0.5 pl-5 text-mist-300">{f.uncertainty_reasons.map((r, i) => <li key={i}><span className="font-mono text-xs text-mist-500">{r.code}</span> — {r.detail}</li>)}</ul></div>)}
                        {f.caveats.length > 0 && <p className="text-mist-500">{f.caveats.join(" ")}</p>}
                        <dl className="grid gap-x-6 gap-y-1 font-mono text-xs text-mist-300 sm:grid-cols-2">
                          <div><dt className="inline text-mist-500">Reference box </dt><dd className="inline">{fmtBox(f.reference_detection)}</dd></div>
                          <div><dt className="inline text-mist-500">Later box </dt><dd className="inline">{fmtBox(f.later_detection)}</dd></div>
                          {f.association_quality && <div><dt className="inline text-mist-500">IoU </dt><dd className="inline">{f.association_quality.iou.toFixed(3)}</dd></div>}
                          {f.area_ratio !== null && <div><dt className="inline text-mist-500">Area ratio (later / reference) </dt><dd className="inline">{f.area_ratio}</dd></div>}
                        </dl>
                      </td>
                    </tr>
                  )}
                </Fragment>
              );
            })}
          </tbody>
        </table>
        {rows.length === 0 && <p className="p-4 text-sm text-mist-500">No findings match these filters.</p>}
      </div>
    </div>
  );
}
