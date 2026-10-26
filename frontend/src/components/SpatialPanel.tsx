import { assetUrl } from "../api/client";
import type { Report } from "../types";
import { ChangeBadge } from "./StatusBadge";

export default function SpatialPanel({ report }: { report: Report }) {
  const { zones, findings } = report.spatial;
  if (zones.length === 0) {
    return <p className="panel p-6 text-sm text-mist-300">No zones are configured. Add polygons to <code className="font-mono">data/zones/zones.json</code> to enable spatial analysis.</p>;
  }
  return (
    <div className="space-y-4">
      <div className="grid gap-4 lg:grid-cols-2">
        {report.outputs.annotated_later && (
          <figure className="panel overflow-hidden">
            <figcaption className="px-4 py-2.5 text-sm font-semibold">Later image with configured zones</figcaption>
            <img src={assetUrl(report.outputs.annotated_later)} alt="Later image with zone polygons shaded" className="w-full bg-ink-900" />
          </figure>
        )}
        <div className="space-y-4">
          <div className="panel p-4">
            <p className="mb-2 text-sm font-semibold">Configured zones</p>
            <ul className="space-y-3 text-sm">
              {zones.map((z) => (
                <li key={z.id}>
                  <p className="font-medium">{z.name} {!z.enabled && <span className="text-mist-500">(disabled)</span>}</p>
                  <p className="text-mist-500">{z.description}</p>
                  <p className="text-mist-300">Rule: object box overlaps the zone by at least {(z.rule.min_overlap_fraction * 100).toFixed(0)}%
                    {z.rule.classes.length > 0 ? ` · classes: ${z.rule.classes.join(", ")}` : " · any class"}</p>
                </li>
              ))}
            </ul>
          </div>
          <p className="panel p-4 text-sm text-mist-300">{report.spatial.note}</p>
        </div>
      </div>

      <div className="panel overflow-x-auto">
        <p className="p-4 pb-2 text-sm font-semibold">Potential spatial concerns ({findings.length})</p>
        {findings.length === 0 ? <p className="px-4 pb-4 text-sm text-mist-500">No detection met a zone rule in either image.</p> : (
          <table className="w-full min-w-[760px] text-left text-sm">
            <thead className="border-y border-ink-700 text-xs text-mist-500"><tr>
              <th className="p-3 font-medium">Zone</th><th className="p-3 font-medium">Image</th><th className="p-3 font-medium">Object</th>
              <th className="p-3 font-medium">Overlap of object box</th><th className="p-3 font-medium">Change</th><th className="p-3 font-medium">Rule met</th></tr></thead>
            <tbody>
              {findings.map((f) => (
                <tr key={`${f.zone_id}-${f.detection_id}`} className="border-b border-ink-700/70 align-top">
                  <td className="p-3">{f.zone_name}</td><td className="p-3">{f.image_role}</td>
                  <td className="p-3">{f.class_name}<span className="block font-mono text-xs text-mist-500">[{f.bbox.map(Math.round).join(", ")}]</span></td>
                  <td className="p-3 tabular-nums">{(f.overlap_fraction_of_object * 100).toFixed(1)}% · {Math.round(f.overlap_area_px)} px²</td>
                  <td className="p-3">{f.change_type ? <ChangeBadge type={f.change_type} /> : "—"}</td>
                  <td className="p-3 text-mist-300">{f.rule}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
