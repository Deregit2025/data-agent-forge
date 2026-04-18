import Link from "next/link";

const STATS = [
  { label: "Final Pass@1",     value: "44.4%", sub: "24 / 54 queries",   color: "text-forge-amber" },
  { label: "Baseline Leader",  value: "38%",   sub: "Gemini 3 Pro",      color: "text-forge-muted" },
  { label: "Improvement",      value: "+6.4pp",sub: "over the ceiling",  color: "text-forge-green"  },
  { label: "DB Types",         value: "4",     sub: "PG · Mongo · SQLite · DuckDB", color: "text-forge-blue" },
  { label: "Total Tools",      value: "29",    sub: "MCP endpoints",     color: "text-forge-purple" },
  { label: "KB Layers",        value: "3",     sub: "AGENT · Domain · Corrections", color: "text-forge-amber" },
];

const PROBES_SUMMARY = [
  { cat: "A", label: "Multi-DB Routing",        count: 7, color: "bg-blue-900/40 border-blue-500/30 text-blue-300" },
  { cat: "B", label: "Key Mismatch",            count: 4, color: "bg-red-900/40 border-red-500/30 text-red-300" },
  { cat: "C", label: "Unstructured Text",       count: 2, color: "bg-purple-900/40 border-purple-500/30 text-purple-300" },
  { cat: "D", label: "Domain Knowledge Gap",    count: 2, color: "bg-orange-900/40 border-orange-500/30 text-orange-300" },
];

const TIMELINE = [
  { date: "Apr 7",  event: "Sprint 1 Inception — unanimous approval",          tag: "Governance" },
  { date: "Apr 9",  event: "MCP server live — 29 tools across 4 DB types",     tag: "Infra" },
  { date: "Apr 11", event: "True baseline: 1.85% — 4 root causes identified",  tag: "Benchmark" },
  { date: "Apr 13", event: "Post-corrections yelp: 66.7% — mechanics fixed",   tag: "Fix" },
  { date: "Apr 13", event: "Sprint 2 Inception — mob session approval",        tag: "Governance" },
  { date: "Apr 14", event: "KB enrichment: 9 domain files completed",          tag: "KB" },
  { date: "Apr 18", event: "Final benchmark: 44.4% — PR #32 submitted",        tag: "Result" },
];

const TAG_COLORS: Record<string, string> = {
  Governance: "bg-purple-900/50 text-purple-300",
  Infra:      "bg-blue-900/50 text-blue-300",
  Benchmark:  "bg-red-900/50 text-red-300",
  Fix:        "bg-amber-900/50 text-amber-300",
  KB:         "bg-teal-900/50 text-teal-300",
  Result:     "bg-green-900/50 text-green-300",
};

export default function Dashboard() {
  return (
    <div className="max-w-7xl mx-auto px-6 py-10 space-y-12 animate-fade-in">

      {/* ── HERO ── */}
      <section className="relative rounded-2xl border border-forge-border bg-forge-surface overflow-hidden p-10">
        {/* background glow */}
        <div className="absolute inset-0 pointer-events-none">
          <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[600px] h-[300px] bg-forge-amber/5 rounded-full blur-3xl" />
        </div>

        <div className="relative flex flex-col md:flex-row items-start md:items-center justify-between gap-8">
          <div className="space-y-4">
            <div className="flex items-center gap-3">
              <span className="font-mono text-forge-muted text-sm">Team Gemini · TRP1 FDE · April 2026</span>
              <span className="px-2 py-0.5 rounded-full text-xs font-mono bg-forge-amber/10 border border-forge-amber/30 text-forge-amber">
                DAB PR #32
              </span>
            </div>
            <h1 className="text-4xl md:text-5xl font-bold text-white leading-tight">
              Oracle Forge<br />
              <span className="text-forge-amber">Data Agent</span>
            </h1>
            <p className="text-forge-muted max-w-lg text-base leading-relaxed">
              A LangGraph-orchestrated multi-database AI agent with three-layer context engineering,
              typed failure recovery, and a self-learning corrections loop — targeting UC Berkeley's
              DataAgentBench.
            </p>
            <div className="flex gap-3 pt-2">
              <Link href="/demo"
                className="px-5 py-2.5 rounded-lg bg-forge-amber text-forge-bg font-semibold text-sm hover:bg-forge-amber2 transition-colors">
                Live Demo →
              </Link>
              <Link href="/benchmark"
                className="px-5 py-2.5 rounded-lg border border-forge-border text-forge-text text-sm hover:border-forge-amber/50 transition-colors">
                Benchmark Results
              </Link>
            </div>
          </div>

          {/* big score */}
          <div className="flex-shrink-0 text-center">
            <div className="relative">
              <div className="text-8xl md:text-9xl font-black text-forge-amber font-mono leading-none text-glow-amber">
                44.4
                <span className="text-4xl">%</span>
              </div>
              <div className="text-forge-muted text-sm mt-2 font-mono">Pass@1 · 54 queries · 5 trials</div>
              <div className="mt-3 flex items-center justify-center gap-2">
                <div className="h-px w-8 bg-forge-muted/30" />
                <span className="text-forge-muted text-xs">vs Gemini 3 Pro</span>
                <div className="h-px w-8 bg-forge-muted/30" />
              </div>
              <div className="text-forge-muted text-2xl font-mono mt-1">38%</div>
              <div className="mt-2 text-forge-green text-sm font-mono font-semibold">+6.4 pp above ceiling</div>
            </div>
          </div>
        </div>
      </section>

      {/* ── STATS GRID ── */}
      <section className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        {STATS.map(s => (
          <div key={s.label} className="rounded-xl border border-forge-border bg-forge-card p-4 space-y-1">
            <div className={`text-2xl font-black font-mono ${s.color}`}>{s.value}</div>
            <div className="text-forge-text text-sm font-medium">{s.label}</div>
            <div className="text-forge-muted text-xs">{s.sub}</div>
          </div>
        ))}
      </section>

      {/* ── ARCHITECTURE OVERVIEW ── */}
      <section className="rounded-2xl border border-forge-border bg-forge-surface p-8">
        <h2 className="text-xl font-bold text-white mb-6">Architecture — LangGraph State Machine</h2>
        <div className="flex flex-col md:flex-row items-stretch gap-3">
          {[
            { node: "plan_node",      model: "Sonnet 4.6", role: "Reads 3-layer KB → selects tools → orders steps",        color: "border-forge-amber/50 bg-forge-amber/5" },
            { node: "execute_node",   model: "Haiku 3.5",  role: "4 sub-agents run in sequence → prior results chained",   color: "border-blue-500/50 bg-blue-500/5" },
            { node: "correct_node",   model: "Sonnet 4.6", role: "Classifies failures → typed recovery → re-executes",     color: "border-red-500/50 bg-red-500/5" },
            { node: "synthesize_node",model: "Sonnet 4.6", role: "Precompute joins → formats final answer",               color: "border-green-500/50 bg-green-500/5" },
          ].map((n, i) => (
            <div key={n.node} className="flex items-stretch gap-3">
              <div className={`flex-1 rounded-xl border p-4 space-y-2 ${n.color}`}>
                <div className="font-mono text-xs text-forge-muted">{`node ${i + 1}`}</div>
                <div className="font-mono font-semibold text-forge-text text-sm">{n.node}</div>
                <div className="text-xs px-2 py-0.5 rounded bg-forge-bg/50 text-forge-muted inline-block font-mono">
                  {n.model}
                </div>
                <p className="text-forge-muted text-xs leading-relaxed">{n.role}</p>
              </div>
              {i < 3 && (
                <div className="hidden md:flex items-center text-forge-dim text-lg self-center">→</div>
              )}
            </div>
          ))}
        </div>

        {/* KB layers */}
        <div className="mt-6 grid grid-cols-3 gap-3">
          {[
            { layer: "Layer 1", name: "AGENT.md",          desc: "29 tool descriptions, join key glossary, 4 dialect rules",  color: "text-forge-amber" },
            { layer: "Layer 2", name: "dab_*.md (×12)",    desc: "Per-dataset schema, query patterns, critical domain facts",  color: "text-blue-400" },
            { layer: "Layer 3", name: "corrections_log.md",desc: "6 self-learned failure patterns from benchmark runs",        color: "text-green-400" },
          ].map(l => (
            <div key={l.layer} className="rounded-xl border border-forge-border bg-forge-card p-4">
              <div className="text-xs font-mono text-forge-muted mb-1">{l.layer}</div>
              <div className={`font-mono font-semibold text-sm mb-1 ${l.color}`}>{l.name}</div>
              <div className="text-xs text-forge-muted">{l.desc}</div>
            </div>
          ))}
        </div>
      </section>

      {/* ── TWO COLUMNS: PROBES + TIMELINE ── */}
      <div className="grid md:grid-cols-2 gap-6">

        {/* Probe summary */}
        <section className="rounded-2xl border border-forge-border bg-forge-surface p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-bold text-white">Adversarial Probe Library</h2>
            <span className="text-forge-green text-sm font-mono font-semibold">15/15 ✅</span>
          </div>
          <div className="space-y-3">
            {PROBES_SUMMARY.map(p => (
              <div key={p.cat} className={`flex items-center justify-between rounded-lg border p-3 ${p.color}`}>
                <div className="flex items-center gap-3">
                  <span className="font-mono font-bold w-5">{p.cat}</span>
                  <span className="text-sm">{p.label}</span>
                </div>
                <span className="font-mono font-semibold">{p.count} probes</span>
              </div>
            ))}
          </div>
          <Link href="/probes" className="mt-4 block text-center text-forge-amber text-sm hover:underline">
            View all probes →
          </Link>
        </section>

        {/* Timeline */}
        <section className="rounded-2xl border border-forge-border bg-forge-surface p-6">
          <h2 className="text-lg font-bold text-white mb-4">Sprint Timeline</h2>
          <div className="space-y-3">
            {TIMELINE.map((t, i) => (
              <div key={i} className="flex items-start gap-3">
                <span className="font-mono text-forge-muted text-xs pt-0.5 w-12 flex-shrink-0">{t.date}</span>
                <div className="flex-1 flex items-start gap-2">
                  <span className={`text-xs px-1.5 py-0.5 rounded font-mono flex-shrink-0 mt-0.5 ${TAG_COLORS[t.tag]}`}>
                    {t.tag}
                  </span>
                  <span className="text-forge-text text-sm leading-relaxed">{t.event}</span>
                </div>
              </div>
            ))}
          </div>
        </section>
      </div>

      {/* ── QUICK LINKS ── */}
      <section className="grid grid-cols-2 md:grid-cols-4 gap-4 pb-8">
        {[
          { href: "/benchmark",   emoji: "📊", title: "Benchmark",    sub: "Score progression & per-dataset results" },
          { href: "/demo",        emoji: "⚡", title: "Live Demo",    sub: "Query the agent across all 12 datasets" },
          { href: "/probes",      emoji: "🔬", title: "Probe Library",sub: "All 15 adversarial probes + fixes" },
          { href: "/corrections", emoji: "📝", title: "Corrections",  sub: "Self-learning loop — 6 KB corrections" },
        ].map(card => (
          <Link key={card.href} href={card.href}
            className="rounded-xl border border-forge-border bg-forge-card p-5 hover:border-forge-amber/40 hover:bg-forge-surface transition-all group">
            <div className="text-2xl mb-2">{card.emoji}</div>
            <div className="font-semibold text-forge-text group-hover:text-forge-amber transition-colors">{card.title}</div>
            <div className="text-forge-muted text-xs mt-1">{card.sub}</div>
          </Link>
        ))}
      </section>
    </div>
  );
}
