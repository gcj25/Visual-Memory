import { assetUrl } from "../api/client";
import type { Report } from "../types";

export default function BaselineComparison({ report }: { report: Report }) {
  const b = report.baseline;
  return (
    <div className="space-y-4">
      <div className="grid gap-4 lg:grid-cols-2">
        <figure className="panel overflow-hidden">
          <figcaption className="px-4 py-2.5 text-sm font-semibold">Object-level method</figcaption>
          {report.outputs.annotated_later && <img src={assetUrl(report.outputs.annotated_later)} alt="Object-level annotated later image" className="w-full bg-ink-900" />}
          <p className="px-4 py-3 text-sm text-mist-300">
            {report.summary.total} findings; {report.summary.by_change_type.unchanged ?? 0} unchanged, {report.summary.total - (report.summary.by_change_type.unchanged ?? 0)} reported as changes.
          </p>
        </figure>
        <figure className="panel overflow-hidden">
          <figcaption className="px-4 py-2.5 text-sm font-semibold">Pixel-difference baseline</figcaption>
          {b.available && report.outputs.baseline_overlay
            ? <img src={assetUrl(report.outputs.baseline_overlay)} alt="Pixel-difference regions drawn on the later image" className="w-full bg-ink-900" />
            : <p className="px-4 py-6 text-sm text-mist-500">The baseline could not be computed for this pair.</p>}
          {b.available && (
            <p className="px-4 py-3 text-sm text-mist-300">
              {b.region_count} changed region{b.region_count === 1 ? "" : "s"}; {((b.changed_pixel_fraction ?? 0) * 100).toFixed(2)}% of pixels above the threshold.
            </p>
          )}
        </figure>
      </div>
      {b.available && report.outputs.baseline_mask && (
        <details className="panel p-4">
          <summary className="cursor-pointer text-sm font-semibold">Difference mask</summary>
          <img src={assetUrl(report.outputs.baseline_mask)} alt="Binary pixel-difference mask" className="mt-3 w-full max-w-xl bg-ink-900" />
        </details>
      )}
      <div className="panel p-4 text-sm text-mist-300">
        <p>{b.explanation}</p>
        {b.warnings.length > 0 && <ul className="mt-2 list-disc space-y-1 pl-5 text-mist-500">{b.warnings.map((w) => <li key={w}>{w}</li>)}</ul>}
        <p className="mt-2 text-mist-500">Which method is more useful depends on the scene; compare them on labelled pairs rather than from a single result.</p>
      </div>
    </div>
  );
}
