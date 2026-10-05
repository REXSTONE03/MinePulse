import React from 'react';
import { Wrench, Calendar, AlertTriangle, ShieldCheck, CheckCircle2 } from 'lucide-react';

export default function MaintenancePlanning({ failureRisk, snapshot, loading }) {
  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="w-8 h-8 border-4 border-cyan-500/30 border-t-cyan-500 rounded-full animate-spin" />
      </div>
    );
  }

  const riskItems = failureRisk || [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-slate-900 border border-slate-800 p-6 rounded-2xl flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white flex items-center space-x-2">
            <Wrench className="w-6 h-6 text-cyan-400" />
            <span>Predictive Maintenance Planning</span>
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Prioritizes work orders by combining Weibull failure probability with scheduled preventive maintenance (PM).
          </p>
        </div>
      </div>

      {/* Maintenance Work Orders Table */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden">
        <div className="p-5 border-b border-slate-800 flex items-center justify-between">
          <h3 className="text-sm font-bold text-white">Recommended Maintenance Work Orders</h3>
          <span className="text-xs font-mono text-slate-400">Total Scheduled: {riskItems.length}</span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-300">
            <thead className="bg-slate-800/80 uppercase text-[10px] text-slate-400 font-mono tracking-wider border-b border-slate-800">
              <tr>
                <th className="py-3 px-4">Vehicle ID</th>
                <th className="py-3 px-4">Component</th>
                <th className="py-3 px-4">Risk Score (30d)</th>
                <th className="py-3 px-4">PM Status</th>
                <th className="py-3 px-4">Recommended Action</th>
                <th className="py-3 px-4 text-center">Priority</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-mono">
              {riskItems.map((item, idx) => {
                const isHighRisk = item.p_fail_30d > 0.4;
                const isMedRisk = item.p_fail_30d > 0.15;
                const pmStatus = isHighRisk ? 'OVERDUE' : isMedRisk ? 'DUE SOON' : 'UP TO DATE';
                const recommendedAction = isHighRisk
                  ? 'Immediate Component Overhaul & Replacement'
                  : isMedRisk
                  ? 'Schedule Inspection & Fluid Sampling'
                  : 'Continue Routine Operation';

                return (
                  <tr key={idx} className="hover:bg-slate-800/40 transition">
                    <td className="py-3 px-4 font-bold text-white">Truck #{item.vehicle_id}</td>
                    <td className="py-3 px-4 text-cyan-300 font-semibold">{item.component_type}</td>
                    <td className="py-3 px-4 font-bold text-amber-400">
                      {(item.p_fail_30d * 100).toFixed(1)}%
                    </td>
                    <td className="py-3 px-4">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                        pmStatus === 'OVERDUE'
                          ? 'bg-rose-500/20 text-rose-400 border border-rose-500/30'
                          : pmStatus === 'DUE SOON'
                          ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                          : 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                      }`}>
                        {pmStatus}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-slate-200">{recommendedAction}</td>
                    <td className="py-3 px-4 text-center">
                      <span className={`px-2.5 py-1 rounded text-[10px] font-bold uppercase ${
                        isHighRisk ? 'bg-rose-500/20 text-rose-400' : isMedRisk ? 'bg-amber-500/20 text-amber-400' : 'bg-slate-800 text-slate-400'
                      }`}>
                        {isHighRisk ? 'CRITICAL' : isMedRisk ? 'HIGH' : 'NORMAL'}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
