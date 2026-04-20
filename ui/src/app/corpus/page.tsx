"use client";
import { useState } from "react";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from "recharts";

// ── data ─────────────────────────────────────────────────────────────────────

const THREADS = [
  {
    id: "T1", date: "2026-04-10", week: 1,
    title: "Kickoff — Architecture Plan",
    type: "X Thread (7 posts)",
    url: "https://x.com/GeminiTrp1/status/2042522406699360407",
    impressions: 81, engagements: 15,
    summary: "Introduced Oracle Forge — three-layer context system, LangGraph conductor, MCP toolbox for 4 DB types. Framed the 38% DAB ceiling as an engineering problem, not a model capability problem.",
    color: "border-forge-amber/40 bg-forge-amber/5 text-forge-amber",
  },
  {
    id: "T2", date: "2026-04-10", week: 1,
    title: "Layer 2 Institutional Knowledge",
    type: "X Quote Retweet",
    url: "https://x.com/GeminiTrp1/status/2042557438755278919",
    impressions: 12, engagements: 3,
    summary: "Schema metadata alone is insufficient. Domain definitions — 'active customer = purchased within 90-day window' — must be maintained as institutional knowledge, not derived from schema.",
    color: "border-blue-500/40 bg-blue-900/10 text-blue-400",
  },
  {
    id: "T3", date: "2026-04-11", week: 1,
    title: "MCP Toolbox Gap Analysis",
    type: "X Thread (6 posts)",
    url: "https://x.com/GeminiTrp1/status/2043026176432545821",
    impressions: 20, engagements: 6,
    summary: "Analysis of Google MCP Toolbox v0.30.0 gaps: missing DuckDB support, silent exit on flag syntax changes, arbitrary SQL restriction blocking multi-database joins. Reason for building custom MCP server.",
    color: "border-purple-500/40 bg-purple-900/10 text-purple-400",
  },
  {
    id: "T4", date: "2026-04-13", week: 1,
    title: "Typed Failure Routing",
    type: "X Thread",
    url: "https://x.com/GeminiTrp1/status/2043655547207999759",
    impressions: 8, engagements: 4,
    summary: "Typed failure routing (JoinKeyMismatch, ContractViolation, etc.) vs generic retry loops. Sub-agent specialists for 4 DB types — each generates correct query syntax for its dialect.",
    color: "border-orange-500/40 bg-orange-900/10 text-orange-400",
  },
  {
    id: "T5", date: "2026-04-15", week: 2,
    title: "Divide & Conquer — 12 Datasets",
    type: "X Thread",
    url: "https://x.com/GeminiTrp1/status/2044325128297746825",
    impressions: 30, engagements: 12,
    summary: "6 team members each own 2 datasets. Manual domain knowledge enrichment per dataset. Pooled API keys for parallel testing. Each member runs their own agent while sharing KB patterns.",
    color: "border-green-500/40 bg-green-900/10 text-green-400",
  },
  {
    id: "T6", date: "2026-04-18", week: 2,
    title: "Final Score — Official Submission",
    type: "X Thread",
    url: "https://x.com/GeminiTrp1/status/2045565250519355522",
    impressions: 13, engagements: 2,
    summary: "44.4% pass@1 on the UC Berkeley DataAgentBench leaderboard — PR #32 merged. Final metrics, repo link, and team credits.",
    color: "border-forge-green/40 bg-green-900/10 text-forge-green",
  },
];

const ARTICLES = [
  {
    date: "2026-04-12", platform: "Medium", week: 1,
    title: "We're Trying to Beat Gemini 3 Pro on a Public Benchmark",
    author: "Rafia Kedir",
    url: "https://medium.com/@rafia_k./were-trying-to-beat-gemini-3-pro-on-a-public-benchmark-26f844bc9bf1",
    reach: 2,
    summary: "Kickoff article — architectural decisions made before writing a single line of agent code. Explains the three-layer KB bet and typed failure taxonomy as design choices for the 38% ceiling problem.",
    quote: "We made two architectural bets before writing a single line of agent code: multi-layer context injection, and a failure taxonomy that classifies before it corrects.",
    color: "border-blue-500/40 bg-blue-900/10",
  },
  {
    date: "2026-04-12", platform: "ReadyTensor", week: 1,
    title: "We're Trying to Beat Gemini 3 Pro (cross-post)",
    author: "Rafia Kedir",
    url: "https://app.readytensor.ai/publications/were-trying-to-beat-gemini-3-pro-on-a-public-benchmark-w29HwYbedo5Y",
    reach: 3,
    summary: "Cross-post of the Medium kickoff article for the AI practitioner community on ReadyTensor.",
    quote: null,
    color: "border-blue-500/40 bg-blue-900/10",
  },
  {
    date: "2026-04-18", platform: "LinkedIn", week: 2,
    title: "What the DataAgentBench Taught Me About Enterprise Data Reality",
    author: "Nuhamin Alemayehu",
    url: "https://www.linkedin.com/pulse/what-dataagentbench-taught-me-enterprise-data-reality-alemayehu-kxgte",
    reach: 11,
    summary: "Reflective essay on why AI benchmarks built on clean data are a polite fiction. Metadata ≠ Knowledge. Layer 2 Institutional Knowledge is the critical gap in production data agents.",
    quote: "An agent without context is just guessing. The difference between 1.85% and 44.4% wasn't a better model — it was better knowledge engineering.",
    color: "border-forge-amber/40 bg-forge-amber/5",
  },
  {
    date: "2026-04-18", platform: "LinkedIn", week: 2,
    title: "From 1.85% to 44.4%: How Team Gemini Built a Self-Learning Data Agent",
    author: "Rafia Kedir & Nuhamin Alemayehu",
    url: "https://www.linkedin.com/pulse/from-185-444-full-story-how-team-gemini-built-data-agent-alemayehu-ea5we",
    reach: 63,
    summary: "Comprehensive retrospective — the full story: compound engineering philosophy, three-unit team structure, MCP pivot, autoDream self-learning loop, and the final 44.4% result that beat Gemini 3 Pro and Claude Opus 4.6.",
    quote: "The score went from 1.85% to 44.4% — not because the model got smarter, but because the system learned from its own failures.",
    color: "border-forge-amber/40 bg-forge-amber/5",
  },
  {
    date: "2026-04-18", platform: "Medium", week: 2,
    title: "Building Oracle Forge: What It Actually Takes to Make an AI Agent Work on Real Enterprise Data",
    author: "Rafia Kedir & Nuhamin Alemayehu",
    url: "https://medium.com/p/4a1869e8dff9",
    reach: 1,
    summary: "Final retrospective on the engineering journey — key learnings and reflections on the future of AI agents in enterprise data contexts.",
    quote: null,
    color: "border-blue-500/40 bg-blue-900/10",
  },
  {
    date: "2026-04-18", platform: "ReadyTensor", week: 2,
    title: "Building Oracle Forge (cross-post)",
    author: "Rafia Kedir & Nuhamin Alemayehu",
    url: "https://app.readytensor.ai/publications/building-oracle-forge-what-it-actually-takes-to-make-an-ai-agent-work-on-real-enterprise-data-team-GctvZPl2Os2N",
    reach: 2,
    summary: "Cross-post of the final Medium retrospective for the ReadyTensor AI practitioner community.",
    quote: null,
    color: "border-blue-500/40 bg-blue-900/10",
  },
];

const REDDIT_POSTS = [
  {
    date: "2026-04-15", subreddit: "r/learnmachinelearning",
    title: "Yelp Dataset 57% Pass — Breaking the 38% Ceiling",
    url: "https://www.reddit.com/r/learnmachinelearning/s/Fk2EyuBhEF",
    impressions: 500, engagements: 5,
  },
  {
    date: "2026-04-18", subreddit: "r/learnmachinelearning",
    title: "Music Brainz Dataset 66% Pass",
    url: "https://www.reddit.com/r/learnmachinelearning/s/61WFPyvypj",
    impressions: 12, engagements: 3,
  },
];

const PLATFORM_REACH = [
  { platform: "Reddit",   reach: 512, color: "#f97316" },
  { platform: "LinkedIn", reach: 100, color: "#3b82f6" },
  { platform: "X",        reach: 164, color: "#e2e8f0" },
  { platform: "ReadyTensor", reach: 5, color: "#8b5cf6" },
  { platform: "Medium",   reach: 3,   color: "#22c55e" },
  { platform: "Discord",  reach: 2,   color: "#6366f1" },
];


const PLATFORM_COLORS: Record<string, string> = {
  "X": "bg-slate-900/50 text-slate-300 border-slate-600/40",
  "Medium": "bg-green-900/20 text-green-400 border-green-500/30",
  "ReadyTensor": "bg-purple-900/20 text-purple-400 border-purple-500/30",
  "LinkedIn": "bg-blue-900/20 text-blue-400 border-blue-500/30",
  "Reddit": "bg-orange-900/20 text-orange-400 border-orange-500/30",
};

export default function CorpusPage() {
  const [activeWeek, setActiveWeek] = useState<number | "all">("all");

  const filteredThreads  = activeWeek === "all" ? THREADS  : THREADS.filter(t => t.week === activeWeek);
  const filteredArticles = activeWeek === "all" ? ARTICLES : ARTICLES.filter(a => a.week === activeWeek);

  const totalReach = PLATFORM_REACH.reduce((s, p) => s + p.reach, 0);
  const totalEngagements = THREADS.reduce((s, t) => s + t.engagements, 0) + REDDIT_POSTS.reduce((s, r) => s + r.engagements, 0);

  return (
    <div className="max-w-7xl mx-auto px-6 py-10 space-y-12">

      {/* header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white">Signal Corps — Public Corpus</h1>
          <p className="text-forge-muted mt-1">External communication, publications, and community engagement — April 10–18, 2026</p>
          <div className="flex items-center gap-2 mt-2 text-sm text-forge-muted font-mono">
            <span className="text-green-400">Rafia Kedir</span>
            <span>&amp;</span>
            <span className="text-green-400">Nuhamin Alemayehu</span>
            <span className="text-forge-dim ml-2">· Signal Corps · @GeminiTrp1</span>
          </div>
        </div>
        <div className="text-right space-y-1">
          <div className="text-3xl font-black font-mono text-forge-amber">{totalReach.toLocaleString()}</div>
          <div className="text-forge-muted text-sm">total reach</div>
          <div className="text-forge-muted text-xs font-mono">{totalEngagements} engagements</div>
        </div>
      </div>

      {/* ── STATS GRID ─────────────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 md:grid-cols-6 gap-3">
        {[
          { label: "X Threads",   value: "6",  sub: "50+ tweets",    color: "text-slate-300" },
          { label: "Articles",    value: "6",  sub: "Medium · LinkedIn · ReadyTensor", color: "text-blue-400" },
          { label: "Reddit Posts",value: "2",  sub: "r/learnML",     color: "text-orange-400" },
          { label: "Platforms",   value: "7",  sub: "X·Medium·LI·RT·Reddit·Discord·Slack", color: "text-purple-400" },
          { label: "Week 1 Reach",value: "~78", sub: "Apr 10–13",    color: "text-forge-muted" },
          { label: "Week 2 Reach",value: "~627",sub: "Apr 14–18",    color: "text-forge-green" },
        ].map(s => (
          <div key={s.label} className="rounded-xl border border-forge-border bg-forge-card p-4 text-center">
            <div className={`text-2xl font-black font-mono ${s.color}`}>{s.value}</div>
            <div className="text-forge-text text-xs font-medium mt-1">{s.label}</div>
            <div className="text-forge-muted text-xs mt-0.5 leading-tight">{s.sub}</div>
          </div>
        ))}
      </div>

      {/* ── WEEK FILTER ────────────────────────────────────────────────────── */}
      <div className="flex gap-2">
        {(["all", 1, 2] as const).map(w => (
          <button
            key={w}
            onClick={() => setActiveWeek(w)}
            className={`px-4 py-1.5 rounded-lg text-sm font-mono font-medium transition-colors ${activeWeek === w ? "bg-forge-amber text-forge-bg" : "bg-forge-card border border-forge-border text-forge-muted hover:text-forge-text"}`}
          >
            {w === "all" ? "All" : w === 1 ? "Week 1 (Apr 10–13)" : "Week 2 (Apr 14–18)"}
          </button>
        ))}
      </div>

      {/* ── X THREADS ──────────────────────────────────────────────────────── */}
      <section>
        <h2 className="text-xl font-bold text-white mb-4">X (Twitter) Threads</h2>
        <div className="space-y-3">
          {filteredThreads.map(t => (
            <div key={t.id} className={`rounded-xl border p-5 ${t.color}`}>
              <div className="flex items-start justify-between gap-4">
                <div className="min-w-0">
                  <div className="flex items-center gap-3 mb-1">
                    <span className="font-mono font-bold text-sm">{t.id}</span>
                    <span className="font-semibold text-forge-text">{t.title}</span>
                    <span className="text-xs text-forge-muted font-mono">{t.type}</span>
                  </div>
                  <p className="text-xs text-forge-muted leading-relaxed">{t.summary}</p>
                </div>
                <div className="flex-shrink-0 text-right space-y-1">
                  <div className="font-mono font-bold text-forge-text">{t.impressions}</div>
                  <div className="text-xs text-forge-muted">impressions</div>
                  <div className="font-mono text-sm text-forge-amber">{t.engagements} eng</div>
                </div>
              </div>
              <div className="mt-3 flex items-center gap-3">
                <span className="text-xs text-forge-muted font-mono">{t.date}</span>
                <a href={t.url} target="_blank" rel="noopener noreferrer"
                  className="text-xs font-mono text-forge-amber hover:underline truncate max-w-xs">
                  {t.url.replace("https://", "")}
                </a>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* ── ARTICLES ───────────────────────────────────────────────────────── */}
      <section>
        <h2 className="text-xl font-bold text-white mb-4">Published Articles</h2>
        <div className="space-y-4">
          {filteredArticles.map((a, i) => (
            <div key={i} className={`rounded-xl border p-5 ${a.color}`}>
              <div className="flex items-start justify-between gap-4">
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2 mb-2 flex-wrap">
                    <span className={`px-2 py-0.5 rounded text-xs font-mono border ${PLATFORM_COLORS[a.platform] || "text-forge-muted border-forge-border"}`}>
                      {a.platform}
                    </span>
                    <span className="text-xs text-forge-muted font-mono">{a.date}</span>
                    <span className="text-xs text-forge-muted">by {a.author}</span>
                  </div>
                  <div className="font-semibold text-forge-text mb-2 leading-snug">{a.title}</div>
                  <p className="text-xs text-forge-muted leading-relaxed">{a.summary}</p>
                  {a.quote && (
                    <blockquote className="mt-3 pl-3 border-l-2 border-forge-amber/50 text-xs text-forge-text italic leading-relaxed">
                      "{a.quote}"
                    </blockquote>
                  )}
                </div>
                <div className="flex-shrink-0 text-right">
                  <div className="font-mono font-bold text-forge-amber text-lg">{a.reach}</div>
                  <div className="text-xs text-forge-muted">reach</div>
                </div>
              </div>
              <a href={a.url} target="_blank" rel="noopener noreferrer"
                className="mt-3 block text-xs font-mono text-forge-amber hover:underline truncate">
                {a.url.replace("https://", "")}
              </a>
            </div>
          ))}
        </div>
      </section>

      {/* ── REDDIT POSTS ───────────────────────────────────────────────────── */}
      {(activeWeek === "all" || activeWeek === 2) && (
        <section>
          <h2 className="text-xl font-bold text-white mb-4">Reddit Posts</h2>
          <div className="grid md:grid-cols-2 gap-4">
            {REDDIT_POSTS.map((r, i) => (
              <div key={i} className="rounded-xl border border-orange-500/30 bg-orange-900/10 p-5">
                <div className="flex items-start justify-between gap-2 mb-2">
                  <div>
                    <span className="text-xs font-mono text-orange-400">{r.subreddit}</span>
                    <div className="font-semibold text-forge-text mt-1 text-sm">{r.title}</div>
                  </div>
                  <div className="text-right flex-shrink-0">
                    <div className="font-mono font-bold text-orange-400 text-xl">{r.impressions}</div>
                    <div className="text-xs text-forge-muted">reach</div>
                  </div>
                </div>
                <div className="text-xs text-forge-muted font-mono">{r.date}</div>
                <a href={r.url} target="_blank" rel="noopener noreferrer"
                  className="mt-2 block text-xs font-mono text-orange-400 hover:underline truncate">
                  {r.url.replace("https://", "")}
                </a>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* ── PLATFORM REACH CHART ───────────────────────────────────────────── */}
      <section className="rounded-2xl border border-forge-border bg-forge-surface p-8">
        <h2 className="text-xl font-bold text-white mb-2">Reach by Platform</h2>
        <p className="text-forge-muted text-sm mb-6">Total impressions across all posts — Reddit spike from Yelp 57% post</p>
        <div className="h-56">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={PLATFORM_REACH} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e2d3d" />
              <XAxis dataKey="platform" tick={{ fill: "#64748b", fontSize: 11 }} />
              <YAxis tick={{ fill: "#64748b", fontSize: 11 }} />
              <Tooltip contentStyle={{ background: "#141c24", border: "1px solid #1e2d3d", borderRadius: 8 }} formatter={(v: any) => [v, "reach"]} />
              <Bar dataKey="reach" radius={[4, 4, 0, 0]}>
                {PLATFORM_REACH.map((p, i) => <Cell key={i} fill={p.color} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </section>

      {/* ── RETROSPECTIVE ──────────────────────────────────────────────────── */}
      <section className="rounded-2xl border border-forge-border bg-forge-surface p-8">
        <h2 className="text-xl font-bold text-white mb-4">Retrospective — What Compounded, What Didn't</h2>
        <div className="grid md:grid-cols-2 gap-6">
          <div className="space-y-3">
            <div className="text-sm font-semibold text-forge-green mb-3">✓ What Compounded</div>
            {[
              { point: "Consistent narrative from Day 1", detail: "Kickoff article + X threads created a public build log. The 'plan vs what actually happened' structure between the two Medium articles became a natural two-part series." },
              { point: "@d_derib MCP exchange", detail: "The public community exchange fed directly into an architectural decision — documented in both community log and interim report as the clearest proof of community intelligence value." },
              { point: "Daily X threads as proof-of-work", detail: "The live build log gave the LinkedIn final post credible references. The thread timeline made the progression from 1.85% to 44.4% visible and verifiable." },
            ].map(w => (
              <div key={w.point} className="rounded-lg border border-green-500/20 bg-green-900/10 p-3">
                <div className="font-semibold text-green-400 text-sm mb-1">{w.point}</div>
                <p className="text-xs text-forge-muted leading-relaxed">{w.detail}</p>
              </div>
            ))}
          </div>
          <div className="space-y-3">
            <div className="text-sm font-semibold text-red-400 mb-3">✗ What We'd Change</div>
            {[
              { point: "Real-time community response logging", detail: "Several potentially valuable replies were missed because the engagement log wasn't checked daily. Documentation happened retroactively, losing some signal." },
              { point: "Discord DAB Community post", detail: "The DAB community Discord channel was not found during Week 2 — the one unchecked minimum requirement. Direct community posting to the benchmark authors' community was missed." },
            ].map(w => (
              <div key={w.point} className="rounded-lg border border-red-500/20 bg-red-900/10 p-3">
                <div className="font-semibold text-red-400 text-sm mb-1">{w.point}</div>
                <p className="text-xs text-forge-muted leading-relaxed">{w.detail}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

    </div>
  );
}
