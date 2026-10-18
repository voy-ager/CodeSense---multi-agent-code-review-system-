"use client";
import { motion } from "framer-motion";

export type Severity = "critical" | "high" | "medium" | "low";

type Finding = {
  severity: Severity;
  file: string;
  line: number;
  issue: string;
  fix: string;
  category: string;
  agent: string;
};

export const SEVERITY_STYLES: Record<Severity, string> = {
  critical: "bg-red-500/20 text-red-300 border-red-500/30",
  high:     "bg-orange-500/20 text-orange-300 border-orange-500/30",
  medium:   "bg-yellow-500/20 text-yellow-300 border-yellow-500/30",
  low:      "bg-blue-500/20 text-blue-300 border-blue-500/30",
};

const AGENT_ICONS: Record<string, string> = {
  security:    "🔒",
  performance: "⚡",
  testing:     "🧪",
  style:       "✏️",
};

export default function FindingCard({
  finding,
  index,
}: {
  finding: Finding;
  index: number;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{
        duration: 0.35,
        delay: index * 0.06,   // stagger each card
        ease: "easeOut",
      }}
      whileHover={{ y: -2, transition: { duration: 0.15 } }}
      className="bg-slate-900 border border-slate-800 hover:border-slate-600
                 rounded-2xl p-5 cursor-default transition-colors duration-200"
    >
      {/* Top row — badges + file location */}
      <div className="flex items-start justify-between gap-3 mb-3 flex-wrap">
        <div className="flex items-center gap-2 flex-wrap">
          {/* Severity badge */}
          <span className={`text-xs px-2.5 py-1 rounded-full border font-medium
                            ${SEVERITY_STYLES[finding.severity]}`}>
            {finding.severity}
          </span>

          {/* Agent badge */}
          <span className="text-xs text-slate-400 bg-slate-800 border border-slate-700
                           px-2.5 py-1 rounded-full">
            {AGENT_ICONS[finding.agent]} {finding.agent}
          </span>

          {/* Category label */}
          <span className="text-xs text-slate-500">{finding.category}</span>
        </div>

        {/* File + line — monospace, right-aligned */}
        <span className="text-xs font-mono text-slate-500 bg-slate-800/60
                         px-2 py-1 rounded shrink-0">
          {finding.file}:{finding.line}
        </span>
      </div>

      {/* Issue description */}
      <p className="text-sm text-slate-200 font-medium mb-3 leading-relaxed">
        {finding.issue}
      </p>

      {/* Fix suggestion — green accent */}
      <div className="bg-emerald-950/50 border border-emerald-900/50 rounded-xl px-4 py-2.5">
        <p className="text-xs text-emerald-400 leading-relaxed">
          <span className="font-semibold text-emerald-300">Fix: </span>
          {finding.fix}
        </p>
      </div>
    </motion.div>
  );
}