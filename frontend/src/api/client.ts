import type { Health, ObservationSummary, Report, ReportListItem } from "../types";

export const API_BASE: string = import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000";

export class ApiError extends Error {
  constructor(public status: number, message: string) { super(message); }
}

async function parse<T>(r: Response): Promise<T> {
  if (!r.ok) {
    let msg = `${r.status} ${r.statusText}`;
    try {
      const j = await r.json();
      msg = typeof j.detail === "string" ? j.detail : JSON.stringify(j.detail ?? j);
    } catch { /* keep default */ }
    throw new ApiError(r.status, msg);
  }
  return r.json() as Promise<T>;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, init);
  } catch {
    throw new ApiError(0, `Cannot reach the backend at ${API_BASE}. Is it running?`);
  }
  return parse<T>(res);
}

export const assetUrl = (path: string) => `${API_BASE}${path}`;
export const reportJsonUrl = (id: string) => `${API_BASE}/api/reports/${id}?download=true`;
export const reportCsvUrl = (id: string) => `${API_BASE}/api/reports/${id}/csv`;

export const api = {
  health: () => request<Health>("/health"),
  observations: () => request<{ count: number; observations: ObservationSummary[]; warnings: string[] }>("/api/observations"),
  reports: () => request<{ reports: ReportListItem[] }>("/api/reports"),
  report: (id: string) => request<Report>(`/api/reports/${id}`),
  compare(reference: File, later: File, opts: { conf: number; align: boolean }) {
    const fd = new FormData();
    fd.append("reference", reference);
    fd.append("later", later);
    fd.append("detector_conf", String(opts.conf));
    fd.append("enable_alignment", String(opts.align));
    return request<Report>("/api/compare", { method: "POST", body: fd });
  },
};
