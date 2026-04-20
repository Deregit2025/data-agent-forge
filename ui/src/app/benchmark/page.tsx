"use client";
import { useEffect, useState } from "react";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, ReferenceLine,
} from "recharts";
import { fetchScore, fetchDatasets } from "@/lib/api";

const DB_COLORS: Record<string, string> = {
  postgres: "#3b82f6",
  mongodb:  "#10b981",
  sqlite:   "#8b5cf6",
  duckdb:   "#f59e0b",
};

export default function BenchmarkPage() {
  const [score,    setScore]    = useState<any>(null);
  const [datasets, setDatasets] = useState<any>(null);
  const [loading,  setLoading]  = useState(true);

  useEffect(() => {
    Promise.all([fetchScore(), fetchDatasets()])
      .then(([s, d]) => { setScore(s); setDatasets(d); })
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="p-10 text-forge-muted font-mono">Loading…</div>;

  const chartData = score?.history.map((h: any) => ({
    label: h.label,
    rate:  +(h.pass_rate * 100).toFixed(1),
    n:     h.n_queries,
    note:  h.note,
  }));

  return (
    <div className="max-w-7xl mx-auto px-6 py-10 space-y-10">
      <div>
        <h1 className="text-3xl font-bold text-white">Benchmark Results</h1>
        <p className="text-forge-muted mt-1">DataAgentBench — 54 queries, 12 datasets, 9 domains, 4 DB types</p>
      </div>

      {/* ── SCORE CARDS ── */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: "Final Score",    value: "44.4%",  sub: "24 / 54 passed",   color: "text-forge-amber" },
          { label: "Baseline Score", value: "1.85%",  sub: "1 / 54 passed",    color: "text-forge-muted" },
          { label: "Leader (Gemini 3 Pro)", value: "38%", sub: "Public ceiling", color: "text-blue-400" },
          { label: "Improvement",    value: "+42.6pp", sub: "baseline → final", color: "text-forge-green" },
        ].map(c => (
          <div key={c.label} className="rounded-xl border border-forge-border bg-forge-card p-5">
            <div className={`text-3xl font-black font-mono ${c.color}`}>{c.value}</div>
            <div className="text-forge-text font-medium mt-1">{c.label}</div>
            <div className="text-forge-muted text-xs">{c.sub}</div>
          </div>
        ))}
      </div>

      {/* ── SCORE PROGRESSION CHART ── */}
      <div className="rounded-2xl border border-forge-border bg-forge-surface p-6">
        <h2 className="text-lg font-bold text-white mb-1">Score Progression</h2>
        <p className="text-forge-muted text-sm mb-1">
          2 full benchmark runs (n=54) + 2 partial spot checks — partial runs test specific datasets only, not comparable to full runs
        </p>
        <div className="flex items-center gap-4 mb-6">
          <span className="flex items-center gap-1.5 text-xs text-forge-muted"><span className="w-3 h-3 rounded-full bg-forge-amber inline-block" />Full run (n=54)</span>
          <span className="flex items-center gap-1.5 text-xs text-forge-muted"><span className="w-3 h-3 rounded-full bg-blue-400 inline-block" />Partial spot check</span>
        </div>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e2d3d" />
              <XAxis dataKey="label" tick={{ fill: "#64748b", fontSize: 11 }} />
              <YAxis
                domain={[0, 70]}
                tick={{ fill: "#64748b", fontSize: 11 }}
                tickFormatter={v => `${v}%`}
              />
              <Tooltip
                contentStyle={{ background: "#141c24", border: "1px solid #1e2d3d", borderRadius: 8 }}
                labelStyle={{ color: "#e2e8f0", fontWeight: 600 }}
                formatter={(v: any) => [`${v}%`, "Pass Rate"]}
              />
              {/* ceiling line */}
              <ReferenceLine y={38} stroke="#3b82f6" strokeDasharray="6 3" label={{ value: "38% ceiling", fill: "#3b82f6", fontSize: 11 }} />
              <Line
                type="monotone" dataKey="rate" stroke="#f59e0b" strokeWidth={2.5}
                dot={{ fill: "#f59e0b", r: 5, strokeWidth: 0 }}
                activeDot={{ r: 7, fill: "#fbbf24" }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
        <div className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-3">
          {chartData?.map((d: any) => (
            <div key={d.label} className="rounded-lg bg-forge-card border border-forge-border p-3">
              <div className="flex items-center gap-2 mb-1">
                <span className="font-mono font-bold text-forge-amber text-sm">{d.rate}%</span>
                <span className={`text-xs font-mono px-1.5 py-0.5 rounded ${d.n === 54 ? "bg-forge-amber/10 text-forge-amber border border-forge-amber/30" : "bg-blue-900/30 text-blue-400 border border-blue-500/30"}`}>
                  {d.n === 54 ? "full n=54" : `partial n=${d.n}`}
                </span>
              </div>
              <div className="text-forge-text text-xs font-medium">{d.label}</div>
              <div className="text-forge-muted text-xs mt-1 leading-tight">{d.note}</div>
            </div>
          ))}
        </div>
      </div>

      {/* ── PER-DATASET TABLE ── */}
      <div className="rounded-2xl border border-forge-border bg-forge-surface p-6">
        <h2 className="text-lg font-bold text-white mb-1">Per-Dataset Performance</h2>
        <p className="text-forge-muted text-sm mb-5">Final run (2026-04-18) vs Baseline (2026-04-11)</p>

        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-forge-border">
                {["Dataset","Domain","DB Types","Queries","Baseline","Final","Improvement"].map(h => (
                  <th key={h} className="text-left py-2 px-3 text-forge-muted font-medium text-xs">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {datasets?.datasets.map((d: any) => (
                <tr key={d.name} className="border-b border-forge-border/50 hover:bg-forge-card/50 transition-colors">
                  <td className="py-2.5 px-3 font-mono text-forge-amber font-medium">{d.name}</td>
                  <td className="py-2.5 px-3 text-forge-muted text-xs">{d.domain}</td>
                  <td className="py-2.5 px-3">
                    <div className="flex gap-1 flex-wrap">
                      {d.db_types.map((t: string) => (
                        <span key={t} className="px-1.5 py-0.5 rounded text-xs font-mono"
                          style={{ background: DB_COLORS[t] + "22", color: DB_COLORS[t], border: `1px solid ${DB_COLORS[t]}44` }}>
                          {t}
                        </span>
                      ))}
                    </div>
                  </td>
                  <td className="py-2.5 px-3 text-forge-text font-mono">{d.n_queries}</td>
                  <td className="py-2.5 px-3">
                    <span className="text-forge-muted font-mono">{d.base_pass}/{d.n_queries}</span>
                    <span className="text-forge-muted text-xs ml-1">({(d.base_rate * 100).toFixed(0)}%)</span>
                  </td>
                  <td className="py-2.5 px-3">
                    <div className="flex items-center gap-2">
                      <span className={`font-mono font-semibold ${d.final_rate >= 0.5 ? "text-forge-green" : d.final_rate > 0 ? "text-forge-amber" : "text-forge-muted"}`}>
                        {d.final_pass}/{d.n_queries}
                      </span>
                      <div className="w-16 h-1.5 rounded-full bg-forge-border overflow-hidden">
                        <div className="h-full rounded-full bg-forge-amber" style={{ width: `${d.final_rate * 100}%` }} />
                      </div>
                    </div>
                  </td>
                  <td className="py-2.5 px-3">
                    {d.improvement > 0
                      ? <span className="text-forge-green font-mono font-semibold">+{d.improvement}</span>
                      : <span className="text-forge-muted font-mono">—</span>
                    }
                  </td>
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr className="border-t border-forge-amber/30">
                <td colSpan={3} className="py-2.5 px-3 text-forge-amber font-semibold">Total</td>
                <td className="py-2.5 px-3 text-forge-text font-mono font-semibold">54</td>
                <td className="py-2.5 px-3 text-forge-muted font-mono font-semibold">1/54 (1.85%)</td>
                <td className="py-2.5 px-3 text-forge-amber font-mono font-bold">24/54 (44.4%)</td>
                <td className="py-2.5 px-3 text-forge-green font-mono font-semibold">+23</td>
              </tr>
            </tfoot>
          </table>
        </div>
      </div>

      {/* ── SCORING METHODOLOGY ── */}
      <div className="rounded-2xl border border-forge-border bg-forge-surface p-6">
        <h2 className="text-lg font-bold text-white mb-4">Scoring Methodology</h2>
        <div className="grid md:grid-cols-3 gap-4">
          {[
            { title: "Majority Pass (3/5)",  desc: "A query passes if ≥3 of 5 independent trials return the correct answer. Eliminates variance from temperature and ordering effects." },
            { title: "validate.py (DAB)",    desc: "Oracle Forge uses the exact same validate.py from ucbepic/DataAgentBench. If DAB's validator says pass, we pass. No custom tolerance." },
            { title: "5 Trials per Query",   desc: "Each of 54 queries runs 5 times with temperature=0. Variance comes from MCP timing, prior result ordering, and synthesis token cap differences." },
          ].map(m => (
            <div key={m.title} className="rounded-xl bg-forge-card border border-forge-border p-4">
              <div className="font-semibold text-forge-text mb-2">{m.title}</div>
              <div className="text-forge-muted text-sm leading-relaxed">{m.desc}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
