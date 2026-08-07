"use client";
import { motion, useInView } from "framer-motion";
import { useRef } from "react";

const STACK = [
  { label: "LangGraph",     desc: "Parallel fan-out agent orchestration" },
  { label: "Llama 3.3 70B", desc: "Free, fast inference via Groq" },
  { label: "FastAPI",       desc: "Streaming SSE backend" },
  { label: "Next.js 14",    desc: "TypeScript frontend with Framer Motion" },
  { label: "GitHub API",    desc: "PR diff and metadata fetching" },
  { label: "Framer Motion", desc: "Smooth animations and transitions" },
];

const PROBLEMS = [
  {
    stat: "20-30%",
    label: "of senior engineer time",
    desc: "spent on first-pass code review - the most repetitive part of the job.",
  },
  {
    stat: "48 min",
    label: "average review wait time",
    desc: "developers sit idle waiting for feedback before they can move forward.",
  },
  {
    stat: "1 in 3",
    label: "security issues missed",
    desc: "human reviewers under time pressure consistently overlook vulnerability patterns.",
  },
];

const VALUES = [
  {
    icon: "🔒",
    title: "Security analysis on every PR",
    desc: "Dedicated security analysis on every PR. SQL injection, XSS, hardcoded secrets, and missing auth checks flagged before code ever reaches production.",
  },
  {
    icon: "⚡",
    title: "Instant, parallel feedback",
    desc: "Four agents run simultaneously. No waiting for a senior engineer to be available. Developers get actionable feedback in under 30 seconds.",
  },
  {
    icon: "📋",
    title: "Consistent quality bar",
    desc: "Every PR gets reviewed against the same standards. No more inconsistency based on who reviewed it or how much time they had.",
  },
  {
    icon: "🎯",
    title: "Actionable, not just critical",
    desc: "Every finding includes a concrete fix suggestion. Not just what is wrong, but exactly what to do about it.",
  },
];

const DECISIONS = [
  {
    title: "Why parallel agents",
    body: "Running security, performance, testing, and style agents sequentially would take 4x longer. LangGraph's fan-out pattern runs all four simultaneously so total time equals the slowest single agent.",
  },
  {
    title: "Why structured JSON output",
    body: "Every agent returns the same schema: severity, file, line, issue, fix, category. This lets the synthesizer merge and sort findings from all four agents without any post-processing logic.",
  },
  {
    title: "Why Groq over OpenAI",
    body: "Groq's free tier provides 14,400 requests per minute with sub-second response times. Four agents running in parallel would hit OpenAI rate limits quickly. Groq handles concurrent requests cleanly.",
  },
  {
    title: "Why severity-first sorting",
    body: "A critical SQL injection buried after 10 style warnings is a bad user experience. The synthesizer always surfaces the highest severity findings first regardless of which agent returned them.",
  },
];

export default function AboutSection() {
  const problemsRef  = useRef(null);
  const valuesRef    = useRef(null);
  const decisionsRef = useRef(null);
  const stackRef     = useRef(null);

  const problemsInView  = useInView(problemsRef,  { once: true, margin: "-60px" });
  const valuesInView    = useInView(valuesRef,    { once: true, margin: "-60px" });
  const decisionsInView = useInView(decisionsRef, { once: true, margin: "-60px" });
  const stackInView     = useInView(stackRef,     { once: true, margin: "-60px" });

  return (
    <section id="about" className="py-24 px-6 bg-white">
      <div className="max-w-5xl mx-auto">

        {/* What is CodeSense */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5 }}
          className="mb-20"
        >
          <span className="text-xs font-medium text-blue-600 bg-blue-50
                           border border-blue-200 rounded-full px-4 py-1.5">
            About CodeSense
          </span>
          <h2 className="text-3xl font-semibold text-slate-900 mt-6 mb-5 tracking-tight">
            Code review should not be a bottleneck
          </h2>
          <div className="max-w-2xl space-y-4">
            <p className="text-slate-600 text-base leading-relaxed">
              CodeSense is an AI-powered code review system that analyzes
              GitHub pull requests the moment they are opened. Four specialized
              agents inspect the diff in parallel and return a ranked, structured
              report covering security vulnerabilities, performance problems,
              missing test coverage, and style issues.
            </p>
            <p className="text-slate-500 text-base leading-relaxed">
              It works on any public pull request with no setup, no
              configuration, and no login required. Paste a URL, get a review.
            </p>
          </div>
        </motion.div>

        {/* The problem */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.4 }}
          className="mb-8"
        >
          <h2 className="text-2xl font-semibold text-slate-900 tracking-tight mb-2">
            The problem with code review today
          </h2>
          <p className="text-slate-500 text-sm max-w-xl">
            Code review is one of the most valuable and most broken parts
            of the software development process.
          </p>
        </motion.div>

        <div ref={problemsRef} className="grid grid-cols-1 md:grid-cols-3 gap-5 mb-20">
          {PROBLEMS.map((p, i) => (
            <motion.div
              key={p.label}
              initial={{ opacity: 0, y: 20 }}
              animate={problemsInView ? { opacity: 1, y: 0 } : {}}
              transition={{ duration: 0.45, delay: i * 0.1 }}
              className="bg-slate-50 border border-slate-200 rounded-2xl p-6"
            >
              <p className="text-3xl font-bold text-slate-900 mb-1">
                {p.stat}
              </p>
              <p className="text-xs font-semibold text-blue-600 uppercase
                            tracking-wider mb-3">
                {p.label}
              </p>
              <p className="text-sm text-slate-500 leading-relaxed">
                {p.desc}
              </p>
            </motion.div>
          ))}
        </div>

        {/* What CodeSense does about it */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.4 }}
          className="mb-8"
        >
          <h2 className="text-2xl font-semibold text-slate-900 tracking-tight mb-2">
            How CodeSense helps
          </h2>
          <p className="text-slate-500 text-sm max-w-xl">
            Automated first-pass review means your engineers spend their
            time on decisions, not repetitive pattern-matching.
          </p>
        </motion.div>

        <div ref={valuesRef} className="grid grid-cols-1 md:grid-cols-2 gap-5 mb-20">
          {VALUES.map((v, i) => (
            <motion.div
              key={v.title}
              initial={{ opacity: 0, x: i % 2 === 0 ? -16 : 16 }}
              animate={valuesInView ? { opacity: 1, x: 0 } : {}}
              transition={{ duration: 0.45, delay: i * 0.1 }}
              whileHover={{ y: -2, transition: { duration: 0.15 } }}
              className="bg-white border border-slate-200 rounded-2xl p-6"
            >
              <div className="flex items-center gap-3 mb-3">
                <span className="text-xl">{v.icon}</span>
                <h3 className="text-sm font-semibold text-slate-900">
                  {v.title}
                </h3>
              </div>
              <p className="text-sm text-slate-500 leading-relaxed">
                {v.desc}
              </p>
            </motion.div>
          ))}
        </div>

        {/* Engineering decisions */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.4 }}
          className="mb-8"
        >
          <h2 className="text-2xl font-semibold text-slate-900 tracking-tight mb-2">
            How it is built
          </h2>
          <p className="text-slate-500 text-sm">
            Every architectural decision was made to maximize review
            quality and minimize latency.
          </p>
        </motion.div>

        <div ref={decisionsRef} className="grid grid-cols-1 md:grid-cols-2 gap-5 mb-20">
          {DECISIONS.map((d, i) => (
            <motion.div
              key={d.title}
              initial={{ opacity: 0, y: 20 }}
              animate={decisionsInView ? { opacity: 1, y: 0 } : {}}
              transition={{ duration: 0.45, delay: i * 0.1 }}
              className="bg-slate-50 border border-slate-200 rounded-2xl p-6"
            >
              <h3 className="text-sm font-semibold text-slate-900 mb-2">
                {d.title}
              </h3>
              <p className="text-sm text-slate-500 leading-relaxed">
                {d.body}
              </p>
            </motion.div>
          ))}
        </div>

        {/* Tech stack */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.4 }}
          className="mb-8"
        >
          <h2 className="text-2xl font-semibold text-slate-900 tracking-tight mb-2">
            Tech stack
          </h2>
          <p className="text-slate-500 text-sm">
            Every component was chosen for a specific reason.
          </p>
        </motion.div>

        <div ref={stackRef} className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4 mb-20">
          {STACK.map((item, i) => (
            <motion.div
              key={item.label}
              initial={{ opacity: 0, scale: 0.95 }}
              animate={stackInView ? { opacity: 1, scale: 1 } : {}}
              transition={{ duration: 0.35, delay: i * 0.07 }}
              className="bg-white border border-slate-200 rounded-xl px-4 py-3"
            >
              <p className="text-sm font-semibold text-slate-900 mb-0.5">
                {item.label}
              </p>
              <p className="text-xs text-slate-500">
                {item.desc}
              </p>
            </motion.div>
          ))}
        </div>

        {/* CTA */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5 }}
          className="bg-slate-900 rounded-2xl p-8 text-center"
        >
          <h3 className="text-xl font-semibold text-white mb-3">
            Try it on any public PR
          </h3>
          <p className="text-slate-400 text-sm mb-6 max-w-sm mx-auto">
            No login required. Paste any public GitHub pull request URL
            and get a full AI review in seconds.
          </p>
          <a
            href="#review"
            className="inline-block bg-blue-600 hover:bg-blue-500 text-white
                       text-sm font-medium px-6 py-3 rounded-xl
                       transition-colors duration-200"
          >
            Analyze a PR
          </a>
        </motion.div>

      </div>
    </section>
  );
}