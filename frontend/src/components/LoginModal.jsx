import React, { useState } from 'react';
import { X, Lock, User, AlertCircle, ShieldCheck } from 'lucide-react';
import { api } from '../services/api';

export default function LoginModal({ isOpen, onClose, onLoginSuccess }) {
  const [username, setUsername] = useState('planner');
  const [password, setPassword] = useState('planner123');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  if (!isOpen) return null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      const data = await api.login(username, password);
      onLoginSuccess(data.user);
      onClose();
    } catch (err) {
      setError(err.message || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  const handleQuickSelect = (roleUser, rolePass) => {
    setUsername(roleUser);
    setPassword(rolePass);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-fade-in">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-md w-full p-6 shadow-2xl relative">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800 transition"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="flex items-center space-x-3 mb-6">
          <div className="w-10 h-10 rounded-xl bg-cyan-500/20 border border-cyan-500/40 flex items-center justify-center text-cyan-400">
            <Lock className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-white">Sign In to MinePulse AI</h2>
            <p className="text-xs text-slate-400">OAuth2 / JWT Secured Authentication</p>
          </div>
        </div>

        {error && (
          <div className="mb-4 p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-400 text-xs flex items-center space-x-2">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">Username</label>
            <div className="relative">
              <User className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
                className="w-full bg-slate-800 border border-slate-700 rounded-xl pl-9 pr-4 py-2 text-sm text-white focus:outline-none focus:border-cyan-500 transition"
                placeholder="Enter username"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">Password</label>
            <div className="relative">
              <Lock className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                className="w-full bg-slate-800 border border-slate-700 rounded-xl pl-9 pr-4 py-2 text-sm text-white focus:outline-none focus:border-cyan-500 transition"
                placeholder="Enter password"
              />
            </div>
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
                <ShieldCheck className="w-4 h-4" />
                <span>Authenticate Session</span>
              </>
            )}
          </button>
        </form>

        <div className="mt-6 pt-4 border-t border-slate-800">
          <p className="text-[11px] text-slate-400 font-semibold mb-2 uppercase tracking-wider">Quick Select Demo Roles</p>
          <div className="grid grid-cols-2 gap-2">
            <button
              onClick={() => handleQuickSelect('admin', 'admin123')}
              className="px-2.5 py-1.5 rounded-lg bg-slate-800/80 hover:bg-slate-800 text-left border border-slate-700/60 text-xs transition"
            >
              <div className="font-semibold text-rose-400">ADMIN</div>
              <div className="text-[10px] text-slate-400">admin / admin123</div>
            </button>
            <button
              onClick={() => handleQuickSelect('planner', 'planner123')}
              className="px-2.5 py-1.5 rounded-lg bg-slate-800/80 hover:bg-slate-800 text-left border border-slate-700/60 text-xs transition"
            >
              <div className="font-semibold text-amber-400">PLANNER</div>
              <div className="text-[10px] text-slate-400">planner / planner123</div>
            </button>
            <button
              onClick={() => handleQuickSelect('dispatcher', 'dispatcher123')}
              className="px-2.5 py-1.5 rounded-lg bg-slate-800/80 hover:bg-slate-800 text-left border border-slate-700/60 text-xs transition"
            >
              <div className="font-semibold text-cyan-400">DISPATCHER</div>
              <div className="text-[10px] text-slate-400">dispatcher / dispatcher123</div>
            </button>
            <button
              onClick={() => handleQuickSelect('viewer', 'viewer123')}
              className="px-2.5 py-1.5 rounded-lg bg-slate-800/80 hover:bg-slate-800 text-left border border-slate-700/60 text-xs transition"
            >
              <div className="font-semibold text-slate-400">VIEWER</div>
              <div className="text-[10px] text-slate-400">viewer / viewer123</div>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
