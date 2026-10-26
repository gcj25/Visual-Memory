import { useCallback, useState } from "react";
import { History as HistoryIcon, LayoutDashboard, ScanSearch } from "lucide-react";
import clsx from "clsx";
import { api } from "./api/client";
import Compare from "./pages/Compare";
import History from "./pages/History";
import Overview from "./pages/Overview";
import type { Report } from "./types";

type View = "overview" | "compare" | "history";
const NAV: { id: View; label: string; icon: typeof ScanSearch }[] = [
  { id: "overview", label: "Overview", icon: LayoutDashboard },
  { id: "compare", label: "Compare", icon: ScanSearch },
  { id: "history", label: "History", icon: HistoryIcon },
];

export default function App() {
  const [view, setView] = useState<View>("overview");
  const [report, setReport] = useState<Report | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const openReport = useCallback(async (id: string) => {
    try { setReport(await api.report(id)); setNotice(null); setView("compare"); }
    catch (e) { setNotice(e instanceof Error ? e.message : "Could not open the report."); }
  }, []);

  return (
    <div className="min-h-screen md:grid md:grid-cols-[13rem_1fr]">
      <nav aria-label="Main" className="border-b border-ink-700 bg-ink-900 md:sticky md:top-0 md:h-screen md:border-b-0 md:border-r">
        <div className="flex items-center gap-4 px-4 py-3 md:flex-col md:items-stretch md:gap-6 md:px-3 md:py-5">
          <span className="text-base font-semibold tracking-tight md:px-2">Visual Memory</span>
          <ul className="flex gap-1 md:flex-col">
            {NAV.map(({ id, label, icon: Icon }) => (
              <li key={id}>
                <button type="button" aria-current={view === id ? "page" : undefined} onClick={() => setView(id)}
                        className={clsx("flex w-full items-center gap-2 rounded-md px-3 py-2 text-sm", view === id ? "bg-ink-700 text-mist-100" : "text-mist-300 hover:bg-ink-800")}>
                  <Icon size={16} aria-hidden />{label}
                </button>
              </li>
            ))}
          </ul>
        </div>
      </nav>
      <main className="mx-auto w-full max-w-6xl px-4 py-8 md:px-8">
        {notice && <p role="alert" className="panel mb-4 border-gone/40 p-4 text-sm text-gone">{notice}</p>}
        {view === "overview" && <Overview onNavigate={setView} onOpenReport={openReport} />}
        {view === "compare" && <Compare report={report} onReport={setReport} />}
        {view === "history" && <History onOpenReport={openReport} />}
      </main>
    </div>
  );
}
