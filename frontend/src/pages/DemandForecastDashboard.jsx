import React, { useState } from 'react';
import { TrendingUp, Layers, Calendar, HelpCircle } from 'lucide-react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
} from 'chart.js';
import { Line } from 'react-chartjs-2';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

export default function DemandForecastDashboard({ demand, horizonDays, setHorizonDays, loading }) {
  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="w-8 h-8 border-4 border-cyan-500/30 border-t-cyan-500 rounded-full animate-spin" />
      </div>
    );
  }

  const items = demand || [];

  const labels = items.map(i => i.part_category);
  const plannedData = items.map(i => i.planned_pm_demand || i.planned_demand || 10);
  const failureData = items.map(i => i.failure_driven_demand || i.failure_demand || 5);
  const totalData = items.map(i => i.total_expected_demand || i.total_demand || 15);
  const p10Data = items.map(i => i.p10_uncertainty || i.p10 || Math.floor(i.total_expected_demand * 0.75));
  const p95Data = items.map(i => i.p95_uncertainty || i.p95 || Math.ceil(i.total_expected_demand * 1.35));

  const chartData = {
    labels,
    datasets: [
      {
        label: 'P95 Upper Bound',
        data: p95Data,
        borderColor: 'rgba(239, 68, 68, 0.4)',
        backgroundColor: 'rgba(239, 68, 68, 0.05)',
        borderDash: [5, 5],
        fill: '+1',
        pointRadius: 0,
      },
      {
        label: 'Total Expected Demand (D_total)',
        data: totalData,
        borderColor: '#06b6d4',
        backgroundColor: 'rgba(6, 182, 212, 0.2)',
        borderWidth: 3,
        fill: false,
        pointRadius: 4,
      },
      {
        label: 'P10 Lower Bound',
        data: p10Data,
        borderColor: 'rgba(16, 185, 129, 0.4)',
        backgroundColor: 'rgba(16, 185, 129, 0.05)',
        borderDash: [5, 5],
        fill: false,
        pointRadius: 0,
      },
      {
        label: 'Planned PM Demand',
        data: plannedData,
        borderColor: '#3b82f6',
        backgroundColor: 'rgba(59, 130, 246, 0.1)',
        borderWidth: 2,
        fill: false,
        pointRadius: 3,
      },
      {
        label: 'Failure-Driven Demand',
        data: failureData,
        borderColor: '#f59e0b',
        backgroundColor: 'rgba(245, 158, 11, 0.1)',
        borderWidth: 2,
        fill: false,
        pointRadius: 3,
      }
    ],
  };

  return (
    <div className="space-y-6">
      {/* Header & Horizon Selector */}
      <div className="bg-slate-900 border border-slate-800 p-6 rounded-2xl flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-white flex items-center space-x-2">
            <TrendingUp className="w-6 h-6 text-cyan-400" />
            <span>Stochastic Parts-Demand Forecasting</span>
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Combines deterministic PM schedules with Weibull failure-driven probability distributions (P10 / P95 confidence intervals).
          </p>
        </div>
        
        <div className="flex items-center space-x-2 bg-slate-800 p-1 rounded-xl border border-slate-700">
          <Calendar className="w-4 h-4 text-slate-400 ml-2" />
          <span className="text-xs text-slate-300 font-semibold mr-2">Horizon:</span>
          {[7, 30, 60, 90].map(h => (
            <button
              key={h}
              onClick={() => setHorizonDays(h)}
              className={`px-3 py-1 rounded-lg text-xs font-mono font-bold transition ${
                horizonDays === h
                  ? 'bg-cyan-500 text-white shadow-md'
                  : 'text-slate-400 hover:text-white hover:bg-slate-700'
              }`}
            >
              {h} Days
            </button>
          ))}
        </div>
      </div>

      {/* Main Demand Chart */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-bold text-white">Expected Demand & P10 / P95 Uncertainty Bands</h3>
          <span className="text-xs font-mono text-cyan-400">Forecast Horizon: {horizonDays} Days</span>
        </div>
        <div className="h-72">
          <Line 
            data={chartData} 
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

      {/* Demand Table */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden">
        <div className="p-5 border-b border-slate-800 flex items-center justify-between">
          <h3 className="text-sm font-bold text-white">Demand Decomposition by Part Category</h3>
          <span className="text-xs text-slate-400 font-mono">D_total = D_planned + D_failure</span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-300">
            <thead className="bg-slate-800/80 uppercase text-[10px] text-slate-400 font-mono tracking-wider border-b border-slate-800">
              <tr>
                <th className="py-3 px-4">Part Category</th>
                <th className="py-3 px-4 text-center">Planned PM Demand</th>
                <th className="py-3 px-4 text-center">Failure-Driven Demand</th>
                <th className="py-3 px-4 text-center">Total Expected (D*)</th>
                <th className="py-3 px-4 text-center text-emerald-400">P10 (Lower)</th>
                <th className="py-3 px-4 text-center text-rose-400">P95 (Upper)</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-mono">
              {items.map((row, idx) => (
                <tr key={idx} className="hover:bg-slate-800/40 transition">
                  <td className="py-3 px-4 font-bold text-cyan-300">{row.part_category}</td>
                  <td className="py-3 px-4 text-center text-slate-300">{row.planned_pm_demand || row.planned_demand} units</td>
                  <td className="py-3 px-4 text-center text-amber-400">{row.failure_driven_demand || row.failure_demand} units</td>
                  <td className="py-3 px-4 text-center font-bold text-white bg-slate-800/30">{row.total_expected_demand || row.total_demand} units</td>
                  <td className="py-3 px-4 text-center text-emerald-400">{row.p10_uncertainty || row.p10}</td>
                  <td className="py-3 px-4 text-center text-rose-400">{row.p95_uncertainty || row.p95}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
