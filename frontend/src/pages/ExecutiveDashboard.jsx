import React from 'react';
import { 
  Truck, 
  AlertTriangle, 
  ShoppingCart, 
  Wrench, 
  ShieldCheck, 
  ArrowUpRight, 
  PackageCheck,
  TrendingUp
} from 'lucide-react';

export default function ExecutiveDashboard({ data, loading, onNavigate }) {
  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="w-8 h-8 border-4 border-cyan-500/30 border-t-cyan-500 rounded-full animate-spin" />
      </div>
    );
  }

  const { snapshot, failureRisk, recommendations, demand } = data || {};

  const totalVehicles = snapshot?.fleet_status?.total_vehicles || 30;
  const activeVehicles = snapshot?.fleet_status?.active_vehicles || 28;
  const inMaintenance = snapshot?.fleet_status?.in_maintenance || 2;

  const urgentReorders = (recommendations || []).filter(r => r.urgency === 'HIGH' || r.urgency === 'CRITICAL').length;
  const criticalFailures = (failureRisk || []).filter(r => r.risk_tier === 'HIGH' || r.p_fail_30d > 0.4).length;

  return (
    <div className="space-[#1e293b] space-y-6">
      {/* Header Banner */}
      <div className="bg-gradient-to-r from-slate-900 via-slate-900 to-cyan-950/40 p-6 rounded-2xl border border-slate-800 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center space-x-3">
            <span>Mining Fleet Executive Overview</span>
            <span className="text-xs bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 px-2.5 py-1 rounded-full font-mono">
              Live Q* Analytics
            </span>
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Real-time fleet failure risk, Weibull survival metrics, and stochastic inventory replenishment decisions.
          </p>
        </div>
        <div className="flex items-center space-x-3">
          <button
            onClick={() => onNavigate('inventory')}
            className="px-4 py-2 bg-cyan-500/10 hover:bg-cyan-500/20 text-cyan-400 border border-cyan-500/30 rounded-xl text-xs font-semibold transition flex items-center space-x-2"
          >
            <span>Run Q* Inventory</span>
            <ArrowUpRight className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Primary KPI Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-slate-900/80 border border-slate-800 p-5 rounded-2xl relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Fleet Operational</span>
            <Truck className="w-5 h-5 text-cyan-400" />
          </div>
          <div className="mt-3 flex items-baseline space-x-2">
            <span className="text-3xl font-extrabold text-white">{activeVehicles} / {totalVehicles}</span>
            <span className="text-xs font-semibold text-emerald-400">({Math.round((activeVehicles/totalVehicles)*100)}%)</span>
          </div>
          <p className="text-xs text-slate-400 mt-2">{inMaintenance} haul trucks in scheduled maintenance</p>
          <div className="absolute bottom-0 left-0 right-0 h-1 bg-gradient-to-r from-cyan-500 to-blue-500" />
        </div>

        <div className="bg-slate-900/80 border border-slate-800 p-5 rounded-2xl relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Critical Maintenance</span>
            <AlertTriangle className="w-5 h-5 text-rose-400" />
          </div>
          <div className="mt-3 flex items-baseline space-x-2">
            <span className="text-3xl font-extrabold text-rose-400">{criticalFailures}</span>
            <span className="text-xs text-slate-400">Components High Risk</span>
          </div>
          <p className="text-xs text-slate-400 mt-2">P(Failure 30d) &gt; 40%</p>
          <div className="absolute bottom-0 left-0 right-0 h-1 bg-rose-500" />
        </div>

        <div className="bg-slate-900/80 border border-slate-800 p-5 rounded-2xl relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Urgent Reorder Q*</span>
            <ShoppingCart className="w-5 h-5 text-amber-400" />
          </div>
          <div className="mt-3 flex items-baseline space-x-2">
            <span className="text-3xl font-extrabold text-amber-400">{urgentReorders}</span>
            <span className="text-xs text-slate-400">Part Categories</span>
          </div>
          <p className="text-xs text-slate-400 mt-2">Stock below safety threshold</p>
          <div className="absolute bottom-0 left-0 right-0 h-1 bg-amber-500" />
        </div>

        <div className="bg-slate-900/80 border border-slate-800 p-5 rounded-2xl relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Active Recommendations</span>
            <PackageCheck className="w-5 h-5 text-emerald-400" />
          </div>
          <div className="mt-3 flex items-baseline space-x-2">
            <span className="text-3xl font-extrabold text-white">{(recommendations || []).length}</span>
            <span className="text-xs text-slate-400">Engine Output</span>
          </div>
          <p className="text-xs text-slate-400 mt-2">Optimized reorder batches</p>
          <div className="absolute bottom-0 left-0 right-0 h-1 bg-emerald-500" />
        </div>
      </div>

      {/* Two Column Section: High Risk & Reorder Highlights */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Top High Risk Components */}
        <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center space-x-2">
              <Wrench className="w-5 h-5 text-rose-400" />
              <h3 className="text-base font-bold text-white">Top High-Risk Components</h3>
            </div>
            <button
              onClick={() => onNavigate('risk')}
              className="text-xs text-cyan-400 hover:text-cyan-300 font-semibold"
            >
              View All &rarr;
            </button>
          </div>
          <div className="space-y-3">
            {(failureRisk || []).slice(0, 4).map((item, idx) => (
              <div key={idx} className="p-3 rounded-xl bg-slate-800/50 border border-slate-700/60 flex items-center justify-between">
                <div>
                  <div className="text-xs font-bold text-white">{item.component_type} — Truck #{item.vehicle_id}</div>
                  <div className="text-[11px] text-slate-400 font-mono mt-0.5">
                    Operating: {item.operating_hours || item.hours} hrs | Age: {item.age_months || 12}m
                  </div>
                </div>
                <div className="text-right">
                  <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                    item.p_fail_30d > 0.4 ? 'bg-rose-500/20 text-rose-400 border border-rose-500/30' : 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                  }`}>
                    {Math.round((item.p_fail_30d || 0.1) * 100)}% Risk (30d)
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Urgent Inventory Reorders (Q*) */}
        <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center space-x-2">
              <TrendingUp className="w-5 h-5 text-cyan-400" />
              <h3 className="text-base font-bold text-white">Top Recommended Reorders (Q*)</h3>
            </div>
            <button
              onClick={() => onNavigate('inventory')}
              className="text-xs text-cyan-400 hover:text-cyan-300 font-semibold"
            >
              View All &rarr;
            </button>
          </div>
          <div className="space-y-3">
            {(recommendations || []).slice(0, 4).map((rec, idx) => (
              <div key={idx} className="p-3 rounded-xl bg-slate-800/50 border border-slate-700/60 flex items-center justify-between">
                <div>
                  <div className="text-xs font-bold text-white">{rec.part_category}</div>
                  <div className="text-[11px] text-slate-400 font-mono mt-0.5">
                    On Hand: {rec.stock_on_hand} | Safety Stock: {rec.safety_stock}
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-xs font-bold text-cyan-400 font-mono">Q* = {rec.recommended_q_star} units</div>
                  <span className={`text-[10px] uppercase font-semibold ${
                    rec.urgency === 'CRITICAL' ? 'text-rose-400' : 'text-amber-400'
                  }`}>
                    {rec.urgency} Priority
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
