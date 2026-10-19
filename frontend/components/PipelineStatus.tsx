"use client";
import { motion, AnimatePresence } from "framer-motion";

type Status = {
  message: string;
  type: "info" | "done" | "error";
};

export default function PipelineStatus({
  statuses,
  loading,
}: {
  statuses: Status[];
  loading: boolean;
}) {
  if (statuses.length === 0) return null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="bg-slate-950 border border-slate-800 rounded-2xl p-5 mb-6"
    >
      <p className="text-xs font-medium text-slate-500 uppercase tracking-wider mb-4">
        Agent pipeline
      </p>

      <div className="space-y-2.5" role="status" aria-live="polite">
        <AnimatePresence>
          {statuses.map((s, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.25, delay: i * 0.05 }}
              className={`flex items-center gap-3 text-sm ${
                s.type === "done"  ? "text-emerald-400" :
                s.type === "error" ? "text-red-400"     : "text-slate-400"
              }`}
            >
              {/* Status icon */}
              <span className="w-4 h-4 flex items-center justify-center shrink-0">
                {s.type === "done"  ? "✓" :
                 s.type === "error" ? "✗" : "·"}
              </span>
              {s.message}
            </motion.div>
          ))}
        </AnimatePresence>

        {/* Animated spinner while loading */}
        {loading && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="flex items-center gap-3 text-slate-500 text-sm"
          >
            <div className="w-4 h-4 border-2 border-slate-700 border-t-blue-500
                            rounded-full animate-spin shrink-0" />
            Running agents in parallel...
          </motion.div>
        )}
      </div>
    </motion.div>
  );
}