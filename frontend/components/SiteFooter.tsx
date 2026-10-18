import AgentIcon from "@/components/AgentIcon";
import { REPO_URL } from "@/lib/site";

const FOCUS = "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-400";

export function FinalCta() {
  return (
    <section className="px-4 sm:px-6 pb-24">
      <div className="max-w-5xl mx-auto rounded-2xl border border-slate-800 bg-gradient-to-b from-slate-900 to-slate-950
                      px-6 py-14 text-center">
        <h2 className="text-3xl font-semibold text-white tracking-tight text-balance">
          Catch it before your reviewers do
        </h2>
        <p className="mt-3 text-slate-400 max-w-md mx-auto">
          Paste any public pull request and get a ranked, fix-ready review in seconds. No sign-up.
        </p>
        <div className="mt-8 flex flex-wrap justify-center gap-3">
          <a href="#review"
             className={`bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium px-6 py-3 rounded-xl
                         transition-colors duration-200 ${FOCUS}`}>
            Analyze a PR
          </a>
          <a href={REPO_URL} target="_blank" rel="noopener noreferrer"
             className={`text-slate-300 hover:text-white text-sm font-medium px-6 py-3 rounded-xl border
                         border-slate-700 hover:border-slate-500 transition-colors duration-200 ${FOCUS}`}>
            View source on GitHub
          </a>
        </div>
      </div>
    </section>
  );
}

export function Footer() {
  return (
    <footer className="border-t border-slate-800 px-4 sm:px-6 py-10">
      <div className="max-w-6xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4 text-sm text-slate-500">
        <span className="flex items-center gap-2">
          <AgentIcon name="search" className="w-4 h-4 text-blue-400" />
          <span className="text-slate-300 font-medium">CodeSense</span>
          <span>· Multi-agent AI code review</span>
        </span>
        <nav aria-label="Footer" className="flex gap-6">
          <a href="#how-it-works" className={`hover:text-white transition-colors ${FOCUS}`}>How it works</a>
          <a href="#faq" className={`hover:text-white transition-colors ${FOCUS}`}>FAQ</a>
          <a href={REPO_URL} target="_blank" rel="noopener noreferrer" className={`hover:text-white transition-colors ${FOCUS}`}>GitHub</a>
        </nav>
      </div>
    </footer>
  );
}
