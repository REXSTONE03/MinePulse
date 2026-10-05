import React, { useState } from 'react';
import { X, SlidersHorizontal, AlertCircle, CheckCircle2, ShieldAlert } from 'lucide-react';
import { api } from '../services/api';

export default function DispatcherOverrideModal({ item, onClose, onSuccess }) {
  const [decision, setDecision] = useState('OVERRIDE');
  const [overrideQuantity, setOverrideQuantity] = useState(item?.recommended_q_star || 10);
  const [reason, setReason] = useState('Adjusted based on mine operational shift demand');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [successMsg, setSuccessMsg] = useState('');

  if (!item) return null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setSuccessMsg('');

    try {
      const payload = {
        recommendation_id: item.recommendation_id || item.id || `REC-${item.part_category}`,
        part_category: item.part_category,
        decision,
        override_quantity: parseInt(overrideQuantity, 10),
        reason,
      };

      const res = await api.applyDispatcherOverride(payload);
      setSuccessMsg('Override recorded successfully in Audit Trail!');
      setTimeout(() => {
        onSuccess(res);
        onClose();
      }, 1200);
    } catch (err) {
      setError(err.message || 'Failed to submit override');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-fade-in">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-lg w-full p-6 shadow-2xl relative">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800 transition"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="flex items-center space-x-3 mb-6">
          <div className="w-10 h-10 rounded-xl bg-cyan-500/20 border border-cyan-500/40 flex items-center justify-center text-cyan-400">
            <SlidersHorizontal className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-white">Dispatcher Override Panel</h2>
            <p className="text-xs text-slate-400">Audit-backed human intervention for Q* recommendation</p>
          </div>
        </div>

        {error && (
          <div className="mb-4 p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-400 text-xs flex items-center space-x-2">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {successMsg && (
          <div className="mb-4 p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs flex items-center space-x-2">
            <CheckCircle2 className="w-4 h-4 shrink-0" />
            <span>{successMsg}</span>
          </div>
        )}

        <div className="p-3 mb-4 rounded-xl bg-slate-800/60 border border-slate-700/60 text-xs space-y-1">
          <div className="text-slate-400 font-mono">Part Category: <span className="text-cyan-400 font-bold">{item.part_category}</span></div>
          <div className="text-slate-400 font-mono">Original System Q*: <span className="text-white font-bold">{item.recommended_q_star} units</span></div>
          <div className="text-slate-400 font-mono">Safety Stock: <span className="text-white">{item.safety_stock}</span></div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">Decision Action</label>
            <select
              value={decision}
              onChange={(e) => setDecision(e.target.value)}
              className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:border-cyan-500 transition"
            >
              <option value="OVERRIDE">OVERRIDE Quantity</option>
              <option value="APPROVE">APPROVE System Q*</option>
              <option value="REJECT">REJECT Reorder Recommendation</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">Override Quantity (Units)</label>
            <input
              type="number"
              value={overrideQuantity}
              onChange={(e) => setOverrideQuantity(e.target.value)}
              disabled={decision !== 'OVERRIDE'}
              required
              min="0"
              className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:border-cyan-500 transition disabled:opacity-50 font-mono"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">Override Justification / Reason</label>
            <textarea
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              required
              rows={3}
              className="w-full bg-slate-800 border border-slate-700 rounded-xl p-3 text-xs text-white focus:outline-none focus:border-cyan-500 transition"
              placeholder="Provide formal audit justification for override..."
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-2.5 bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white font-semibold text-sm rounded-xl shadow-lg shadow-cyan-500/20 transition flex items-center justify-center space-x-2"
          >
            {loading ? (
              <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            ) : (
              <>
                <ShieldAlert className="w-4 h-4" />
                <span>Confirm Dispatcher Override</span>
              </>
            )}
          </button>
        </form>
      </div>
    </div>
  );
}
