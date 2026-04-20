export default function ArchitecturePage() {
  return (
    <div className="max-w-7xl mx-auto px-6 py-10 space-y-10">
      <div>
        <h1 className="text-3xl font-bold text-white">Architecture</h1>
        <p className="text-forge-muted mt-1">Five subsystems — all designed before the first line of agent code was written</p>
      </div>

      {/* LangGraph flow */}
      <div className="rounded-2xl border border-forge-border bg-forge-surface p-8">
        <h2 className="text-xl font-bold text-white mb-6">LangGraph State Machine</h2>

        <div className="flex flex-col gap-4">
          {[
            {
              node: "plan_node", model: "Claude Sonnet 4.6", color: "border-amber-500/50 bg-amber-900/10",
              inputs: ["Natural language question", "3-layer KB context (AGENT.md + dab_*.md + corrections_log.md)"],
              outputs: ["Ordered execution steps", "Tool selection (1–4 DB tools)"],
              detail: "Reads the full three-layer KB before generating a plan. Never generates SQL — only selects tools and describes step purposes.",
            },
            {
              node: "execute_node", model: "Claude Haiku 3.5", color: "border-blue-500/50 bg-blue-900/10",
              inputs: ["Execution plan", "Prior results from previous steps (ALL IDs, no truncation)"],
              outputs: ["Tool results with row counts", "Step trace with query_used + error"],
              detail: "Runs sub-agents sequentially. Each sub-agent: generate query → execute via MCP → recover if failed (max 2 retries). Prior results chained via 'prior' list.",
            },
            {
              node: "correct_node", model: "Claude Sonnet 4.6", color: "border-red-500/50 bg-red-900/10",
              inputs: ["Failed tool results (error != null)", "Full 3-layer KB context"],
              outputs: ["Corrected queries", "Re-executed results"],
              detail: "Level-2 correction using Sonnet (full context). Level-1 is sub-agent internal retry with Haiku. Failure type classified deterministically (no LLM needed for classification).",
            },
            {
              node: "synthesize_node", model: "Claude Sonnet 4.6", color: "border-green-500/50 bg-green-900/10",
              inputs: ["All tool results", "Precompute dispatch (8 datasets)"],
              outputs: ["Final natural language answer"],
              detail: "Precompute functions for 8 datasets bypass LLM for precise numeric aggregations. Short-circuit returns the answer directly without synthesis when precompute succeeds.",
            },
          ].map((n, i) => (
            <div key={n.node}>
              <div className={`rounded-xl border p-5 ${n.color}`}>
                <div className="flex items-center gap-4 mb-4">
                  <span className="font-mono text-forge-muted text-sm">node {i + 1}</span>
                  <span className="font-mono font-bold text-forge-text">{n.node}</span>
                  <span className="px-2 py-0.5 rounded bg-forge-bg/60 font-mono text-xs text-forge-muted border border-forge-border">{n.model}</span>
                </div>
                <div className="grid md:grid-cols-3 gap-4">
                  <div>
                    <div className="text-xs font-mono text-forge-muted mb-2">INPUTS</div>
                    <ul className="space-y-1">
                      {n.inputs.map(inp => <li key={inp} className="text-xs text-forge-text flex gap-1"><span className="text-forge-muted">→</span>{inp}</li>)}
                    </ul>
                  </div>
                  <div>
                    <div className="text-xs font-mono text-forge-muted mb-2">OUTPUTS</div>
                    <ul className="space-y-1">
                      {n.outputs.map(out => <li key={out} className="text-xs text-forge-text flex gap-1"><span className="text-forge-green">←</span>{out}</li>)}
                    </ul>
                  </div>
                  <div>
                    <div className="text-xs font-mono text-forge-muted mb-2">DETAIL</div>
                    <p className="text-xs text-forge-muted leading-relaxed">{n.detail}</p>
                  </div>
                </div>
              </div>
              {i < 3 && <div className="text-center text-forge-dim text-xl py-1">↓</div>}
            </div>
          ))}
        </div>
      </div>

      {/* MCP server */}
      <div className="rounded-2xl border border-forge-border bg-forge-surface p-8">
        <h2 className="text-xl font-bold text-white mb-2">MCP Server — Unified HTTP Contract</h2>
        <p className="text-forge-muted text-sm mb-6">29 tools across 4 DB types — one interface, one response format</p>

        <div className="grid md:grid-cols-2 gap-6">
          {/* contract */}
          <div className="rounded-xl bg-forge-bg border border-forge-border p-4 font-mono text-xs space-y-2">
            <div className="text-forge-amber">POST /v1/tools/{"{tool_name}"}</div>
            <div className="text-forge-muted pl-4">{"{"}</div>
            <div className="text-forge-text pl-8">"sql": "SELECT AVG(rating) FROM ..."</div>
            <div className="text-forge-muted pl-4">{"}"}</div>
            <div className="text-forge-muted">———————————————</div>
            <div className="text-forge-amber">Response (all 4 DB types):</div>
            <div className="text-forge-muted pl-4">{"{"}</div>
            <div className="text-forge-text pl-8">"result": [<span className="text-forge-amber">...</span>],</div>
            <div className="text-forge-text pl-8">"row_count": <span className="text-forge-amber">N</span>,</div>
            <div className="text-forge-text pl-8">"query_used": <span className="text-forge-amber">"..."</span>,</div>
            <div className="text-forge-text pl-8">"error": <span className="text-forge-green">null</span></div>
            <div className="text-forge-muted pl-4">{"}"}</div>
          </div>

          {/* tool breakdown */}
          <div className="space-y-3">
            {[
              { type: "PostgreSQL", count: 5,  color: "text-blue-400",   bg: "bg-blue-900/20 border-blue-500/30",   datasets: "bookreview, crmarenapro, googlelocal, pancancer, patents" },
              { type: "MongoDB",    count: 3,  color: "text-green-400",  bg: "bg-green-900/20 border-green-500/30",  datasets: "yelp (business, checkin), agnews" },
              { type: "SQLite",     count: 12, color: "text-purple-400", bg: "bg-purple-900/20 border-purple-500/30", datasets: "All 12 datasets — metadata + reference data" },
              { type: "DuckDB",     count: 9,  color: "text-amber-400",  bg: "bg-amber-900/20 border-amber-500/30",  datasets: "yelp, crmarenapro, pancancer, stockmarket, stockindex, deps_dev, github_repos, music_brainz" },
            ].map(t => (
              <div key={t.type} className={`rounded-xl border p-3 flex items-center justify-between ${t.bg}`}>
                <div>
                  <div className={`font-mono font-bold text-sm ${t.color}`}>{t.type}</div>
                  <div className="text-xs text-forge-muted mt-0.5">{t.datasets}</div>
                </div>
                <div className={`font-black font-mono text-2xl ${t.color}`}>{t.count}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

    </div>
  );
}
