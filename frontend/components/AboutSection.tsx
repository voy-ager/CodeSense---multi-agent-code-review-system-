"use client";
import { motion, MotionConfig } from "framer-motion";
import { REPO_URL } from "@/lib/site";

// Every claim here maps to something in the codebase — no marketing numbers.
const DECISIONS = [
  {
    title: "Parallel by design",
    body: "LangGraph fans the diff out to four independent agents, so a review takes as long as the slowest agent, not the sum of all four.",
  },
  {
    title: "Failures are never silent",
    body: "If an agent errors, the report is marked incomplete and names it. A broken review is never shown as a clean PR, and incomplete reports aren't cached.",
  },
  {
    title: "One schema, ranked output",
    body: "Every agent returns the same JSON shape — severity, file, line, issue, fix — so findings from all four merge into one list sorted by severity.",
  },
  {
    title: "Cached and persisted",
    body: "Redis caches each report for an hour, so repeat reviews return instantly. PostgreSQL keeps the review history behind an API key.",
  },
  {
    title: "Hardened API",
    body: "Per-client rate limits, strict GitHub URL validation, request size caps, security headers, a CORS allowlist, and a non-root container.",
  },
  {
    title: "Open source",
    body: "Every agent prompt, the pipeline, and the infrastructure are on GitHub. Read exactly what each agent is told to look for.",
  },
];

const STACK = [
  "LangGraph", "Groq · gpt-oss-120b", "FastAPI + SSE", "PostgreSQL",
  "Redis", "Docker", "Next.js 16", "Framer Motion",
];

const LIMITS = [
  "Public GitHub pull requests only",
  "Diffs beyond 8,000 characters are truncated",
  "Findings are AI-generated — treat them as a first pass, not a verdict",
];

export default function AboutSection() {
  return (
    <MotionConfig reducedMotion="user">
      <section id="about" className="py-24 px-4 sm:px-6 border-t border-slate-800/60 scroll-mt-14">
        <div className="max-w-6xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5 }}
            className="max-w-2xl mb-12"
          >
            <span className="text-xs font-medium text-blue-400 bg-blue-500/10 border border-blue-500/20 rounded-full px-4 py-1.5">
              Under the hood
            </span>
            <h2 className="text-3xl font-semibold text-white tracking-tight mt-6 mb-3 text-balance">
              Built like a production service, not a demo
            </h2>
            <p className="text-slate-400 leading-relaxed">
              The decisions that keep reviews fast, honest about failure, and safe to expose publicly.
            </p>
          </motion.div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {DECISIONS.map((d, i) => (
              <motion.div
                key={d.title}
                initial={{ opacity: 0, y: 16 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.4, delay: (i % 3) * 0.06 }}
                className="rounded-2xl border border-slate-800 bg-slate-900 p-6 hover:border-slate-700 transition-colors"
              >
                <h3 className="text-base font-semibold text-white mb-2">{d.title}</h3>
                <p className="text-sm text-slate-400 leading-relaxed">{d.body}</p>
              </motion.div>
            ))}
          </div>

          <div className="mt-12 grid grid-cols-1 lg:grid-cols-2 gap-8">
            <div>
              <h3 className="text-xs font-medium text-slate-500 uppercase tracking-wider mb-4">Stack</h3>
              <ul className="flex flex-wrap gap-2">
                {STACK.map(s => (
                  <li key={s} className="text-sm text-slate-300 bg-slate-900 border border-slate-800 rounded-lg px-3 py-1.5 font-mono">
                    {s}
                  </li>
                ))}
              </ul>
            </div>
            <div>
              <h3 className="text-xs font-medium text-slate-500 uppercase tracking-wider mb-4">Known limits</h3>
              <ul className="space-y-2">
                {LIMITS.map(l => (
                  <li key={l} className="flex gap-2 text-sm text-slate-400">
                    <span className="text-slate-600" aria-hidden="true">—</span>{l}
                  </li>
                ))}
              </ul>
              <a href={REPO_URL} target="_blank" rel="noopener noreferrer"
                 className="inline-block mt-5 text-sm text-blue-400 hover:text-blue-300 underline underline-offset-4">
                Read the source on GitHub
              </a>
            </div>
          </div>
        </div>
      </section>
    </MotionConfig>
  );
}
