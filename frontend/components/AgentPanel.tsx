"use client";
import AgentIcon from "@/components/AgentIcon";
import { motion } from "framer-motion";

type Severity = "critical" | "high" | "medium" | "low";

type Report = {
  pr_title: string;
  author: string;
  total_findings: number;
  by_severity: Record<Severity, number>;
  by_agent: Record<string, number>;
  summary: string;
  diff_truncated?: boolean;
  failed_agents?: string[];
  stale?: boolean;
};

const SEVERITY_STYLES: Record<Severity, string> = {
  critical: "bg-red-500/20 text-red-300 border-red-500/30 hover:bg-red-500/30",
  high:     "bg-orange-500/20 text-orange-300 border-orange-500/30 hover:bg-orange-500/30",
  medium:   "bg-yellow-500/20 text-yellow-300 border-yellow-500/30 hover:bg-yellow-500/30",
  low:      "bg-blue-500/20 text-blue-300 border-blue-500/30 hover:bg-blue-500/30",
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

      {!!report.failed_agents?.length && (
        <p role="alert" className="text-sm text-red-300 bg-red-500/10 border border-red-500/30 rounded-lg px-3 py-2 mb-4">
          Incomplete review: the {report.failed_agents.join(", ")} check{report.failed_agents.length > 1 ? "s" : ""} failed.
          A missing finding does not mean the code is clean — try again in a minute.
        </p>
      )}

      {report.stale && (
        <p role="note" className="text-sm text-amber-300 bg-amber-500/10 border border-amber-500/30 rounded-lg px-3 py-2 mb-4">
          GitHub couldn&apos;t be reached, so this is the most recent saved review. It may predate the latest commits.
        </p>
      )}

      {report.diff_truncated && (
        <p role="note" className="text-sm text-amber-300 bg-amber-500/10 border border-amber-500/30 rounded-lg px-3 py-2 mb-4">
          Large PR: the AI agents reviewed the first part of the diff. Rule-based checks
          (secrets, dependencies, hidden Unicode, prompt injection) covered all of it.
        </p>
      )}

      {/* Severity filters */}
      <div className="flex gap-2 flex-wrap mb-4">
        {(["critical", "high", "medium", "low"] as Severity[]).map((sev) => (
          <motion.button
            key={sev}
            whileTap={{ scale: 0.95 }}
            onClick={() => setFilter(filter === sev ? "all" : sev)}
            aria-pressed={filter === sev}
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
            aria-pressed={filter === agent}
            className={`text-xs text-slate-300 flex items-center gap-1.5 px-3 py-1.5
                        bg-slate-800 rounded-lg border border-slate-700
                        hover:border-slate-500 hover:bg-slate-700/60
                        transition-all duration-200
                        ${filter === agent ? "ring-2 ring-white/20 ring-offset-1 ring-offset-slate-900" : ""}`}
          >
            <AgentIcon name={agent} className="w-3.5 h-3.5" />
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