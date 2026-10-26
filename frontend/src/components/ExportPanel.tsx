import { Download } from "lucide-react";
import { reportCsvUrl, reportJsonUrl } from "../api/client";
import type { Report } from "../types";

export default function ExportPanel({ report }: { report: Report }) {
  return (
    <div className="space-y-4">
      <div className="panel p-5">
        <p className="text-sm text-mist-300">Report <span className="font-mono">{report.report_id}</span> · created {new Date(report.created_at).toLocaleString()}</p>
        <div className="mt-4 flex flex-wrap gap-3">
          <a className="btn-primary" href={reportJsonUrl(report.report_id)} download><Download size={16} aria-hidden /> Download JSON report</a>
          <a className="btn-quiet" href={reportCsvUrl(report.report_id)} download><Download size={16} aria-hidden /> Download findings CSV</a>
        </div>
        <p className="mt-3 text-xs text-mist-500">The JSON report contains configuration, detections, findings with evidence, spatial results, baseline results, warnings and limitations. The CSV lists one row per finding.</p>
      </div>
      <div className="panel p-5">
        <p className="mb-2 text-sm font-semibold">Limitations recorded in the report</p>
        <ul className="list-disc space-y-1 pl-5 text-sm text-mist-300">{report.limitations.map((l) => <li key={l}>{l}</li>)}</ul>
      </div>
    </div>
  );
}
