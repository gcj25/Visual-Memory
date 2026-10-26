export type ChangeType = "unchanged" | "possibly_relocated" | "newly_observed" | "not_observed";
export type Status = "supported" | "uncertain";

export interface Detection {
  id: string; image_id: string; class_name: string; bbox: [number, number, number, number];
  confidence: number; image_width: number; image_height: number;
}
export interface UncertaintyReason { code: string; detail: string }
export interface Finding {
  finding_id: string; change_type: ChangeType; status: Status; class_name: string; explanation: string;
  reference_detection: Detection | null; later_detection: Detection | null;
  displacement_norm: number | null; area_ratio: number | null;
  association_quality: { match_cost: number; iou: number; normalized_centroid_distance: number; ambiguous: boolean } | null;
  detector_confidence: { reference: number | null; later: number | null };
  evidence: string[]; uncertainty_reasons: UncertaintyReason[]; caveats: string[];
}
export interface SpatialFinding {
  zone_id: string; zone_name: string; image_role: string; detection_id: string; class_name: string;
  bbox: number[]; overlap_area_px: number; overlap_fraction_of_object: number; rule: string;
  status: string; change_type: ChangeType | null; note: string;
}
export interface Zone {
  id: string; name: string; description: string; polygon: number[][]; coordinate_space: string; enabled: boolean;
  rule: { type: string; min_overlap_fraction: number; classes: string[] };
}
export interface ImageMeta { image_id: string; filename: string; width: number; height: number; sha256: string; format: string; size_bytes: number }
export interface Baseline {
  available: boolean; warnings: string[]; explanation: string; region_count?: number;
  changed_pixel_fraction?: number; regions?: { bbox: number[]; area_px: number }[];
}
export interface Report {
  report_id: string; created_at: string; reference_image: ImageMeta; later_image: ImageMeta;
  model: Record<string, unknown> & { name: string; device: string };
  configuration: Record<string, unknown>;
  detections: { reference: Detection[]; later: Detection[] };
  alignment: { attempted: boolean; applied: boolean; reason: string; inlier_ratio?: number | null; inliers?: number; good_matches?: number };
  summary: { total: number; uncertain: number; by_change_type: Partial<Record<ChangeType, number>>; reference_detections: number; later_detections: number };
  findings: Finding[];
  spatial: { zones: Zone[]; findings: SpatialFinding[]; note: string };
  baseline: Baseline;
  outputs: Record<string, string>;
  timings: Record<string, number>;
  warnings: string[]; limitations: string[];
}
export interface ObservationSummary {
  observation_id: string; timestamp: string; role: string; detection_count: number;
  image: (ImageMeta & { stored_file?: string }) | null;
  comparison: { report_id: string; reference_image_id: string; summary: Report["summary"] } | null;
}
export interface Health { status: string; detector: { initialized: boolean; model: string; error: string | null } }
export interface ReportListItem { report_id: string; created_at: string; reference_image: string; later_image: string; summary: Report["summary"] }
