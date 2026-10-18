"use client";
// Adapted from 21st.dev "DevTool Landing Page" (code-stepper hero) — reworked as a
// diff walkthrough where each agent highlights the line it flagged.
import { useState } from "react";
import { motion, AnimatePresence, MotionConfig } from "framer-motion";
import { SEVERITY_STYLES, type Severity } from "@/components/FindingCard";

type DiffLine = { num: number; kind: "ctx" | "add" | "del"; code: string };

const DIFF: DiffLine[] = [
  { num: 1, kind: "ctx", code: '@app.get("/users/{user_id}/orders")' },
  { num: 2, kind: "ctx", code: "def get_orders(user_id):" },
  { num: 3, kind: "del", code: "    return Order.query.filter_by(user_id=user_id).all()" },
  { num: 4, kind: "add", code: "    sql = f\"SELECT * FROM orders WHERE user_id = '{user_id}'\"" },
  { num: 5, kind: "add", code: "    orders = db.execute(sql).fetchall()" },
  { num: 6, kind: "add", code: "    for o in orders:" },
  { num: 7, kind: "add", code: '        o.items = db.execute(f"SELECT * FROM items WHERE order_id={o.id}")' },
  { num: 8, kind: "add", code: "    return orders" },
];

const FINDINGS: { line: number; agent: string; severity: Severity; issue: string; fix: string }[] = [
  { line: 4, agent: "Security",    severity: "critical", issue: "SQL injection: user_id is interpolated straight into the query.", fix: "Use a parameterized query: db.execute(sql, {\"uid\": user_id})." },
  { line: 7, agent: "Performance", severity: "high",     issue: "N+1 query: one items lookup per order.",                         fix: "Load all items in one query with WHERE order_id IN (...)." },
  { line: 2, agent: "Testing",     severity: "medium",   issue: "The new raw-SQL path has no test for an unknown user_id.",       fix: "Add a test asserting an empty list for a missing user." },
  { line: 6, agent: "Style",       severity: "low",      issue: "Single-letter loop variable `o` hides intent.",                  fix: "Rename `o` to `order`." },
];

const LINE_STYLES: Record<DiffLine["kind"], { bg: string; sign: string; text: string }> = {
  ctx: { bg: "",                sign: " ", text: "text-slate-300" },
  add: { bg: "bg-emerald-500/[0.07]", sign: "+", text: "text-emerald-200/90" },
  del: { bg: "bg-red-500/[0.08]",     sign: "-", text: "text-red-300/80 line-through decoration-red-400/40" },
};

export default function CodeReviewHero() {
  // Default to the first finding so touch users (no hover) still see the walkthrough.
  const [activeLine, setActiveLine] = useState<number>(FINDINGS[0].line);
  const active = FINDINGS.find(f => f.line === activeLine)!;

  return (
    <MotionConfig reducedMotion="user">
      <section className="relative pt-28 pb-16 px-4 sm:px-6 border-b border-slate-800/60 overflow-hidden">
        <div className="max-w-6xl mx-auto grid grid-cols-1 lg:grid-cols-12 gap-10 lg:gap-12 items-center">

          {/* Left: copy + walkthrough */}
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.45, ease: "easeOut" }}
            className="lg:col-span-5 space-y-8"
          >
            <div className="space-y-4">
              <span className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-slate-900
                               border border-slate-800 text-xs font-medium text-slate-400">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" aria-hidden="true" />
                Multi-agent AI code review
              </span>
              <h1 className="text-4xl lg:text-5xl font-semibold text-white tracking-tight leading-tight">
                Code review that{" "}
                <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-cyan-400">
                  thinks in parallel
                </span>
              </h1>
              <p className="text-base text-slate-400 leading-relaxed max-w-lg">
                Paste a GitHub PR. Four specialist agents review security, performance,
                test coverage, and style at the same time, then rank every finding by severity
                with a concrete fix.
              </p>
            </div>

            <div>
              <p id="walkthrough-label" className="text-xs font-medium text-slate-500 uppercase tracking-wider mb-3">
                What each agent caught
              </p>
              <div role="group" aria-labelledby="walkthrough-label" className="space-y-1.5">
                {FINDINGS.map(f => {
                  const isActive = f.line === activeLine;
                  return (
                    <button
                      key={f.line}
                      type="button"
                      aria-pressed={isActive}
                      onMouseEnter={() => setActiveLine(f.line)}
                      onFocus={() => setActiveLine(f.line)}
                      onClick={() => setActiveLine(f.line)}
                      className={`w-full min-h-11 text-left px-4 py-3 rounded-xl border cursor-pointer
                                  transition-colors duration-200 focus-visible:outline-2
                                  focus-visible:outline-offset-2 focus-visible:outline-blue-400 ${
                        isActive
                          ? "bg-slate-900/80 border-slate-700"
                          : "border-transparent hover:border-slate-800 hover:bg-slate-900/40"
                      }`}
                    >
                      <span className="flex items-center gap-3">
                        <span className={`text-[11px] font-medium px-2 py-0.5 rounded-md border shrink-0 ${SEVERITY_STYLES[f.severity]}`}>
                          {f.severity}
                        </span>
                        <span className={`text-sm transition-colors ${isActive ? "text-slate-100" : "text-slate-400"}`}>
                          <span className="font-medium">{f.agent}</span>
                          <span className="text-slate-500"> · line {f.line}</span>
                        </span>
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>

            <div className="flex flex-wrap gap-3">
              <a href="#review"
                 className="bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium px-6 py-3
                            rounded-xl transition-colors duration-200 focus-visible:outline-2
                            focus-visible:outline-offset-2 focus-visible:outline-blue-400">
                Analyze a PR
              </a>
              <a href="#how-it-works"
                 className="text-slate-300 hover:text-white text-sm font-medium px-6 py-3 rounded-xl
                            border border-slate-800 hover:border-slate-600 transition-colors duration-200
                            focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-400">
                How it works
              </a>
            </div>
          </motion.div>

          {/* Right: diff panel */}
          <motion.div
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.1, ease: "easeOut" }}
            className="lg:col-span-7 relative min-w-0"
          >
            <div className="absolute -inset-1 bg-gradient-to-b from-blue-500/10 to-transparent rounded-2xl blur-xl" aria-hidden="true" />
            <figure className="relative rounded-xl overflow-hidden bg-[#0b1120] border border-slate-800 shadow-2xl">
              <figcaption className="flex items-center justify-between gap-3 px-4 py-3 bg-slate-900/80 border-b border-slate-800">
                <span className="flex items-center gap-2 px-2 py-1 bg-slate-950/60 rounded-md border border-slate-800
                                 text-xs text-slate-400 font-mono truncate">
                  api/orders.py
                </span>
                <span className="text-xs text-slate-500 shrink-0">Example review · 4 agents</span>
              </figcaption>

              <div className="py-3 font-mono text-[13px] sm:text-sm leading-7 overflow-x-auto">
                {DIFF.map(line => {
                  const style    = LINE_STYLES[line.kind];
                  const isActive = line.num === activeLine;
                  return (
                    <div key={line.num}>
                      <motion.div
                        animate={{ opacity: isActive ? 1 : 0.55 }}
                        transition={{ duration: 0.2 }}
                        className={`relative flex pr-4 ${style.bg}`}
                      >
                        {isActive && (
                          <motion.span
                            layoutId="active-line"
                            className="absolute inset-0 bg-blue-400/10 border-l-2 border-blue-400"
                            transition={{ duration: 0.2 }}
                            aria-hidden="true"
                          />
                        )}
                        <span className="relative w-10 shrink-0 text-right pr-3 text-slate-600 select-none">{line.num}</span>
                        <span className="relative w-4 shrink-0 text-slate-500 select-none">{style.sign}</span>
                        <span className={`relative whitespace-pre ${style.text}`}>{line.code}</span>
                      </motion.div>

                      <AnimatePresence initial={false}>
                        {isActive && (
                          <motion.div
                            key={line.num}
                            initial={{ opacity: 0, y: -4 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0 }}
                            transition={{ duration: 0.18 }}
                            className="mx-4 my-2 sm:ml-14 rounded-lg border border-slate-700 bg-slate-900
                                       p-3 font-sans text-sm leading-relaxed whitespace-normal"
                            aria-live="polite"
                          >
                            <p className="flex items-center gap-2 mb-1.5">
                              <span className={`text-[11px] font-medium px-2 py-0.5 rounded-md border ${SEVERITY_STYLES[active.severity]}`}>
                                {active.severity}
                              </span>
                              <span className="text-xs text-slate-400">{active.agent} agent</span>
                            </p>
                            <p className="text-slate-200">{active.issue}</p>
                            <p className="text-slate-400 mt-1">
                              <span className="text-emerald-400 font-medium">Fix: </span>{active.fix}
                            </p>
                          </motion.div>
                        )}
                      </AnimatePresence>
                    </div>
                  );
                })}
              </div>
            </figure>
          </motion.div>
        </div>
      </section>
    </MotionConfig>
  );
}
