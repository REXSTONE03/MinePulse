import React from 'react';
import { FileText, ShieldCheck, Clock, User, AlertCircle } from 'lucide-react';

export default function AuditGovernance({ auditLogs, loading }) {
  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="w-8 h-8 border-4 border-cyan-500/30 border-t-cyan-500 rounded-full animate-spin" />
      </div>
    );
  }

  const logs = auditLogs || [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-slate-900 border border-slate-800 p-6 rounded-2xl flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white flex items-center space-x-2">
            <FileText className="w-6 h-6 text-cyan-400" />
            <span>Audit & Operational Governance Trail</span>
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Immutable log of dispatcher overrides, recommendation approvals, and model decision history.
          </p>
        </div>
      </div>

      {/* Audit Logs Table */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden">
        <div className="p-5 border-b border-slate-800 flex items-center justify-between">
          <h3 className="text-sm font-bold text-white">System Audit History</h3>
          <span className="text-xs font-mono text-slate-400">Total Audit Records: {logs.length}</span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-300">
            <thead className="bg-slate-800/80 uppercase text-[10px] text-slate-400 font-mono tracking-wider border-b border-slate-800">
              <tr>
                <th className="py-3 px-4">Timestamp</th>
                <th className="py-3 px-4">User / Actor</th>
                <th className="py-3 px-4">Action</th>
                <th className="py-3 px-4">Recommendation Target</th>
                <th className="py-3 px-4">Override Quantity</th>
                <th className="py-3 px-4">Reason / Justification</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-mono">
              {logs.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-slate-500 italic">
                    No override audit entries recorded yet.
                  </td>
                </tr>
              ) : (
                logs.map((log, idx) => (
                  <tr key={idx} className="hover:bg-slate-800/40 transition">
                    <td className="py-3 px-4 text-slate-400 font-mono">
                      {new Date(log.timestamp || Date.now()).toLocaleString()}
                    </td>
                    <td className="py-3 px-4 font-bold text-white flex items-center space-x-1">
                      <User className="w-3.5 h-3.5 text-cyan-400" />
                      <span>{log.user || log.username || 'dispatcher'}</span>
                    </td>
                    <td className="py-3 px-4">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                        log.action === 'OVERRIDE'
                          ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                          : log.action === 'APPROVE'
                          ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                          : 'bg-rose-500/20 text-rose-400 border border-rose-500/30'
                      }`}>
                        {log.action || 'DISPATCHER_OVERRIDE'}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-cyan-300 font-bold">{log.recommendation_id || log.part_category}</td>
                    <td className="py-3 px-4 font-extrabold text-white">{log.override_quantity || log.quantity} units</td>
                    <td className="py-3 px-4 text-slate-300 italic max-w-xs truncate">{log.reason || 'Standard operational override'}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
