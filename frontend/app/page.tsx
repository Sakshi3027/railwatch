"use client";
import "leaflet/dist/leaflet.css";
import { useEffect, useState } from "react";
import { fetchKPIs, fetchScorecard, fetchRoutes, fetchTrend, fetchFeatureImportance } from "@/lib/api";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  LineChart, Line, CartesianGrid,
} from "recharts";
import { Train, AlertTriangle, TrendingUp, Activity, Bot, ChevronRight } from "lucide-react";
import dynamic from "next/dynamic";
const TrainMap = dynamic(() => import("./components/TrainMap"), { ssr: false });

const GRADE_COLOR: Record<string, string> = {
  A: "#1D9E75", B: "#639922", C: "#BA7517", D: "#D85A30", F: "#E24B4A",
};
const RISK_COLOR: Record<string, string> = {
  Critical: "#E24B4A", High: "#EF9F27", Medium: "#BA7517", Normal: "#1D9E75",
};

export default function Dashboard() {
  const [kpis, setKpis] = useState<any>(null);
  const [scorecard, setScorecard] = useState<any[]>([]);
  const [routes, setRoutes] = useState<any[]>([]);
  const [trend, setTrend] = useState<any[]>([]);
  const [features, setFeatures] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [briefing, setBriefing] = useState<string>("");
  const [escalations, setEscalations] = useState<string[]>([]);
  const [anomalies, setAnomalies] = useState<string[]>([]);
  const [agentLoading, setAgentLoading] = useState(false);

  useEffect(() => {
    Promise.all([
      fetchKPIs(),
      fetchScorecard(),
      fetchRoutes(),
      fetchTrend(),
      fetchFeatureImportance(),
    ]).then(([k, s, r, t, f]) => {
      setKpis(k);
      setScorecard(s);
      setRoutes(r);
      setTrend(t.map((d: any) => ({
        ...d,
        label: `${d.year}-${String(d.month).padStart(2, "0")}`,
      })));
      setFeatures(f.slice(0, 8));
      setLoading(false);
    });
  }, []);

  async function runAgent() {
    setAgentLoading(true);
    setBriefing("");
    setEscalations([]);
    setAnomalies([]);
    try {
      const res = await fetch("http://127.0.0.1:8000/api/agent/briefing", { method: "POST" });
      const data = await res.json();
      setBriefing(data.briefing);
      setEscalations(data.escalations);
      setAnomalies(data.anomalies);
    } catch (e) {
      setBriefing("Agent error — make sure the backend is running.");
    }
    setAgentLoading(false);
  }

  if (loading) return (
    <div className="flex items-center justify-center h-screen bg-[#0f1117]">
      <div className="text-slate-400 text-lg">Loading RailWatch...</div>
    </div>
  );

  return (
    <div className="min-h-screen bg-[#0f1117]">
      <div className="border-b border-slate-800 px-6 py-3 flex items-center">
        <div className="w-8 h-8 bg-indigo-600 rounded-lg flex items-center justify-center mr-3">
          <Train size={16} className="text-white" />
        </div>
        <span className="text-white font-medium text-lg mr-3">RailWatch</span>
        <span className="text-xs bg-red-900 text-red-300 px-2 py-0.5 rounded-full mr-auto">Live</span>
        <button
          onClick={runAgent}
          disabled={agentLoading}
          className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white text-sm px-4 py-2 rounded-lg"
        >
          <Bot size={14} />
          {agentLoading ? "Running agent..." : "Run AI briefing"}
        </button>
      </div>

      <div className="p-6 space-y-6">
        <div className="grid grid-cols-4 gap-4">
          {[
            { label: "Total delay minutes", value: kpis.total_delay_minutes.toLocaleString(), icon: <AlertTriangle size={14} />, delta: "FY2024", bad: false },
            { label: "Avg on-time %", value: `${kpis.avg_on_time_pct}%`, icon: <Activity size={14} />, delta: "FRA target: 80%", bad: true },
            { label: "Avg FTI per 10k mi", value: kpis.avg_fti_per_10k.toLocaleString(), icon: <TrendingUp size={14} />, delta: "Host railroad caused", bad: true },
            { label: "Routes failing FRA", value: `${kpis.routes_failing_fra_target} / ${kpis.total_routes}`, icon: <Train size={14} />, delta: "Below 80% threshold", bad: true },
          ].map((k, i) => (
            <div key={i} className="bg-slate-900 border border-slate-800 rounded-xl p-4">
              <div className="flex items-center gap-2 text-slate-400 text-xs mb-2">{k.icon} {k.label}</div>
              <div className="text-2xl font-medium text-white">{k.value}</div>
              <div className={`text-xs mt-1 ${k.bad ? "text-red-400" : "text-slate-400"}`}>{k.delta}</div>
            </div>
          ))}
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
            <div className="text-sm font-medium text-white mb-4">Monthly FTI trend (avg delay min / 10k mi)</div>
            <ResponsiveContainer width="100%" height={220}>
              <LineChart data={trend}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="label" tick={{ fill: "#64748b", fontSize: 10 }} interval={5} />
                <YAxis tick={{ fill: "#64748b", fontSize: 10 }} />
                <Tooltip contentStyle={{ background: "#1e293b", border: "none", borderRadius: 8 }} />
                <Line type="monotone" dataKey="avg_fti_per_10k" stroke="#E24B4A" strokeWidth={2} dot={false} name="FTI/10k mi" />
              </LineChart>
            </ResponsiveContainer>
          </div>

          <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
            <div className="text-sm font-medium text-white mb-4">Top delay attribution features (SHAP)</div>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={features} layout="vertical">
                <XAxis type="number" tick={{ fill: "#64748b", fontSize: 10 }} />
                <YAxis dataKey="feature" type="category" tick={{ fill: "#64748b", fontSize: 10 }} width={120} />
                <Tooltip contentStyle={{ background: "#1e293b", border: "none", borderRadius: 8 }} />
                <Bar dataKey="mean_shap" fill="#4f46e5" radius={[0, 4, 4, 0]} name="SHAP value" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="grid grid-cols-3 gap-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
            <div className="text-sm font-medium text-white mb-4">Host railroad grades</div>
            <div className="space-y-3">
              {scorecard.map((rr: any) => (
                <div key={rr.host_railroad} className="flex items-center justify-between">
                  <div>
                    <div className="text-sm text-white font-medium">{rr.host_railroad}</div>
                    <div className="text-xs text-slate-400">{rr.avg_fti_per_10k} min/10k mi · {rr.avg_otp}% OTP</div>
                  </div>
                  <div className="text-2xl font-medium" style={{ color: GRADE_COLOR[rr.grade] }}>{rr.grade}</div>
                </div>
              ))}
            </div>
          </div>

          <div className="col-span-2 bg-slate-900 border border-slate-800 rounded-xl p-4">
            <div className="text-sm font-medium text-white mb-4">Route risk summary</div>
            <table className="w-full text-sm">
              <thead>
                <tr className="text-slate-400 text-xs uppercase tracking-wide border-b border-slate-800">
                  <th className="text-left pb-2">Route</th>
                  <th className="text-left pb-2">Host RR</th>
                  <th className="text-left pb-2">OTP %</th>
                  <th className="text-left pb-2">FTI/10k</th>
                  <th className="text-left pb-2">Risk</th>
                </tr>
              </thead>
              <tbody>
                {routes.map((r: any) => (
                  <tr key={r.route} className="border-b border-slate-800">
                    <td className="py-2 text-white">{r.route}</td>
                    <td className="py-2 text-slate-300">{r.host_railroad}</td>
                    <td className="py-2 text-slate-300">{r.avg_otp}%</td>
                    <td className="py-2 text-slate-300">{r.avg_fti_per_10k}</td>
                    <td className="py-2">
                      <span className="text-xs px-2 py-0.5 rounded-full font-medium"
                        style={{ background: RISK_COLOR[r.risk_level] + "22", color: RISK_COLOR[r.risk_level] }}>
                        {r.risk_level}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <TrainMap />

        {(briefing || agentLoading) && (
          <div className="grid grid-cols-3 gap-4">
            <div className="col-span-2 bg-slate-900 border border-indigo-800 rounded-xl p-4">
              <div className="flex items-center gap-2 mb-4">
                <Bot size={16} className="text-indigo-400" />
                <span className="text-sm font-medium text-white">AI Intelligence Briefing</span>
                <span className="text-xs bg-indigo-900 text-indigo-300 px-2 py-0.5 rounded-full">LangGraph · Groq</span>
              </div>
              {agentLoading ? (
                <div className="text-slate-400 text-sm animate-pulse">Agent is analyzing data...</div>
              ) : (
                <div className="text-slate-300 text-sm whitespace-pre-wrap leading-relaxed">{briefing}</div>
              )}
            </div>

            <div className="space-y-4">
              {anomalies.length > 0 && (
                <div className="bg-slate-900 border border-red-900 rounded-xl p-4">
                  <div className="text-sm font-medium text-white mb-3">Anomalies detected</div>
                  <div className="space-y-2">
                    {anomalies.map((a, i) => (
                      <div key={i} className="text-xs text-red-300 flex items-start gap-2">
                        <AlertTriangle size={12} className="mt-0.5 flex-shrink-0" />
                        {a}
                      </div>
                    ))}
                  </div>
                </div>
              )}
              {escalations.length > 0 && (
                <div className="bg-slate-900 border border-amber-900 rounded-xl p-4">
                  <div className="text-sm font-medium text-white mb-3">Escalation actions</div>
                  <div className="space-y-2">
                    {escalations.map((e, i) => (
                      <div key={i} className="text-xs text-amber-300 flex items-start gap-2">
                        <ChevronRight size={12} className="mt-0.5 flex-shrink-0" />
                        {e}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}