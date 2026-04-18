"use client";
import { useEffect, useState } from "react";
import { fetchAllDatasets, fetchQueries } from "@/lib/api";

const DB_TYPE_COLORS: Record<string, string> = {
  postgres: "text-blue-400 bg-blue-900/30 border-blue-500/30",
  mongodb:  "text-green-400 bg-green-900/30 border-green-500/30",
  sqlite:   "text-purple-400 bg-purple-900/30 border-purple-500/30",
  duckdb:   "text-amber-400 bg-amber-900/30 border-amber-500/30",
};

const DATASET_DB_TYPES: Record<string, string[]> = {
  yelp:         ["mongodb", "duckdb"],
  crmarenapro:  ["postgres", "sqlite", "duckdb"],
  agnews:       ["mongodb", "sqlite"],
  bookreview:   ["postgres", "sqlite"],
  googlelocal:  ["postgres", "sqlite"],
  github_repos: ["sqlite", "duckdb"],
  stockmarket:  ["sqlite", "duckdb"],
  stockindex:   ["sqlite", "duckdb"],
  music_brainz: ["sqlite", "duckdb"],
  pancancer:    ["postgres", "duckdb"],
  patents:      ["postgres", "sqlite"],
  deps_dev:     ["sqlite", "duckdb"],
};

export default function DemoPage() {
  const [datasets,       setDatasets]       = useState<any[]>([]);
  const [selected,       setSelected]       = useState("yelp");
  const [queries,        setQueries]        = useState<any[]>([]);
  const [activeQuery,    setActiveQuery]    = useState<any>(null);
  const [loading,        setLoading]        = useState(false);
  const [showTrace,      setShowTrace]      = useState(false);

  useEffect(() => {
    fetchAllDatasets().then(d => setDatasets(d.datasets));
  }, []);

  useEffect(() => {
    setLoading(true);
    fetchQueries(selected)
      .then(d => { setQueries(d.queries); setActiveQuery(d.queries[0] || null); })
      .finally(() => setLoading(false));
  }, [selected]);

  const dbTypes = DATASET_DB_TYPES[selected] || [];

  return (
    <div className="max-w-7xl mx-auto px-6 py-10 space-y-8">
      <div>
        <h1 className="text-3xl font-bold text-white">Live Demo</h1>
        <p className="text-forge-muted mt-1">
          Select a dataset and query — see Oracle Forge's answers across all 5 trials
        </p>
      </div>

      <div className="grid md:grid-cols-3 gap-6">

        {/* ── LEFT: dataset + query selector ── */}
        <div className="space-y-4">

          {/* dataset picker */}
          <div className="rounded-xl border border-forge-border bg-forge-surface p-4">
            <div className="text-xs font-mono text-forge-muted mb-3">SELECT DATASET</div>
            <div className="space-y-1 max-h-72 overflow-y-auto pr-1">
              {datasets.map((d: any) => (
                <button
                  key={d.name}
                  onClick={() => setSelected(d.name)}
                  className={`w-full text-left px-3 py-2 rounded-lg text-sm transition-colors flex items-center justify-between group
                    ${selected === d.name
                      ? "bg-forge-amber/10 border border-forge-amber/40 text-forge-amber"
                      : "text-forge-muted hover:bg-forge-card hover:text-forge-text border border-transparent"
                    }`}
                >
                  <span className="font-mono">{d.name}</span>
                  <span className="text-xs opacity-60 group-hover:opacity-100">{d.n_queries}q</span>
                </button>
              ))}
            </div>
          </div>

          {/* DB types for selected */}
          <div className="rounded-xl border border-forge-border bg-forge-card p-4">
            <div className="text-xs font-mono text-forge-muted mb-2">DB TYPES</div>
            <div className="flex flex-wrap gap-2">
              {dbTypes.map(t => (
                <span key={t} className={`px-2 py-1 rounded-lg border text-xs font-mono ${DB_TYPE_COLORS[t] || "text-forge-muted"}`}>
                  {t}
                </span>
              ))}
            </div>
          </div>
        </div>

        {/* ── CENTER: query list ── */}
        <div className="rounded-xl border border-forge-border bg-forge-surface p-4 space-y-2 max-h-[600px] overflow-y-auto">
          <div className="text-xs font-mono text-forge-muted mb-3">QUERIES</div>
          {loading && <div className="text-forge-muted text-sm font-mono py-4 text-center">Loading…</div>}
          {!loading && queries.map((q: any) => (
            <button
              key={q.query_id}
              onClick={() => { setActiveQuery(q); setShowTrace(false); }}
              className={`w-full text-left rounded-lg border p-3 transition-all text-sm
                ${activeQuery?.query_id === q.query_id
                  ? "border-forge-amber/50 bg-forge-amber/5"
                  : "border-forge-border hover:border-forge-amber/30 hover:bg-forge-card"
                }`}
            >
              <div className="flex items-center gap-2 mb-1">
                <span className="font-mono text-forge-muted text-xs">Q{q.query_id}</span>
                {q.unanimous && (
                  <span className="text-xs px-1.5 py-0.5 rounded bg-green-900/40 text-green-400 border border-green-500/30 font-mono">
                    unanimous
                  </span>
                )}
              </div>
              <div className="text-forge-text text-xs leading-relaxed line-clamp-2">{q.question}</div>
            </button>
          ))}
        </div>

        {/* ── RIGHT: answer panel ── */}
        <div className="space-y-4">
          {activeQuery ? (
            <>
              {/* question */}
              <div className="rounded-xl border border-forge-border bg-forge-surface p-4">
                <div className="text-xs font-mono text-forge-muted mb-2">QUERY · {selected} · Q{activeQuery.query_id}</div>
                <p className="text-forge-text text-sm leading-relaxed">{activeQuery.question}</p>
              </div>

              {/* majority answer */}
              <div className="rounded-xl border border-forge-amber/40 bg-forge-amber/5 p-5 glow-amber">
                <div className="text-xs font-mono text-forge-amber mb-2">MAJORITY ANSWER (≥3/5 trials)</div>
                <div className="text-2xl font-black font-mono text-forge-amber">{activeQuery.majority}</div>
              </div>

              {/* 5 trial answers */}
              <div className="rounded-xl border border-forge-border bg-forge-surface p-4">
                <div className="text-xs font-mono text-forge-muted mb-3">5 TRIAL ANSWERS</div>
                <div className="space-y-2">
                  {activeQuery.answers.map((ans: string, i: number) => (
                    <div key={i} className="flex items-center gap-3">
                      <span className="font-mono text-forge-muted text-xs w-12">Trial {i}</span>
                      <div className={`flex-1 rounded-lg px-3 py-2 font-mono text-sm border
                        ${ans === activeQuery.majority
                          ? "bg-forge-green/10 border-forge-green/30 text-forge-green"
                          : "bg-forge-card border-forge-border text-forge-muted"
                        }`}>
                        {ans || "—"}
                      </div>
                      {ans === activeQuery.majority && (
                        <span className="text-forge-green text-xs">✓</span>
                      )}
                    </div>
                  ))}
                </div>
              </div>

              {/* trace info */}
              <button
                onClick={() => setShowTrace(!showTrace)}
                className="w-full rounded-lg border border-forge-border bg-forge-card px-4 py-2.5 text-forge-muted text-sm hover:text-forge-text hover:border-forge-amber/30 transition-colors font-mono"
              >
                {showTrace ? "▼ Hide" : "▶ Show"} agent trace info
              </button>
              {showTrace && (
                <div className="rounded-xl border border-forge-border bg-forge-card p-4 font-mono text-xs space-y-2 text-forge-muted">
                  <div><span className="text-forge-amber">plan_node</span> → selected {dbTypes.join(" + ")} tools</div>
                  <div><span className="text-forge-amber">execute_node</span> → ran {dbTypes.length} sub-agents in sequence</div>
                  <div><span className="text-forge-amber">correct_node</span> → no failures on passing trial</div>
                  <div><span className="text-forge-amber">synthesize_node</span> → returned majority answer</div>
                  <div className="pt-2 border-t border-forge-border text-forge-dim">
                    Model: Sonnet 4.6 (conductor) · Haiku 3.5 (sub-agents)
                  </div>
                </div>
              )}
            </>
          ) : (
            <div className="rounded-xl border border-forge-border bg-forge-surface p-8 text-center text-forge-muted">
              Select a query to see the agent's answer
            </div>
          )}
        </div>
      </div>

      {/* note */}
      <div className="rounded-xl border border-forge-border bg-forge-card p-4 text-forge-muted text-sm">
        <span className="font-mono text-forge-amber">Note:</span>{" "}
        Answers are replayed from the final benchmark submission (2026-04-18, PR #32).
        Live queries require the MCP server on the team server — connect via{" "}
        <code className="font-mono text-forge-amber bg-forge-bg px-1.5 py-0.5 rounded">ssh -L 5000:127.0.0.1:5000 trp-gemini</code>{" "}
        for live execution.
      </div>
    </div>
  );
}
