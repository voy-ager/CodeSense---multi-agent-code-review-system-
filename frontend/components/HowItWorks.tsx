"use client";
import AgentIcon from "@/components/AgentIcon";
import { motion, useInView } from "framer-motion";
import { useRef } from "react";

const AGENTS = [
  {
    icon: "security",
    name: "Security agent",
    color: "from-red-500/20 to-red-500/5 border-red-500/20",
    iconBg: "bg-red-500/20",
    checks: [
      "SQL injection and XSS vulnerabilities",
      "Hardcoded secrets and API keys",
      "Missing authentication checks",
      "Use of dangerous functions",
    ],
  },
  {
    icon: "performance",
    name: "Performance agent",
    color: "from-yellow-500/20 to-yellow-500/5 border-yellow-500/20",
    iconBg: "bg-yellow-500/20",
    checks: [
      "O(n2) algorithms and nested loops",
      "N+1 database query patterns",
      "Blocking calls in async contexts",
      "Unnecessary object copies",
    ],
  },
  {
    icon: "testing",
    name: "Testing agent",
    color: "from-green-500/20 to-green-500/5 border-green-500/20",
    iconBg: "bg-green-500/20",
    checks: [
      "Untested functions and branches",
      "Missing edge cases and null inputs",
      "Untested error and failure paths",
      "Tests that cannot fail",
    ],
  },
  {
    icon: "style",
    name: "Style agent",
    color: "from-blue-500/20 to-blue-500/5 border-blue-500/20",
    iconBg: "bg-blue-500/20",
    checks: [
      "Misleading variable names",
      "Magic numbers and strings",
      "Functions longer than 30 lines",
      "Dead and unreachable code",
    ],
  },
];

const STEPS = [
  {
    number: "01",
    title: "Paste a PR URL",
    description:
      "Drop any public GitHub pull request URL into the input. CodeSense fetches the unified diff directly from the GitHub API.",
  },
  {
    number: "02",
    title: "Four agents run in parallel",
    description:
      "Security, performance, testing, and style agents analyze the diff simultaneously, alongside rule-based checks for secrets, risky dependencies, and prompt injection. Total time is determined by the slowest single agent, not the sum.",
  },
  {
    number: "03",
    title: "Findings ranked by severity",
    description:
      "Results from all four agents are merged and sorted by severity. Critical issues always appear first regardless of which agent found them.",
  },
];

export default function HowItWorks() {
  const stepsRef = useRef(null);
  const agentsRef = useRef(null);
  const stepsInView = useInView(stepsRef, { once: true, margin: "-80px" });
  const agentsInView = useInView(agentsRef, { once: true, margin: "-80px" });

  return (
    <section id="how-it-works" className="py-24 px-6">
      <div className="max-w-5xl mx-auto">

        {/* Section label */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5 }}
          className="text-center mb-16"
        >
          <span className="text-xs font-medium text-blue-400 bg-blue-500/10
                           border border-blue-500/20 rounded-full px-4 py-1.5">
            How it works
          </span>
          <h2 className="text-3xl font-semibold text-white mt-6 mb-4 tracking-tight">
            From PR to review in three steps
          </h2>
          <p className="text-slate-400 max-w-lg mx-auto text-base leading-relaxed">
            No configuration. No setup. Paste a URL and four specialized
            agents get to work immediately.
          </p>
        </motion.div>

        {/* Steps */}
        <div ref={stepsRef} className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-20">
          {STEPS.map((step, i) => (
            <motion.div
              key={step.number}
              initial={{ opacity: 0, y: 24 }}
              animate={stepsInView ? { opacity: 1, y: 0 } : {}}
              transition={{ duration: 0.5, delay: i * 0.12 }}
              className="bg-slate-900 border border-slate-800 rounded-2xl p-6"
            >
              <span className="text-3xl font-bold text-slate-700 block mb-4">
                {step.number}
              </span>
              <h3 className="text-base font-semibold text-white mb-2">
                {step.title}
              </h3>
              <p className="text-sm text-slate-400 leading-relaxed">
                {step.description}
              </p>
            </motion.div>
          ))}
        </div>

        {/* Agent cards */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5 }}
          className="text-center mb-10"
        >
          <h2 className="text-2xl font-semibold text-white tracking-tight">
            Four agents, one parallel pipeline
          </h2>
          <p className="text-slate-400 mt-3 text-sm max-w-md mx-auto">
            Each agent is specialized and independent. They never block each other.
          </p>
        </motion.div>

        <div ref={agentsRef} className="grid grid-cols-1 md:grid-cols-2 gap-5">
          {AGENTS.map((agent, i) => (
            <motion.div
              key={agent.name}
              initial={{ opacity: 0, x: i % 2 === 0 ? -20 : 20 }}
              animate={agentsInView ? { opacity: 1, x: 0 } : {}}
              transition={{ duration: 0.5, delay: i * 0.1 }}
              whileHover={{ y: -3, transition: { duration: 0.2 } }}
              className={`bg-gradient-to-br ${agent.color} border rounded-2xl p-6`}
            >
              <div className="flex items-center gap-3 mb-4">
                <div className={`w-10 h-10 ${agent.iconBg} rounded-xl
                                 flex items-center justify-center text-xl`}>
                  <AgentIcon name={agent.icon} className="w-5 h-5 text-white" />
                </div>
                <h3 className="text-base font-semibold text-white">
                  {agent.name}
                </h3>
              </div>
              <ul className="space-y-2">
                {agent.checks.map((check) => (
                  <li key={check} className="flex items-start gap-2 text-sm text-slate-300">
                    <span className="text-slate-500 mt-0.5 shrink-0">+</span>
                    {check}
                  </li>
                ))}
              </ul>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}