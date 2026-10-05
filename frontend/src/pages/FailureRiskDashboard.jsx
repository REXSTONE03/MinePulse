import React from 'react';
import { ShieldAlert, AlertCircle, CheckCircle2, AlertTriangle } from 'lucide-react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
  ArcElement
} from 'chart.js';
import { Bar, Doughnut } from 'react-chartjs-2';

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
  ArcElement
);

export default function FailureRiskDashboard({ failureRisk, loading }) {
  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="w-8 h-8 border-4 border-cyan-500/30 border-t-cyan-500 rounded-full animate-spin" />
      </div>
    );
  }

  const items = failureRisk || [];

  const highRiskCount = items.filter(i => i.risk_tier === 'HIGH' || i.p_fail_30d > 0.4).length;
  const mediumRiskCount = items.filter(i => i.risk_tier === 'MEDIUM' || (i.p_fail_30d > 0.15 && i.p_fail_30d <= 0.4)).length;
  const lowRiskCount = items.filter(i => i.risk_tier === 'LOW' || i.p_fail_30d <= 0.15).length;

  const barChartData = {
    labels: items.slice(0, 8).map(i => `${i.component_type} (#${i.vehicle_id})`),
    datasets: [
      {
        label: 'P(Fail 7d)',
        data: items.slice(0, 8).map(i => (i.p_fail_7d * 100).toFixed(1)),
        backgroundColor: '#06b6d4',
      },
      {
        label: 'P(Fail 30d)',
        data: items.slice(0, 8).map(i => (i.p_fail_30d * 100).toFixed(1)),
        backgroundColor: '#f59e0b',
      },
      {
        label: 'P(Fail 60d)',
        data: items.slice(0, 8).map(i => (i.p_fail_60d * 100).toFixed(1)),
        backgroundColor: '#f97316',
      },
      {
        label: 'P(Fail 90d)',
        data: items.slice(0, 8).map(i => (i.p_fail_90d * 100).toFixed(1)),
        backgroundColor: '#ef4444',
      },
    ],
  };

  const doughnutData = {
    labels: ['High Risk', 'Medium Risk', 'Low Risk'],
    datasets: [
      {
        data: [highRiskCount, mediumRiskCount, lowRiskCount],
        backgroundColor: ['#ef4444', '#f59e0b', '#10b981'],
        borderWidth: 2,
        borderColor: '#0f172a',
      },
    ],
  };

  return (
    <div className="space-y-6">
      {/* Title */}
      <div className="bg-slate-900 border border-slate-800 p-6 rounded-2xl flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white flex items-center space-x-2">
            <ShieldAlert className="w-6 h-6 text-cyan-400" />
            <span>Weibull Failure Risk Prediction Dashboard</span>
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Parametric Weibull survival analysis predictions for 7, 30, 60, and 90-day time horizons.
          </p>
        </div>
      </div>

      {/* Visual Risk Distribution Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 bg-slate-900 border border-slate-800 rounded-2xl p-5">
          <h3 className="text-sm font-bold text-white mb-4">Multi-Horizon Failure Probabilities (%)</h3>
          <div className="h-64 flex items-center justify-center">
            <Bar 
              data={barChartData} 
              options={{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                  legend: { labels: { color: '#94a3b8', font: { size: 11 } } }
                },
                scales: {
                  x: { ticks: { color: '#64748b', font: { size: 10 } }, grid: { color: '#1e293b' } },
                  y: { ticks: { color: '#64748b', font: { size: 10 } }, grid: { color: '#1e293b' } },
                }
              }} 
            />
          </div>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 flex flex-col items-center justify-center">
          <h3 className="text-sm font-bold text-white mb-4 self-start">Risk Tier Breakdown</h3>
          <div className="w-48 h-48">
            <Doughnut 
              data={doughnutData} 
              options={{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                  legend: { position: 'bottom', labels: { color: '#94a3b8', font: { size: 11 } } }
                }
              }} 
            />
          </div>
        </div>
      </div>

      {/* Component Risk Table */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden">
        <div className="p-5 border-b border-slate-800 flex items-center justify-between">
          <h3 className="text-sm font-bold text-white">Component Weibull Survival Assessment</h3>
          <span className="text-xs font-mono text-slate-400">Total Analyzed: {items.length}</span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-300">
            <thead className="bg-slate-800/80 uppercase text-[10px] text-slate-400 font-mono tracking-wider border-b border-slate-800">
              <tr>
                <th className="py-3 px-4">Vehicle ID</th>
                <th className="py-3 px-4">Component</th>
                <th className="py-3 px-4">Op Hours</th>
                <th className="py-3 px-4">Age (Months)</th>
                <th className="py-3 px-4 text-center">7 Days</th>
                <th className="py-3 px-4 text-center">30 Days</th>
                <th className="py-3 px-4 text-center">60 Days</th>
                <th className="py-3 px-4 text-center">90 Days</th>
                <th className="py-3 px-4 text-center">Risk Tier</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-mono">
              {items.map((row, idx) => (
                <tr key={idx} className="hover:bg-slate-800/40 transition">
                  <td className="py-3 px-4 font-bold text-white">Truck #{row.vehicle_id}</td>
                  <td className="py-3 px-4 text-cyan-300">{row.component_type}</td>
                  <td className="py-3 px-4">{row.operating_hours || row.hours || 3500} hrs</td>
                  <td className="py-3 px-4">{row.age_months || 14} m</td>
                  <td className="py-3 px-4 text-center">{(row.p_fail_7d * 100).toFixed(1)}%</td>
                  <td className="py-3 px-4 text-center font-bold text-amber-400">{(row.p_fail_30d * 100).toFixed(1)}%</td>
                  <td className="py-3 px-4 text-center">{(row.p_fail_60d * 100).toFixed(1)}%</td>
                  <td className="py-3 px-4 text-center">{(row.p_fail_90d * 100).toFixed(1)}%</td>
                  <td className="py-3 px-4 text-center">
                    <span className={`px-2.5 py-1 rounded text-[10px] font-bold uppercase ${
                      row.risk_tier === 'HIGH' || row.p_fail_30d > 0.4
                        ? 'bg-rose-500/20 text-rose-400 border border-rose-500/30'
                        : row.risk_tier === 'MEDIUM' || row.p_fail_30d > 0.15
                        ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                        : 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                    }`}>
                      {row.risk_tier || (row.p_fail_30d > 0.4 ? 'HIGH' : row.p_fail_30d > 0.15 ? 'MEDIUM' : 'LOW')}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
