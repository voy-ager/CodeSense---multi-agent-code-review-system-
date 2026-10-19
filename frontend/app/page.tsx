"use client";
import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import Navigation     from "@/components/Navigation";
import PipelineStatus from "@/components/PipelineStatus";
import FindingCard    from "@/components/FindingCard";
import AgentPanel     from "@/components/AgentPanel";
import HowItWorks     from "@/components/HowItWorks";
import AboutSection   from "@/components/AboutSection";
import CodeReviewHero from "@/components/CodeReviewHero";
import AgentIcon      from "@/components/AgentIcon";
import FaqSection     from "@/components/FaqSection";
import { FinalCta, Footer } from "@/components/SiteFooter";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8002";

const EXAMPLE_PR = "https://github.com/psf/requests/pull/6746";
const DONE_STATUSES = ["diff_fetched", "security_done", "perf_done", "test_done", "style_done", "static_done"];

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
  diff_truncated?: boolean;
  failed_agents?: string[];
  stale?: boolean;
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

  async function analyze(url = prUrl) {
    if (!url.trim() || loading) return;
    setLoading(true);
    setReport(null);
    setStatuses([]);
    setFilter("all");

    try {
      const res = await fetch(`${API}/review/stream`, {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify({ pr_url: url.trim() }),
      });
      if (!res.ok) {
        // FastAPI/SlowAPI errors carry a human-readable reason in "detail" (string or
        // validation list) or "error".
        const body = await res.json().catch(() => ({}));
        const detail = typeof body.detail === "string" ? body.detail
          : Array.isArray(body.detail) ? body.detail.map((d: { msg?: string }) => d.msg).filter(Boolean).join("; ")
          : body.error;
        throw new Error(detail || `Server error: ${res.status}`);
      }
      const reader  = res.body!.getReader();
      const decoder = new TextDecoder();
      let   buffer  = "";
      let   settled = false;   // got a final "complete" or "error"
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
            // PipelineStatus draws the ✓/✗ icon, so messages go in unprefixed.
            if (DONE_STATUSES.includes(data.status)) addStatus(data.message, "done");
            if (data.status === "error" || data.status === "agent_failed") addStatus(data.message, "error");
            if (data.status === "error") settled = true;
            if (data.status === "complete" && data.report) {
              settled = true;
              setReport(data.report);
              addStatus("Analysis complete", "done");
            }
          } catch { /* skip malformed */ }
        }
      }
      if (!settled) addStatus("Connection lost before the review finished — please try again", "error");
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

      <CodeReviewHero />

      {/* Review tool — right after the hero: trying it is the main conversion */}
      <section id="review" className="max-w-5xl mx-auto px-4 sm:px-6 py-24 scroll-mt-14">
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
          <label htmlFor="pr-url" className="block text-sm font-medium text-slate-300 mb-3">
            GitHub Pull Request URL
          </label>
          <div className="flex flex-col sm:flex-row gap-3">
            <input
              id="pr-url"
              type="url"
              inputMode="url"
              autoComplete="off"
              value={prUrl}
              onChange={e => setPrUrl(e.target.value)}
              onKeyDown={e => e.key === "Enter" && analyze()}
              placeholder="https://github.com/owner/repo/pull/123"
              disabled={loading}
              className="flex-1 min-w-0 bg-slate-800 border border-slate-700 rounded-xl
                         px-4 py-3 text-base sm:text-sm text-white placeholder-slate-500
                         focus:outline-none focus:ring-2 focus:ring-blue-500
                         focus:border-transparent disabled:opacity-50
                         transition-all duration-200"
            />
            <motion.button
              whileTap={{ scale: 0.97 }}
              onClick={() => analyze()}
              disabled={loading || !prUrl.trim()}
              className="bg-blue-600 hover:bg-blue-500 text-white px-6 py-3
                         rounded-xl text-sm font-medium disabled:opacity-40
                         disabled:cursor-not-allowed transition-colors
                         duration-200 whitespace-nowrap"
            >
              {loading ? "Analyzing..." : "Analyze PR"}
            </motion.button>
          </div>
          <p className="mt-3 text-sm text-slate-500">
            No PR handy?{" "}
            <button
              type="button"
              disabled={loading}
              onClick={() => { setPrUrl(EXAMPLE_PR); analyze(EXAMPLE_PR); }}
              className="text-blue-400 hover:text-blue-300 underline underline-offset-4 cursor-pointer
                         disabled:opacity-40 disabled:cursor-not-allowed"
            >
              Try an example from psf/requests
            </button>
          </p>
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
            className="text-center py-16"
          >
            <AgentIcon name="search" className="w-12 h-12 mx-auto mb-5 text-slate-600" />
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

      <HowItWorks />
      <AboutSection />
      <FaqSection />
      <FinalCta />
      <Footer />
    </div>
  );
}