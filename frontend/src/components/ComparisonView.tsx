import { AlertTriangle } from "lucide-react";
import { assetUrl } from "../api/client";
import type { ChangeType, Report } from "../types";
import { CHANGE_LABEL, ChangeBadge } from "./StatusBadge";

const ORDER: ChangeType[] = ["unchanged", "possibly_relocated", "newly_observed", "not_observed"];

function Figure({ title, sub, src }: { title: string; sub: string; src?: string }) {
  return (
    <figure className="panel overflow-hidden">
      <figcaption className="flex items-baseline justify-between px-4 py-2.5">
        <span className="text-sm font-semibold">{title}</span>
        <span className="truncate pl-3 text-xs text-mist-500">{sub}</span>
      </figcaption>
      {src ? <img src={assetUrl(src)} alt={`${title}, annotated with detections`} className="w-full bg-ink-900" />
           : <div className="p-6 text-sm text-mist-500">Not available.</div>}
    </figure>
  );
}

export default function ComparisonView({ report }: { report: Report }) {
  const s = report.summary;
  return (
    <div className="space-y-4">
      <div className="panel p-4">
        <div className="flex flex-wrap items-center gap-x-6 gap-y-3">
          <div>
            <p className="text-2xl font-semibold tabular-nums">{s.total}</p>
            <p className="text-xs text-mist-500">findings · {s.uncertain} uncertain</p>
          </div>
          <div className="flex flex-wrap gap-2">
            {ORDER.map((t) => (
              <span key={t} className="flex items-center gap-2">
                <ChangeBadge type={t} /><span className="text-sm tabular-nums text-mist-300">{s.by_change_type[t] ?? 0}</span>
              </span>
            ))}
          </div>
        </div>
        <p className="mt-3 text-xs text-mist-500">
          Detections: {s.reference_detections} in the reference, {s.later_detections} in the later image · model {report.model.name} on {report.model.device} ·
          processed in {report.timings.total_s}s
        </p>
        <p className="mt-1 text-xs text-mist-500">
          Alignment: {report.alignment.applied
            ? `applied (RANSAC inlier ratio ${report.alignment.inlier_ratio?.toFixed(2)}, an indicator rather than a probability)`
            : `not applied — ${report.alignment.reason}`}
        </p>
      </div>

      {report.warnings.length > 0 && (
        <div role="status" className="panel border-moved/30 p-4">
          <p className="mb-1 flex items-center gap-2 text-sm font-semibold text-moved"><AlertTriangle size={16} aria-hidden /> Notes on this result</p>
          <ul className="list-disc space-y-1 pl-5 text-sm text-mist-300">{report.warnings.map((w) => <li key={w}>{w}</li>)}</ul>
        </div>
      )}

      <div className="grid gap-4 lg:grid-cols-2">
        <Figure title="Reference" sub={report.reference_image.filename} src={report.outputs.annotated_reference} />
        <Figure title="Later observation" sub={report.later_image.filename} src={report.outputs.annotated_later} />
      </div>
      <p className="text-xs text-mist-500">
        Box colours: {ORDER.map((t) => CHANGE_LABEL[t]).join(", ")} (green, amber, blue, red). A “?” after a label marks an uncertain finding.
      </p>
    </div>
  );
}
