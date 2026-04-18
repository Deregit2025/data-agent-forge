"use client";
import { useEffect, useState } from "react";
import { fetchCorrections } from "@/lib/api";

export default function CorrectionsPage() {
  const [data,    setData]    = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchCorrections().then(d => { setData(d); setLoading(false); });
  }, []);

  const corrections: any[] = data?.corrections || [];

  return (
    <div className="max-w-7xl mx-auto px-6 py-10 space-y-8">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white">Self-Learning Corrections Log</h1>
          <p className="text-forge-muted mt-1">
            Structured failure patterns written after the April 11 baseline — consolidated by <code className="font-mono text-forge-amber">autoDream</code> into KB domain files
          </p>
        </div>
        <div className="text-right">
          <div className="text-3xl font-black font-mono text-forge-green">{corrections.length}</div>
          <div className="text-forge-muted text-sm">corrections applied</div>
        </div>
      </div>

      {/* autoDream loop diagram */}
      <div className="rounded-2xl border border-forge-border bg-forge-surface p-6">
        <h2 className="text-lg font-bold text-white mb-4">The autoDream Self-Learning Loop</h2>
        <div className="flex flex-col md:flex-row items-stretch gap-2">
          {[
            { step: "1", label: "Agent Fails",      desc: "Query returns 0 rows or wrong answer",     color: "border-red-500/40 bg-red-900/10" },
            { step: "2", label: "Driver Logs",      desc: "Wrong / Correct / Impact written to corrections_log.md", color: "border-amber-500/40 bg-amber-900/10" },
            { step: "3", label: "autoDream Runs",   desc: "Claude Sonnet integrates corrections into dab_*.md KB", color: "border-blue-500/40 bg-blue-900/10" },
            { step: "4", label: "Next Run Loads",   desc: "load_context() injects updated KB before every query", color: "border-green-500/40 bg-green-900/10" },
          ].map((s, i) => (
            <div key={s.step} className="flex items-stretch gap-2">
              <div className={`flex-1 rounded-xl border p-4 text-center space-y-1 ${s.color}`}>
                <div className="text-2xl font-black font-mono text-forge-muted">{s.step}</div>
                <div className="font-semibold text-forge-text text-sm">{s.label}</div>
                <div className="text-forge-muted text-xs leading-tight">{s.desc}</div>
              </div>
              {i < 3 && <div className="hidden md:flex items-center text-forge-dim text-xl">→</div>}
            </div>
          ))}
        </div>
        <div className="mt-4 rounded-lg bg-forge-card border border-forge-border p-3 font-mono text-xs text-forge-muted">
          <span className="text-forge-amber">$ </span>python -m utils.autodream
          <span className="text-forge-muted ml-4"># run after every benchmark session</span>
        </div>
      </div>

      {/* correction cards */}
      {loading && <div className="text-forge-muted font-mono py-8">Loading corrections…</div>}
      <div className="space-y-4">
        {corrections.map((c: any, i: number) => (
          <div key={i} className="rounded-2xl border border-forge-border bg-forge-surface overflow-hidden">
            {/* header */}
            <div className="flex items-center justify-between px-5 py-3 border-b border-forge-border bg-forge-card">
              <div className="flex items-center gap-3">
                <span className="font-mono font-bold text-forge-amber text-sm">#{i + 1}</span>
                <span className="font-mono text-forge-amber text-sm">{c.dataset}</span>
                <span className="text-forge-muted text-xs font-mono">{c.date}</span>
              </div>
              <span className="text-xs px-2 py-0.5 rounded-full bg-green-900/40 border border-green-500/30 text-green-400 font-mono">
                ✅ Applied
              </span>
            </div>

            <div className="p-5 grid md:grid-cols-3 gap-5">
              {/* Wrong */}
              <div>
                <div className="flex items-center gap-2 mb-2">
                  <div className="w-2 h-2 rounded-full bg-red-400" />
                  <span className="text-xs font-mono text-red-400 font-semibold">WRONG</span>
                </div>
                <p className="text-forge-muted text-xs leading-relaxed">{c.wrong}</p>
              </div>

              {/* Correct */}
              <div>
                <div className="flex items-center gap-2 mb-2">
                  <div className="w-2 h-2 rounded-full bg-green-400" />
                  <span className="text-xs font-mono text-green-400 font-semibold">CORRECT</span>
                </div>
                <p className="text-forge-text text-xs leading-relaxed">{c.correct}</p>
              </div>

              {/* Impact */}
              <div>
                <div className="flex items-center gap-2 mb-2">
                  <div className="w-2 h-2 rounded-full bg-blue-400" />
                  <span className="text-xs font-mono text-blue-400 font-semibold">IMPACT</span>
                </div>
                <div className="text-forge-muted text-xs leading-relaxed font-mono whitespace-pre-wrap">
                  {c.impact}
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* score impact */}
      <div className="rounded-2xl border border-forge-border bg-forge-surface p-6">
        <h2 className="text-lg font-bold text-white mb-4">Score Impact of the Corrections Loop</h2>
        <div className="space-y-3">
          {[
            { phase: "Before corrections (Baseline)",   score: "1.85%",  n: "1/54",  note: "4 simultaneous root causes active", color: "text-red-400" },
            { phase: "After yelp corrections (3 queries)", score: "66.7%", n: "2/3",   note: "All yelp mechanics fixed", color: "text-forge-amber" },
            { phase: "Final benchmark (54 queries)",    score: "44.4%",  n: "24/54", note: "All 12 KB files enriched + bugs fixed", color: "text-forge-green" },
          ].map(r => (
            <div key={r.phase} className="flex items-center gap-4">
              <div className={`font-mono font-bold text-lg w-20 flex-shrink-0 ${r.color}`}>{r.score}</div>
              <div className="flex-1">
                <div className="text-forge-text text-sm font-medium">{r.phase}</div>
                <div className="text-forge-muted text-xs">{r.n} · {r.note}</div>
              </div>
              <div className="w-32 h-2 rounded-full bg-forge-border overflow-hidden flex-shrink-0">
                <div
                  className="h-full rounded-full bg-forge-amber"
                  style={{ width: `${parseFloat(r.score) / 70 * 100}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
