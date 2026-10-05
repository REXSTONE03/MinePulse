import React from 'react';
import { 
  Activity, 
  ShieldAlert, 
  TrendingUp, 
  Package, 
  Wrench, 
  SlidersHorizontal, 
  FileText, 
  LineChart,
  LogOut, 
  User 
} from 'lucide-react';

export default function Navbar({ activeTab, setActiveTab, currentUser, onOpenLogin, onLogout }) {
  const tabs = [
    { id: 'executive', label: 'Executive', icon: Activity },
    { id: 'risk', label: 'Failure Risk', icon: ShieldAlert },
    { id: 'demand', label: 'Demand Forecast', icon: TrendingUp },
    { id: 'inventory', label: 'Inventory (Q*)', icon: Package },
    { id: 'maintenance', label: 'Maintenance', icon: Wrench },
    { id: 'override', label: 'Dispatcher Override', icon: SlidersHorizontal, roleReq: ['ADMIN', 'DISPATCHER'] },
    { id: 'audit', label: 'Audit Log', icon: FileText, roleReq: ['ADMIN', 'DISPATCHER'] },
    { id: 'monitoring', label: 'Model Governance', icon: LineChart },
  ];

  const roleColors = {
    ADMIN: 'bg-rose-500/20 text-rose-400 border-rose-500/30',
    MAINTENANCE_PLANNER: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
    DISPATCHER: 'bg-cyan-500/20 text-cyan-400 border-cyan-500/30',
    VIEWER: 'bg-slate-500/20 text-slate-400 border-slate-500/30',
  };

  return (
    <header className="sticky top-0 z-40 bg-slate-900/90 backdrop-blur-md border-b border-slate-800">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Brand logo */}
          <div className="flex items-center space-x-3 cursor-pointer" onClick={() => setActiveTab('executive')}>
            <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-cyan-500 to-blue-600 flex items-center justify-center shadow-lg shadow-cyan-500/20">
              <Activity className="w-5 h-5 text-white" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="font-bold text-lg tracking-wide text-white">MinePulse</span>
                <span className="text-xs bg-cyan-500/10 text-cyan-400 border border-cyan-500/30 font-semibold px-2 py-0.5 rounded-full">AI v1.0</span>
              </div>
              <p className="text-[10px] text-slate-400 uppercase tracking-widest font-mono">Decision Engine Q*</p>
            </div>
          </div>

          {/* Navigation links */}
          <nav className="hidden lg:flex items-center space-x-1">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              const isActive = activeTab === tab.id;
              const hasAccess = !tab.roleReq || (currentUser && tab.roleReq.includes(currentUser.role));

              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  disabled={!hasAccess}
                  className={`flex items-center space-x-1.5 px-3 py-2 rounded-lg text-xs font-medium transition-all ${
                    isActive
                      ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/30 shadow-sm'
                      : hasAccess
                      ? 'text-slate-300 hover:text-white hover:bg-slate-800/60'
                      : 'text-slate-600 cursor-not-allowed opacity-50'
                  }`}
                  title={!hasAccess ? `Requires ${tab.roleReq.join(' or ')} role` : tab.label}
                >
                  <Icon className="w-4 h-4" />
                  <span>{tab.label}</span>
                </button>
              );
            })}
          </nav>

          {/* User Auth Info & Controls */}
          <div className="flex items-center space-x-3">
            {currentUser ? (
              <div className="flex items-center space-x-3">
                <div className="flex flex-col items-end">
                  <span className="text-xs font-semibold text-slate-200">{currentUser.full_name || currentUser.username}</span>
                  <span className={`text-[10px] px-2 py-0.5 rounded-md border font-mono ${roleColors[currentUser.role] || roleColors.VIEWER}`}>
                    {currentUser.role}
                  </span>
                </div>
                <button
                  onClick={onLogout}
                  className="p-2 rounded-lg bg-slate-800 text-slate-400 hover:text-rose-400 hover:bg-slate-700 transition"
                  title="Logout"
                >
                  <LogOut className="w-4 h-4" />
                </button>
              </div>
            ) : (
              <button
                onClick={onOpenLogin}
                className="flex items-center space-x-2 px-4 py-2 bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white text-xs font-semibold rounded-lg shadow-lg shadow-cyan-500/20 transition"
              >
                <User className="w-4 h-4" />
                <span>Sign In</span>
              </button>
            )}
          </div>
        </div>

        {/* Mobile / Tablet scrollable tab bar */}
        <div className="flex lg:hidden overflow-x-auto space-x-1 py-2 border-t border-slate-800/60 scrollbar-none">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            const hasAccess = !tab.roleReq || (currentUser && tab.roleReq.includes(currentUser.role));

            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                disabled={!hasAccess}
                className={`flex items-center space-x-1 px-3 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap ${
                  isActive
                    ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/30'
                    : hasAccess
                    ? 'text-slate-300 hover:bg-slate-800'
                    : 'text-slate-600 opacity-50'
                }`}
              >
                <Icon className="w-3.5 h-3.5" />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </div>
      </div>
    </header>
  );
}
