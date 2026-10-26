import clsx from "clsx";
import type { ChangeType, Status } from "../types";

export const CHANGE_LABEL: Record<ChangeType, string> = {
  unchanged: "Unchanged", possibly_relocated: "Possibly relocated", newly_observed: "Newly observed", not_observed: "Not observed",
};
const CHANGE_STYLE: Record<ChangeType, string> = {
  unchanged: "border-kept/40 bg-kept/10 text-kept",
  possibly_relocated: "border-moved/40 bg-moved/10 text-moved",
  newly_observed: "border-fresh/40 bg-fresh/10 text-fresh",
  not_observed: "border-gone/40 bg-gone/10 text-gone",
};

const base = "inline-flex items-center gap-1.5 whitespace-nowrap rounded border px-2 py-0.5 text-xs font-medium";

export function ChangeBadge({ type }: { type: ChangeType }) {
  return (
    <span className={clsx(base, CHANGE_STYLE[type])}>
      <span aria-hidden className="h-1.5 w-1.5 rounded-full bg-current" />
      {CHANGE_LABEL[type]}
    </span>
  );
}

export function StatusBadge({ status }: { status: Status }) {
  return (
    <span className={clsx(base, status === "supported" ? "border-ink-600 text-mist-300" : "border-accent/50 bg-accent/10 text-accent")}>
      {status === "supported" ? "Supported" : "Uncertain"}
    </span>
  );
}
