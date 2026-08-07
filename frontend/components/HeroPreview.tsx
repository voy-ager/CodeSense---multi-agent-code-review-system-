"use client";
import { motion } from "framer-motion";

const PIPELINE = [
  { label: "Security",    count: 1, color: "text-red-400"    },
  { label: "Performance", count: 0, color: "text-yellow-400" },
  { label: "Testing",     count: 2, color: "text-green-400"  },
  { label: "Style",       count: 1, color: "text-blue-400"   },
];

const FINDINGS = [
  {
    severity:   "critical",
    bg:         "bg-red-500/15",
    text:       "text-red-300",
    border:     "border-red-500/20",
    leftBorder: "border-l-red-500/60",
    agent:      "security",
    agentIcon:  "🔒",
    file:       "src/auth.js:42",
    issue:      "SQL injection via string concatenation in query builder",
    fix:        "Use parameterized queries",
  },
  {
    severity:   "medium",
    bg:         "bg-yellow-500/10",
    text:       "text-yellow-300",
    border:     "border-yellow-500/20",
    leftBorder: "border-l-yellow-500/50",
    agent:      "testing",
    agentIcon:  "🧪",
    file:       "src/api.js:87",
    issue:      "Missing test cases for validateUser() error paths",
    fix:        "Add tests for null, expired, and malformed inputs",
  },
  {
    severity:   "low",
    bg:         "bg-blue-500/10",
    text:       "text-blue-300",
    border:     "border-blue-500/20",
    leftBorder: "border-l-blue-500/40",
    agent:      "style",
    agentIcon:  "✏️",
    file:       "src/routes.js:156",
    issue:      "Function processRequest has 47 lines",
    fix:        "Break into smaller focused functions",
  },
];

export default function HeroPreview() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 40 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.8, delay: 0.5, ease: "easeOut" }}
    >
      <div style={{ animation: "heroFloat 4s ease-in-out 1.3s infinite" }}>
        <div className="bg-slate-900 border border-slate-700/60 rounded-2xl overflow-hidden shadow-2xl">

          {/* Top bar */}
          <div className="px-4 py-3 border-b border-slate-800 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <svg className="w-3.5 h-3.5 text-slate-400" fill="currentColor" viewBox="0 0 24 24">
                <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0 0 24 12c0-6.63-5.37-12-12-12z" />
              </svg>
              <span className="text-xs text-slate-400 font-mono">
                psf/requests <span className="text-slate-600">#6746</span>
              </span>
            </div>
            <span className="text-xs text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 rounded-full font-medium">
              Analyzed
            </span>
          </div>

          {/* Pipeline */}
          <div className="px-4 py-3 border-b border-slate-800">
            <p className="text-xs text-slate-500 uppercase tracking-wider mb-2.5 font-medium">
              Agent pipeline
            </p>
            <div className="space-y-1.5">
              {PIPELINE.map((p) => (
                <div key={p.label} className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="text-emerald-400 text-xs">✓</span>
                    <span className="text-xs text-slate-400">{p.label}</span>
                  </div>
                  <span className={`text-xs font-medium ${p.color}`}>
                    {p.count} {p.count === 1 ? "issue" : "issues"}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Findings */}
          <div className="p-3 space-y-2">
            {FINDINGS.map((f, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.4, delay: 0.9 + i * 0.12 }}
                className={`${f.bg} border ${f.border} border-l-2 ${f.leftBorder} rounded-xl p-3`}
              >
                <div className="flex items-center justify-between mb-1.5">
                  <div className="flex items-center gap-1.5">
                    <span className={`text-xs px-2 py-0.5 rounded-full border ${f.bg} ${f.text} ${f.border} font-medium`}>
                      {f.severity}
                    </span>
                    <span className="text-xs text-slate-500">
                      {f.agentIcon} {f.agent}
                    </span>
                  </div>
                  <span className="text-xs font-mono text-slate-500">
                    {f.file}
                  </span>
                </div>
                <p className="text-xs text-slate-200 mb-1.5 leading-relaxed">
                  {f.issue}
                </p>
                <p className="text-xs text-emerald-400 bg-emerald-950/50 border border-emerald-900/40 rounded-lg px-2 py-1">
                  Fix: {f.fix}
                </p>
              </motion.div>
            ))}
          </div>

        </div>
      </div>
    </motion.div>
  );
}