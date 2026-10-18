"use client";
import dynamic from "next/dynamic";
import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import Navigation     from "@/components/Navigation";
import PipelineStatus from "@/components/PipelineStatus";
import FindingCard    from "@/components/FindingCard";
import AgentPanel     from "@/components/AgentPanel";
import HowItWorks     from "@/components/HowItWorks";
import AboutSection   from "@/components/AboutSection";
import HeroBackground from "@/components/HeroBackground";

const HeroPreview = dynamic(() => import("@/components/HeroPreview"), {
  ssr: false,
});

const API = "http://localhost:8002";

type Severity = "critical" | "high" | "medium" | "low";
type Finding = {
  severity: Severity;
  file: string;
  line: number;
  issue: string;
  fix: string;
  category: string;
  agent: string;
};
type Report = {
  pr_title: string;
  author: string;
  total_findings: number;
  by_severity: Record<Severity, number>;
  by_agent: Record<string, number>;
  findings: Finding[];
  summary: string;
};
type Status = { message: string; type: "info" | "done" | "error" };

const SEVERITY_ORDER: Record<Severity, number> = {
  critical: 0, high: 1, medium: 2, low: 3,
};

export default function Home() {
  const [prUrl, setPrUrl]       = useState("");
  const [loading, setLoading]   = useState(false);
  const [report, setReport]     = useState<Report | null>(null);
  const [statuses, setStatuses] = useState<Status[]>([]);
  const [filter, setFilter]     = useState("all");

  function addStatus(message: string, type: Status["type"] = "info") {
    setStatuses(prev => [...prev, { message, type }]);
  }

  async function analyze() {
    if (!prUrl.trim() || loading) return;
    setLoading(true);
    setReport(null);
    setStatuses([]);
    setFilter("all");

    try {
      const res = await fetch(`${API}/review/stream`, {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify({ pr_url: prUrl.trim() }),
      });
      if (!res.ok) throw new Error(`Server error: ${res.status}`);
      const reader  = res.body!.getReader();
      const decoder = new TextDecoder();
      let   buffer  = "";
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n\n");
        buffer = lines.pop() || "";
        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          const payload = line.slice(6);
          if (payload === "[DONE]") break;
          try {
            const data = JSON.parse(payload);
            if (data.status === "starting")      addStatus("Fetching PR from GitHub...");
            if (data.status === "diff_fetched")  addStatus(`✓ ${data.message}`, "done");
            if (data.status === "security_done") addStatus(`✓ ${data.message}`, "done");
            if (data.status === "perf_done")     addStatus(`✓ ${data.message}`, "done");
            if (data.status === "test_done")     addStatus(`✓ ${data.message}`, "done");
            if (data.status === "style_done")    addStatus(`✓ ${data.message}`, "done");
            if (data.status === "error")         addStatus(`✗ ${data.message}`, "error");
            if (data.status === "agent_failed")  addStatus(`✗ ${data.message}`, "error");
            if (data.status === "complete" && data.report) {
              setReport(data.report);
              addStatus("Analysis complete", "done");
            }
          } catch { /* skip malformed */ }
        }
      }
    } catch (err: unknown) {
      addStatus(err instanceof Error ? err.message : "Failed to reach backend", "error");
    } finally {
      setLoading(false);
    }
  }

  const filteredFindings = (report?.findings ?? [])
    .filter(f => filter === "all" || f.agent === filter || f.severity === filter)
    .sort((a, b) => SEVERITY_ORDER[a.severity] - SEVERITY_ORDER[b.severity]);

  return (
    <div className="min-h-screen bg-slate-950">
      <Navigation />

      {/* Hero */}
      <section className="relative pt-24 pb-4 px-6 overflow-hidden">
        <HeroBackground />
        <div className="relative z-10 max-w-6xl mx-auto grid grid-cols-1 lg:grid-cols-2
                        gap-12 items-center min-h-[520px]">

          {/* Left: text */}
          <motion.div
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, ease: "easeOut" }}
            className="text-center lg:text-left"
          >
            <motion.span
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 0.2, duration: 0.4 }}
              className="inline-block text-xs font-medium text-blue-400 bg-blue-500/10
                         border border-blue-500/20 rounded-full px-4 py-1.5 mb-6"
            >
              Multi-agent AI code review
            </motion.span>

            <motion.h1
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3, duration: 0.5 }}
              className="text-4xl lg:text-5xl font-semibold text-white mb-5
                         tracking-tight leading-tight"
            >
              Code review that{" "}
              <span className="text-transparent bg-clip-text
                               bg-gradient-to-r from-blue-400 to-cyan-400">
                thinks in parallel
              </span>
            </motion.h1>

            <motion.p
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.4, duration: 0.5 }}
              className="text-base text-slate-400 mb-8 leading-relaxed
                         max-w-lg mx-auto lg:mx-0"
            >
              Four specialized agents analyze your GitHub PR simultaneously.
              Security, performance, test coverage, and style - in under 30 seconds.
            </motion.p>

            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.5, duration: 0.5 }}
              className="flex items-center gap-4 flex-wrap mb-10
                         justify-center lg:justify-start"
            >
              {["🔒 Security", "⚡ Performance", "🧪 Testing", "✏️ Style"].map(label => (
                <span key={label} className="text-sm text-slate-500">{label}</span>
              ))}
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.6, duration: 0.4 }}
              className="flex gap-3 justify-center lg:justify-start"
            >
              <a href="#review"
                 className="bg-blue-600 hover:bg-blue-500 text-white text-sm
                            font-medium px-6 py-3 rounded-xl transition-colors duration-200">
                Analyze a PR
              </a>
              <a href="#how-it-works"
                 className="text-slate-400 hover:text-white text-sm font-medium
                            px-6 py-3 rounded-xl border border-slate-800
                            hover:border-slate-600 transition-all duration-200">
                How it works
              </a>
            </motion.div>
          </motion.div>

          {/* Right: product preview — desktop only */}
          <div className="hidden lg:block">
            <HeroPreview />
          </div>

        </div>
      </section>

      <HowItWorks />
      <AboutSection />

      {/* Review tool */}
      <section id="review" className="max-w-5xl mx-auto px-6 pb-24 pt-8">
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5 }}
          className="text-center mb-10"
        >
          <span className="text-xs font-medium text-blue-400 bg-blue-500/10
                           border border-blue-500/20 rounded-full px-4 py-1.5">
            Try it now
          </span>
          <h2 className="text-3xl font-semibold text-white mt-6 mb-3 tracking-tight">
            Analyze any public PR
          </h2>
          <p className="text-slate-400 text-sm max-w-md mx-auto">
            No login required. Paste any public GitHub pull request URL below.
          </p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5 }}
          className="bg-slate-900 border border-slate-800 rounded-2xl p-6 mb-6"
        >
          <label className="block text-sm font-medium text-slate-300 mb-3">
            GitHub Pull Request URL
          </label>
          <div className="flex gap-3">
            <input
              value={prUrl}
              onChange={e => setPrUrl(e.target.value)}
              onKeyDown={e => e.key === "Enter" && analyze()}
              placeholder="https://github.com/owner/repo/pull/123"
              disabled={loading}
              className="flex-1 bg-slate-800 border border-slate-700 rounded-xl
                         px-4 py-3 text-sm text-white placeholder-slate-500
                         focus:outline-none focus:ring-2 focus:ring-blue-500
                         focus:border-transparent disabled:opacity-50
                         transition-all duration-200"
            />
            <motion.button
              whileTap={{ scale: 0.97 }}
              onClick={analyze}
              disabled={loading || !prUrl.trim()}
              className="bg-blue-600 hover:bg-blue-500 text-white px-6 py-3
                         rounded-xl text-sm font-medium disabled:opacity-40
                         disabled:cursor-not-allowed transition-colors
                         duration-200 whitespace-nowrap"
            >
              {loading ? "Analyzing..." : "Analyze PR"}
            </motion.button>
          </div>
        </motion.div>

        <PipelineStatus statuses={statuses} loading={loading} />

        <AnimatePresence>
          {report && (
            <motion.div
              key="report"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.3 }}
            >
              <AgentPanel report={report} filter={filter} setFilter={setFilter} />
              {filteredFindings.length === 0 ? (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="bg-slate-900 border border-slate-800 rounded-2xl p-12 text-center"
                >
                  <p className="text-slate-500 text-sm">No issues found for this filter.</p>
                </motion.div>
              ) : (
                <div className="space-y-3">
                  {filteredFindings.map((f, i) => (
                    <FindingCard key={i} finding={f} index={i} />
                  ))}
                </div>
              )}
            </motion.div>
          )}
        </AnimatePresence>

        {!report && !loading && statuses.length === 0 && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.3 }}
            className="text-center py-24"
          >
            <p className="text-5xl mb-5">🔍</p>
            <h2 className="text-lg font-medium text-slate-300 mb-2">
              Paste a GitHub PR URL to get started
            </h2>
            <p className="text-sm text-slate-500 max-w-md mx-auto">
              Four AI agents analyze your PR in parallel. Security vulnerabilities,
              performance issues, missing tests, and style problems.
            </p>
          </motion.div>
        )}
      </section>

      <footer className="border-t border-slate-800 py-8 px-6 text-center">
        <p className="text-sm text-slate-500">
          CodeSense - Multi-agent AI code review - Built with LangGraph, Groq, FastAPI, and Next.js
        </p>
      </footer>
    </div>
  );
}