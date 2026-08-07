"use client";
import { motion } from "framer-motion";

type Severity = "critical" | "high" | "medium" | "low";

type Report = {
  pr_title: string;
  author: string;
  total_findings: number;
  by_severity: Record<Severity, number>;
  by_agent: Record<string, number>;
  summary: string;
};

const SEVERITY_STYLES: Record<Severity, string> = {
  critical: "bg-red-500/20 text-red-300 border-red-500/30 hover:bg-red-500/30",
  high:     "bg-orange-500/20 text-orange-300 border-orange-500/30 hover:bg-orange-500/30",
  medium:   "bg-yellow-500/20 text-yellow-300 border-yellow-500/30 hover:bg-yellow-500/30",
  low:      "bg-blue-500/20 text-blue-300 border-blue-500/30 hover:bg-blue-500/30",
};

const AGENT_ICONS: Record<string, string> = {
  security:    "🔒",
  performance: "⚡",
  testing:     "🧪",
  style:       "✏️",
};

export default function AgentPanel({
  report,
  filter,
  setFilter,
}: {
  report: Report;
  filter: string;
  setFilter: (f: string) => void;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="bg-slate-900 border border-slate-800 rounded-2xl p-5 mb-6"
    >
      {/* PR info */}
      <div className="flex items-start justify-between flex-wrap gap-4 mb-5">
        <div>
          <h2 className="text-base font-semibold text-white mb-1">
            {report.pr_title}
          </h2>
          <p className="text-sm text-slate-400">by {report.author}</p>
        </div>
        <span className="text-sm text-slate-400 bg-slate-800 px-3 py-1.5 rounded-lg">
          {report.summary}
        </span>
      </div>

      {/* Severity filters */}
      <div className="flex gap-2 flex-wrap mb-4">
        {(["critical", "high", "medium", "low"] as Severity[]).map((sev) => (
          <motion.button
            key={sev}
            whileTap={{ scale: 0.95 }}
            onClick={() => setFilter(filter === sev ? "all" : sev)}
            className={`text-xs px-3 py-1.5 rounded-full border font-medium
                        transition-all duration-200 ${SEVERITY_STYLES[sev]}
                        ${filter === sev ? "ring-2 ring-white/20 ring-offset-1 ring-offset-slate-900" : ""}`}
          >
            {report.by_severity[sev]} {sev}
          </motion.button>
        ))}
      </div>

      {/* Agent filters */}
      <div className="flex gap-2 flex-wrap items-center">
        {Object.entries(report.by_agent).map(([agent, count]) => (
          <motion.button
            key={agent}
            whileTap={{ scale: 0.95 }}
            onClick={() => setFilter(filter === agent ? "all" : agent)}
            className={`text-xs text-slate-300 flex items-center gap-1.5 px-3 py-1.5
                        bg-slate-800 rounded-lg border border-slate-700
                        hover:border-slate-500 hover:bg-slate-700/60
                        transition-all duration-200
                        ${filter === agent ? "ring-2 ring-white/20 ring-offset-1 ring-offset-slate-900" : ""}`}
          >
            <span>{AGENT_ICONS[agent]}</span>
            {agent}: {count}
          </motion.button>
        ))}

        {filter !== "all" && (
          <button
            onClick={() => setFilter("all")}
            className="text-xs text-blue-400 hover:text-blue-300 transition-colors ml-1"
          >
            clear filter
          </button>
        )}
      </div>
    </motion.div>
  );
}