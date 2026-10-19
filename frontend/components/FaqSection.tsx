"use client";
// Adapted from 21st.dev "FAQ Accordion Reveal" (Hirael faq-06, MIT, Mohammad Shehadeh).
// Uses native <details> instead of Radix Accordion: same keyboard/screen-reader
// behaviour, zero extra dependencies.
import { motion, MotionConfig } from "framer-motion";
import { REPO_URL } from "@/lib/site";

const HEADLINE = "Answers before you ask";

const FAQS = [
  {
    q: "Is my code stored?",
    a: "The PR diff is sent to the LLM provider (Groq) for analysis and is not saved. The resulting report (findings, PR title, author) is cached for one hour and kept in the review history.",
  },
  {
    q: "Which pull requests can I review?",
    a: "Any public GitHub pull request. Paste the PR link; the /files or /commits tab URLs work too.",
  },
  {
    q: "How long does a review take?",
    a: "Usually 5–30 seconds, depending on the size of the diff and model load. Reviewing the same PR again within an hour returns the cached report instantly.",
  },
  {
    q: "Can a malicious PR trick the reviewer?",
    a: "It can try. The diff is passed to the model as fenced, untrusted data, and rule-based checks flag text aimed at AI reviewers and invisible Unicode. Those rules don't use the model, so they can't be talked out of a finding.",
  },
  {
    q: "What does it catch that a typical AI reviewer misses?",
    a: "Dependencies that don't exist or were published days ago (slopsquatting), secrets hidden as lists of numbers, and bidirectional or zero-width characters that make code read differently than it runs.",
  },
  {
    q: "Can I use it from my editor?",
    a: "Yes. Run mcp_server.py and add it to Claude Desktop, Cursor, or VS Code as an MCP server; it exposes a review_pull_request tool.",
  },
  {
    q: "What happens with very large PRs?",
    a: "The AI agents review the first 8,000 characters of the diff and the report says so. Rule-based checks always scan the whole diff.",
  },
  {
    q: "What if one of the agents fails?",
    a: "The report is marked incomplete and names the failed agent. CodeSense never presents a failed review as a clean PR, and incomplete reports are not cached.",
  },
  {
    q: "Which model runs the agents?",
    a: "openai/gpt-oss-120b on Groq by default. The model is a single environment variable, so it can be swapped without code changes.",
  },
] as const;

const EASE = "easeOut" as const;

export default function FaqSection() {
  const words = HEADLINE.split(" ");
  const half = Math.floor(words.length / 2);

  return (
    <MotionConfig reducedMotion="user">
      <section id="faq" className="py-24 px-4 sm:px-6 border-t border-slate-800/60 scroll-mt-14">
        <div className="mx-auto w-full max-w-3xl">
          <div className="mb-10 flex flex-col items-center gap-5 text-center">
            <motion.span
              initial={{ opacity: 0, scale: 0.9 }}
              whileInView={{ opacity: 1, scale: 1 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, ease: EASE, delay: 0.1 }}
              className="rounded-full border border-slate-800 bg-slate-900/70 px-4 py-1.5 font-mono
                         text-[11px] uppercase tracking-[0.14em] text-slate-400"
            >
              FAQ
            </motion.span>
            <h2 className="mx-auto max-w-3xl text-balance text-3xl sm:text-4xl font-semibold tracking-tight">
              {words.map((word, i) => (
                <motion.span
                  key={`${word}-${i}`}
                  className={`me-[0.25em] inline-block ${i < half ? "text-slate-500" : "text-white"}`}
                  initial={{ opacity: 0, y: 16 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.5, ease: EASE, delay: 0.15 + i * 0.08 }}
                >
                  {word}
                </motion.span>
              ))}
            </h2>
            <p className="mx-auto max-w-2xl text-pretty text-base text-slate-400">
              What teams ask before pointing CodeSense at their pull requests. Still unsure?{" "}
              <a href={`${REPO_URL}/issues`} target="_blank" rel="noopener noreferrer"
                 className="text-blue-400 hover:text-blue-300 underline underline-offset-4">
                Open an issue
              </a>.
            </p>
          </div>

          <div className="flex flex-col gap-3">
            {FAQS.map((item, i) => (
              <motion.details
                key={item.q}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.45, ease: EASE, delay: i * 0.08 }}
                className="group rounded-xl border border-slate-800 bg-slate-900 px-4 md:px-6
                           transition-colors open:bg-slate-800/50 open:border-slate-700"
              >
                <summary
                  className="flex min-h-11 cursor-pointer list-none items-center justify-between gap-6 py-4
                             text-left text-base font-medium text-slate-100 md:text-lg
                             focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-blue-400
                             [&::-webkit-details-marker]:hidden"
                >
                  {item.q}
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}
                       strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"
                       className="h-4 w-4 shrink-0 text-slate-400 transition-transform duration-200 group-open:rotate-180">
                    <path d="m6 9 6 6 6-6" />
                  </svg>
                </summary>
                <p className="pb-5 text-base leading-relaxed text-slate-400">{item.a}</p>
              </motion.details>
            ))}
          </div>
        </div>
      </section>
    </MotionConfig>
  );
}
