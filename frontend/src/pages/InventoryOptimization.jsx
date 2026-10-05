import React from 'react';
import { Package, ShoppingCart, AlertCircle, ArrowUpRight, CheckCircle2 } from 'lucide-react';

export default function InventoryOptimization({ recommendations, loading, onOpenOverride, currentUser }) {
  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="w-8 h-8 border-4 border-cyan-500/30 border-t-cyan-500 rounded-full animate-spin" />
      </div>
    );
  }

  const items = recommendations || [];

  const canOverride = currentUser && (currentUser.role === 'ADMIN' || currentUser.role === 'DISPATCHER');

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-slate-900 border border-slate-800 p-6 rounded-2xl flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white flex items-center space-x-2">
            <Package className="w-6 h-6 text-cyan-400" />
            <span>Q* Inventory Optimization Engine</span>
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Calculates safety stock thresholds, projected shortages, and cost-optimal reorder quantities Q*.
          </p>
        </div>
      </div>

      {/* Main Table */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden">
        <div className="p-5 border-b border-slate-800 flex items-center justify-between">
          <h3 className="text-sm font-bold text-white">Stochastic Inventory Reorder Recommendations</h3>
          <span className="text-xs font-mono text-slate-400">Total Items: {items.length}</span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-300">
            <thead className="bg-slate-800/80 uppercase text-[10px] text-slate-400 font-mono tracking-wider border-b border-slate-800">
              <tr>
                <th className="py-3 px-4">Part Category</th>
                <th className="py-3 px-4 text-center">On Hand</th>
                <th className="py-3 px-4 text-center">On Order</th>
                <th className="py-3 px-4 text-center">Allocated</th>
                <th className="py-3 px-4 text-center">Safety Stock</th>
                <th className="py-3 px-4 text-center">Shortage</th>
                <th className="py-3 px-4 text-center font-bold text-cyan-400">Q* Reorder</th>
                <th className="py-3 px-4 text-center">Lead Time</th>
                <th className="py-3 px-4 text-center">Priority</th>
                <th className="py-3 px-4 text-center">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-mono">
              {items.map((row, idx) => (
                <tr key={idx} className="hover:bg-slate-800/40 transition">
                  <td className="py-3 px-4 font-bold text-white flex items-center space-x-2">
                    <span>{row.part_category}</span>
                  </td>
                  <td className="py-3 px-4 text-center">{row.stock_on_hand}</td>
                  <td className="py-3 px-4 text-center">{row.stock_on_order}</td>
                  <td className="py-3 px-4 text-center">{row.allocated_stock || 0}</td>
                  <td className="py-3 px-4 text-center font-semibold text-slate-300">{row.safety_stock}</td>
                  <td className="py-3 px-4 text-center font-bold text-rose-400">
                    {row.projected_shortage > 0 ? `-${row.projected_shortage}` : '0'}
                  </td>
                  <td className="py-3 px-4 text-center font-extrabold text-cyan-400 bg-cyan-950/20 text-sm">
                    {row.recommended_q_star}
                  </td>
                  <td className="py-3 px-4 text-center">{row.lead_time_days || row.lead_time || 7} days</td>
                  <td className="py-3 px-4 text-center">
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                      row.urgency === 'CRITICAL'
                        ? 'bg-rose-500/20 text-rose-400 border border-rose-500/30'
                        : row.urgency === 'HIGH'
                        ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                        : 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                    }`}>
                      {row.urgency}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-center">
                    <button
                      onClick={() => onOpenOverride(row)}
                      disabled={!canOverride}
                      className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition flex items-center space-x-1 justify-center mx-auto ${
                        canOverride
                          ? 'bg-cyan-500/10 hover:bg-cyan-500/20 text-cyan-400 border border-cyan-500/30'
                          : 'bg-slate-800 text-slate-600 cursor-not-allowed border border-slate-700/50'
                      }`}
                      title={!canOverride ? 'Requires DISPATCHER or ADMIN role' : 'Apply Dispatcher Override'}
                    >
                      <ShoppingCart className="w-3.5 h-3.5" />
                      <span>Override</span>
                    </button>
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
