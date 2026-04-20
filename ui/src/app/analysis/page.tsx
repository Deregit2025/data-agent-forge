"use client";
import { useState } from "react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Cell, PieChart, Pie, Legend,
} from "recharts";

const GREEN  = "#22c55e";
const RED    = "#ef4444";
const BLUE   = "#3b82f6";
const PURPLE = "#8b5cf6";

// ── failure data (derived from dab_submission.json vs ground truth) ──────────
const FAILURE_MODES = [
  { name: "No Answer (N/A)",   count: 13, color: RED,    desc: "Agent returned N/A — query too complex or schema gap" },
  { name: "Gave Up",           count: 6,  color: "#f97316", desc: "Agent printed 'I need to:' — planning incomplete" },
  { name: "Wrong Value",       count: 7,  color: PURPLE, desc: "Answered but value numerically or categorically wrong" },
  { name: "Wrong Format",      count: 4,  color: BLUE,   desc: "Correct entity but wrong structure or ordering" },
];

const DATASET_FAIL = [
  { name: "crmarenapro", pass: 5, fail: 8 },
  { name: "yelp",        pass: 3, fail: 4 },
  { name: "stockmarket", pass: 3, fail: 2 },
  { name: "googlelocal", pass: 3, fail: 1 },
  { name: "github_repos",pass: 2, fail: 2 },
  { name: "music_brainz",pass: 2, fail: 1 },
  { name: "stockindex",  pass: 2, fail: 1 },
  { name: "agnews",      pass: 2, fail: 2 },
  { name: "deps_dev",    pass: 2, fail: 0 },
  { name: "pancancer",   pass: 0, fail: 3 },
  { name: "patents",     pass: 0, fail: 3 },
  { name: "bookreview",  pass: 0, fail: 3 },
];

// ── component status ─────────────────────────────────────────────────────────
const COMPONENTS = [
  {
    name: "autoDream",
    file: "utils/autodream.py",
    status: "wired",
    when: "Post-eval only",
    color: "border-green-500/40 bg-green-900/10 text-green-400",
    desc: "Reads corrections_log.md, calls Claude Sonnet to integrate patterns into dab_*.md KB files. Invoked by harness after each benchmark session via --no_autodream flag.",
    call: "python -m utils.autodream",
  },
  {
    name: "contract_validator",
    file: "utils/contract_validator.py",
    status: "unwired",
    when: "Designed for synthesize_node",
    color: "border-red-500/40 bg-red-900/10 text-red-400",
    desc: "Would validate every MCP tool response schema: result[], row_count, query_used, error. Not wired because the MCP server proved reliable and KB enrichment had higher ROI. CONTRACT_VIOLATION is the rarest failure type.",
    call: "never called",
  },
  {
    name: "entity_resolver",
    file: "utils/entity_resolver.py",
    status: "unwired",
    when: "Designed for cross-DB joins",
    color: "border-red-500/40 bg-red-900/10 text-red-400",
    desc: "Would auto-detect and fix foreign key prefix mismatches (businessid_ → businessref_). The specific fix was hardcoded directly in duckdb_agent.py PREFIX RULE — more reliable than dynamic resolution.",
    call: "never called",
  },
  {
    name: "multi_pass_retrieval",
    file: "utils/multi_pass_retrieval.py",
    status: "unwired",
    when: "Designed for EMPTY_RESULT recovery",
    color: "border-red-500/40 bg-red-900/10 text-red-400",
    desc: "Would iteratively rewrite queries that return 0 rows, trying looser filters, different columns, or alternative aggregations. recovery_router.py covers this at Level 1 (sub-agent) instead.",
    call: "never called",
  },
];


export default function AnalysisPage() {
  const [openComp, setOpenComp] = useState<string | null>(null);

  return (
    <div className="max-w-7xl mx-auto px-6 py-10 space-y-12">

      {/* header */}
      <div>
        <h1 className="text-3xl font-bold text-white">System Analysis</h1>
        <p className="text-forge-muted mt-1">Full flow, execution traces, failure taxonomy, component wiring, and self-learning loop</p>
      </div>

      {/* ── 1. FULL PIPELINE FLOW ─────────────────────────────────────────── */}
      <section className="rounded-2xl border border-forge-border bg-forge-surface p-8">
        <h2 className="text-xl font-bold text-white mb-6">End-to-End Pipeline</h2>
        <div className="flex flex-col gap-1">
          {[
            { label: "DAB Harness",     sub: "Loads query.json + validate.py · spawns OracleForgeAgent · 5 trials",   color: "border-forge-amber/40 bg-forge-amber/5",  side: "eval/harness.py" },
            { label: "load_context()",  sub: "Injects 3-layer KB: AGENT.md + dab_*.md + corrections_log.md",          color: "border-blue-500/40 bg-blue-900/10",        side: "agent/context.py" },
            { label: "plan_node",       sub: "Claude Sonnet 4.6 — reads full KB, selects 1-4 tools, orders steps",    color: "border-amber-500/40 bg-amber-900/10",      side: "No SQL generated" },
            { label: "execute_node",    sub: "Claude Haiku 3.5 — runs sub-agents sequentially, chains prior results", color: "border-blue-500/40 bg-blue-900/10",        side: "agent/nodes/execute.py" },
            { label: "Sub-agent × N",   sub: "generate query → POST /v1/tools/{tool} → result · max 2 retries (Level 1)", color: "border-purple-500/40 bg-purple-900/10", side: "recovery_router.py" },
            { label: "correct_node",    sub: "Claude Sonnet 4.6 — re-reads KB, fixes failed steps (Level 2)",         color: "border-red-500/40 bg-red-900/10",          side: "Only if error != null" },
            { label: "synthesize_node", sub: "Precompute dispatch for 8 datasets · short-circuit bypasses LLM",       color: "border-green-500/40 bg-green-900/10",      side: "agent/nodes/synthesize.py" },
            { label: "validate.py",     sub: "DAB's own validator — compare majority answer to ground truth",          color: "border-forge-border bg-forge-card",        side: "ucbepic/DataAgentBench" },
          ].map((step, i, arr) => (
            <div key={step.label}>
              <div className={`rounded-xl border p-4 flex items-center justify-between gap-4 ${step.color}`}>
                <div className="flex items-center gap-3 min-w-0">
                  <span className="font-mono text-forge-muted text-sm w-5 flex-shrink-0">{i + 1}</span>
                  <div>
                    <span className="font-mono font-bold text-forge-text">{step.label}</span>
                    <p className="text-xs text-forge-muted mt-0.5 leading-relaxed">{step.sub}</p>
                  </div>
                </div>
                <span className="font-mono text-xs text-forge-muted flex-shrink-0 hidden md:block">{step.side}</span>
              </div>
              {i < arr.length - 1 && <div className="text-center text-forge-dim py-0.5">↓</div>}
            </div>
          ))}
        </div>
      </section>

      {/* ── 2. RECOVERY ARCHITECTURE ─────────────────────────────────────── */}
      <section className="rounded-2xl border border-forge-border bg-forge-surface p-8">
        <h2 className="text-xl font-bold text-white mb-2">Two-Level Recovery Architecture</h2>
        <p className="text-forge-muted text-sm mb-6">Failure classification is deterministic — no LLM needed for classify()</p>
        <div className="grid md:grid-cols-2 gap-6">
          <div className="rounded-xl border border-orange-500/40 bg-orange-900/10 p-5 space-y-3">
            <div className="font-mono font-bold text-orange-400">Level 1 — Sub-agent Internal Retry</div>
            <div className="text-xs text-forge-muted space-y-1">
              <div className="flex gap-2"><span className="text-orange-400">Model:</span><span>Claude Haiku 3.5</span></div>
              <div className="flex gap-2"><span className="text-orange-400">Trigger:</span><span>error != null in MCP response</span></div>
              <div className="flex gap-2"><span className="text-orange-400">Max retries:</span><span>2 per step</span></div>
              <div className="flex gap-2"><span className="text-orange-400">Strategy:</span><span>Classify error type → targeted rewrite of just the failed query</span></div>
            </div>
            <div className="rounded-lg bg-forge-bg border border-forge-border p-3 font-mono text-xs text-forge-muted space-y-1">
              <div><span className="text-orange-400">classify(error)</span> → QUERY_SYNTAX_ERROR</div>
              <div><span className="text-orange-400">recover()</span> → rewrite with corrected syntax</div>
              <div><span className="text-orange-400">execute()</span> → retry MCP call</div>
            </div>
          </div>
          <div className="rounded-xl border border-red-500/40 bg-red-900/10 p-5 space-y-3">
            <div className="font-mono font-bold text-red-400">Level 2 — correct_node (Full Context)</div>
            <div className="text-xs text-forge-muted space-y-1">
              <div className="flex gap-2"><span className="text-red-400">Model:</span><span>Claude Sonnet 4.6</span></div>
              <div className="flex gap-2"><span className="text-red-400">Trigger:</span><span>Level 1 exhausted (2 retries failed)</span></div>
              <div className="flex gap-2"><span className="text-red-400">Context:</span><span>Full 3-layer KB re-injected</span></div>
              <div className="flex gap-2"><span className="text-red-400">Strategy:</span><span>Root cause analysis with full schema + domain knowledge</span></div>
            </div>
            <div className="rounded-lg bg-forge-bg border border-forge-border p-3 font-mono text-xs text-forge-muted space-y-1">
              <div><span className="text-red-400">load_context()</span> → full KB</div>
              <div><span className="text-red-400">diagnose(failed_steps)</span> → root cause</div>
              <div><span className="text-red-400">rewrite + re-execute()</span></div>
            </div>
          </div>
        </div>

        {/* failure taxonomy */}
        <div className="mt-6">
          <div className="text-sm font-semibold text-forge-text mb-3">10-Type Failure Taxonomy (deterministic classify — no LLM)</div>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-2">
            {[
              { type: "QUERY_SYNTAX_ERROR",  conf: "High",   color: "text-red-400 bg-red-900/20 border-red-500/30" },
              { type: "JOIN_KEY_MISMATCH",   conf: "High",   color: "text-orange-400 bg-orange-900/20 border-orange-500/30" },
              { type: "SCHEMA_MISMATCH",     conf: "High",   color: "text-red-400 bg-red-900/20 border-red-500/30" },
              { type: "DATABASE_TYPE_ERROR", conf: "High",   color: "text-yellow-400 bg-yellow-900/20 border-yellow-500/30" },
              { type: "PIPELINE_ERROR",      conf: "High",   color: "text-amber-400 bg-amber-900/20 border-amber-500/30" },
              { type: "EMPTY_RESULT",        conf: "Medium", color: "text-blue-400 bg-blue-900/20 border-blue-500/30" },
              { type: "DATA_TYPE_ERROR",     conf: "Medium", color: "text-blue-400 bg-blue-900/20 border-blue-500/30" },
              { type: "TIMEOUT",             conf: "Low",    color: "text-purple-400 bg-purple-900/20 border-purple-500/30" },
              { type: "CONTRACT_VIOLATION",  conf: "Low",    color: "text-purple-400 bg-purple-900/20 border-purple-500/30" },
              { type: "UNKNOWN",             conf: "Low",    color: "text-forge-muted bg-forge-card border-forge-border" },
            ].map(f => (
              <div key={f.type} className={`rounded-lg border p-2 text-center ${f.color}`}>
                <div className="font-mono text-xs font-semibold leading-tight">{f.type}</div>
                <div className={`text-xs mt-0.5 ${f.conf === "High" ? "text-green-400" : f.conf === "Medium" ? "text-amber-400" : "text-forge-muted"}`}>{f.conf}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── 3. FAILURE ANALYSIS ──────────────────────────────────────────── */}
      <section className="rounded-2xl border border-forge-border bg-forge-surface p-8">
        <h2 className="text-xl font-bold text-white mb-2">Failure Analysis — 30 Failed Queries</h2>
        <p className="text-forge-muted text-sm mb-6">Derived by comparing dab_submission.json majority answers against ground truth</p>

        <div className="grid md:grid-cols-2 gap-8">
          {/* pie chart */}
          <div>
            <div className="text-sm font-semibold text-forge-text mb-3">Failure Mode Distribution</div>
            <div className="h-56">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={FAILURE_MODES} dataKey="count" nameKey="name" cx="50%" cy="50%" outerRadius={90} label={({ count }) => `${count}`}>
                    {FAILURE_MODES.map((f, i) => <Cell key={i} fill={f.color} />)}
                  </Pie>
                  <Tooltip contentStyle={{ background: "#141c24", border: "1px solid #1e2d3d", borderRadius: 8 }} formatter={(v: any, n: any) => [v, n]} />
                  <Legend formatter={(v) => <span className="text-xs text-forge-muted">{v}</span>} />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div className="space-y-2 mt-2">
              {FAILURE_MODES.map(f => (
                <div key={f.name} className="flex items-start gap-2">
                  <div className="w-2 h-2 rounded-full mt-1.5 flex-shrink-0" style={{ background: f.color }} />
                  <div>
                    <span className="text-xs font-mono font-semibold" style={{ color: f.color }}>{f.name} ({f.count})</span>
                    <p className="text-xs text-forge-muted">{f.desc}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* per-dataset bar chart */}
          <div>
            <div className="text-sm font-semibold text-forge-text mb-3">Pass / Fail per Dataset</div>
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={DATASET_FAIL} layout="vertical" margin={{ left: 20, right: 10 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e2d3d" horizontal={false} />
                  <XAxis type="number" tick={{ fill: "#64748b", fontSize: 10 }} domain={[0, 13]} />
                  <YAxis type="category" dataKey="name" tick={{ fill: "#94a3b8", fontSize: 10 }} width={80} />
                  <Tooltip contentStyle={{ background: "#141c24", border: "1px solid #1e2d3d", borderRadius: 8 }} />
                  <Bar dataKey="pass" name="Pass" stackId="a" fill={GREEN} />
                  <Bar dataKey="fail" name="Fail" stackId="a" fill={RED} radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      </section>

      {/* ── 4. AUTODREAM SELF-LEARNING LOOP ──────────────────────────────── */}
      <section className="rounded-2xl border border-forge-border bg-forge-surface p-8">
        <h2 className="text-xl font-bold text-white mb-2">autoDream — Self-Learning Loop</h2>
        <p className="text-forge-muted text-sm mb-6">
          <span className="text-green-400 font-mono">REAL AND WIRED</span> — runs post-eval via harness, not during live agent execution
        </p>
        <div className="grid md:grid-cols-4 gap-3 mb-6">
          {[
            { step: "1", label: "Agent Fails",    desc: "Query returns wrong answer or error in benchmark run",           color: "border-red-500/40 bg-red-900/10" },
            { step: "2", label: "Driver Logs",    desc: "Wrong/Correct/Impact triple written to corrections_log.md",      color: "border-amber-500/40 bg-amber-900/10" },
            { step: "3", label: "autoDream Runs", desc: "Claude Sonnet reads corrections + KB, integrates into dab_*.md", color: "border-blue-500/40 bg-blue-900/10" },
            { step: "4", label: "Next Run Loads", desc: "load_context() injects updated KB before every plan_node call",  color: "border-green-500/40 bg-green-900/10" },
          ].map(s => (
            <div key={s.step} className={`rounded-xl border p-4 text-center ${s.color}`}>
              <div className="text-2xl font-black font-mono text-forge-muted">{s.step}</div>
              <div className="font-semibold text-forge-text text-sm mt-1">{s.label}</div>
              <div className="text-forge-muted text-xs mt-1 leading-tight">{s.desc}</div>
            </div>
          ))}
        </div>
        <div className="rounded-lg bg-forge-bg border border-forge-border p-3 font-mono text-xs text-forge-muted">
          <span className="text-forge-amber">$ </span>python -m utils.autodream
          <span className="text-forge-muted ml-4"># run after every benchmark session — 6 corrections integrated</span>
        </div>
        <div className="mt-4 grid md:grid-cols-3 gap-3">
          {[
            { phase: "Before autoDream", score: "1.85%", n: "1/54" },
            { phase: "After yelp corrections", score: "66.7%", n: "2/3 yelp" },
            { phase: "After full KB enrichment", score: "44.4%", n: "24/54" },
          ].map(r => (
            <div key={r.phase} className="rounded-lg bg-forge-card border border-forge-border p-3 text-center">
              <div className="font-mono font-bold text-forge-amber text-lg">{r.score}</div>
              <div className="text-forge-text text-xs">{r.phase}</div>
              <div className="text-forge-muted text-xs font-mono">{r.n}</div>
            </div>
          ))}
        </div>
      </section>

      {/* ── 7. COMPONENT STATUS ───────────────────────────────────────────── */}
      <section className="rounded-2xl border border-forge-border bg-forge-surface p-8">
        <h2 className="text-xl font-bold text-white mb-2">Component Status — Wired vs Designed</h2>
        <p className="text-forge-muted text-sm mb-6">Honest accounting of what runs in production vs what was designed but not integrated</p>
        <div className="space-y-3">
          {COMPONENTS.map(c => {
            const open = openComp === c.name;
            return (
              <div key={c.name} className={`rounded-xl border ${c.color} overflow-hidden`}>
                <button
                  className="w-full text-left p-4 flex items-center justify-between gap-4"
                  onClick={() => setOpenComp(open ? null : c.name)}
                >
                  <div className="flex items-center gap-4">
                    <span className={`font-mono font-bold text-sm ${c.color.split(" ")[0].replace("border-", "text-").replace("/40", "")}`}>
                      {c.status === "wired" ? "✅ WIRED" : "⚠ NOT WIRED"}
                    </span>
                    <span className="font-mono font-semibold text-forge-text">{c.name}</span>
                    <span className="text-xs text-forge-muted font-mono hidden md:block">{c.file}</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-xs text-forge-muted">{c.when}</span>
                    <span className="text-forge-muted">{open ? "▼" : "▶"}</span>
                  </div>
                </button>
                {open && (
                  <div className="px-4 pb-4 border-t border-forge-border/30 pt-3 space-y-3">
                    <p className="text-sm text-forge-muted leading-relaxed">{c.desc}</p>
                    <div className="rounded-lg bg-forge-bg border border-forge-border p-2 font-mono text-xs text-forge-muted">
                      <span className="text-forge-amber">$ </span>{c.call}
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
        <div className="mt-4 rounded-xl border border-forge-border bg-forge-card p-4">
          <div className="text-sm font-semibold text-forge-text mb-2">Why three utilities remain unwired</div>
          <p className="text-xs text-forge-muted leading-relaxed">
            All three (contract_validator, entity_resolver, multi_pass_retrieval) were designed before the benchmark revealed the actual failure distribution.
            The dominant failures were <span className="text-forge-amber">domain knowledge gaps</span> and <span className="text-forge-amber">N/A responses</span> —
            not contract violations or entity mismatches. Time was redirected to KB enrichment and autoDream, which had higher ROI.
            The prefix mismatch (JOIN_KEY_MISMATCH) was fixed directly in duckdb_agent.py rather than via entity_resolver.
          </p>
        </div>
      </section>

      {/* ── 8. HARNESS ARCHITECTURE ──────────────────────────────────────── */}
      <section className="rounded-2xl border border-forge-border bg-forge-surface p-8">
        <h2 className="text-xl font-bold text-white mb-2">Harness Architecture</h2>
        <p className="text-forge-muted text-sm mb-6">eval/harness.py orchestrates all 54 queries × 5 trials and writes structured results</p>
        <div className="grid md:grid-cols-3 gap-4">
          {[
            {
              label: "Query Loop",
              color: "border-forge-amber/40 bg-forge-amber/5",
              items: ["Iterates DataAgentBench/query_*/queryN/", "Loads query.json for question text", "Calls OracleForgeAgent.run() 5 times", "Collects answers into trial list"],
            },
            {
              label: "Scoring",
              color: "border-blue-500/40 bg-blue-900/10",
              items: ["score() calls query's validate.py", "majority_pass = ≥3/5 trials correct", "pass_at_1 = any single trial correct", "per_query and per_dataset aggregated"],
            },
            {
              label: "Post-Run",
              color: "border-green-500/40 bg-green-900/10",
              items: ["Writes eval/results/benchmark_*.json", "Updates eval/results/latest.json", "Appends to eval/score_log.jsonl", "Runs autoDream (unless --no_autodream)"],
            },
          ].map(s => (
            <div key={s.label} className={`rounded-xl border p-4 ${s.color}`}>
              <div className="font-mono font-bold text-forge-text mb-3">{s.label}</div>
              <ul className="space-y-1.5">
                {s.items.map(item => (
                  <li key={item} className="text-xs text-forge-muted flex gap-1.5"><span className="flex-shrink-0">→</span>{item}</li>
                ))}
              </ul>
            </div>
          ))}
        </div>
        <div className="mt-4 rounded-lg bg-forge-bg border border-forge-border p-3 font-mono text-xs text-forge-muted space-y-1">
          <div><span className="text-forge-amber">$ </span>python -m eval.harness --datasets yelp crmarenapro --n_trials 5</div>
          <div><span className="text-forge-amber">$ </span>python -m eval.harness --all_datasets --n_trials 5 --no_early_stop</div>
        </div>
      </section>

    </div>
  );
}
