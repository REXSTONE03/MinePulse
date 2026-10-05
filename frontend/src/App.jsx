import React, { useState, useEffect } from 'react';
import Navbar from './components/Navbar';
import LoginModal from './components/LoginModal';

import ExecutiveDashboard from './pages/ExecutiveDashboard';
import FailureRiskDashboard from './pages/FailureRiskDashboard';
import DemandForecastDashboard from './pages/DemandForecastDashboard';
import InventoryOptimization from './pages/InventoryOptimization';
import MaintenancePlanning from './pages/MaintenancePlanning';
import DispatcherOverrideModal from './pages/DispatcherOverrideModal';
import AuditGovernance from './pages/AuditGovernance';
import ModelMonitoring from './pages/ModelMonitoring';

import { api, getCurrentUser } from './services/api';

export default function App() {
  const [activeTab, setActiveTab] = useState('executive');
  const [currentUser, setCurrentUser] = useState(() => getCurrentUser());
  const [isLoginOpen, setIsLoginOpen] = useState(false);
  const [selectedOverrideItem, setSelectedOverrideItem] = useState(null);

  const [horizonDays, setHorizonDays] = useState(30);

  // Application Data States
  const [snapshot, setSnapshot] = useState(null);
  const [failureRisk, setFailureRisk] = useState([]);
  const [demand, setDemand] = useState([]);
  const [recommendations, setRecommendations] = useState([]);
  const [auditLogs, setAuditLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const fetchData = async () => {
    setLoading(true);
    setError('');
    try {
      const [snapRes, riskRes, demRes, recRes, auditRes] = await Promise.allSettled([
        api.getSnapshotSummary(),
        api.getFailureRiskPredictions(),
        api.getDemandForecasts(horizonDays),
        api.getRecommendations(),
        api.getAuditLogs(),
      ]);

      if (snapRes.status === 'fulfilled') setSnapshot(snapRes.value);
      if (riskRes.status === 'fulfilled') setFailureRisk(riskRes.value);
      if (demRes.status === 'fulfilled') setDemand(demRes.value);
      if (recRes.status === 'fulfilled') setRecommendations(recRes.value);
      if (auditRes.status === 'fulfilled') setAuditLogs(auditRes.value);
    } catch (err) {
      setError(err.message || 'Failed to load system data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [horizonDays]);

  const handleLoginSuccess = (user) => {
    setCurrentUser(user);
    fetchData();
  };

  const handleLogout = () => {
    api.logout();
    setCurrentUser(null);
  };

  const handleOpenOverride = (item) => {
    setSelectedOverrideItem(item);
  };

  const handleOverrideSuccess = () => {
    fetchData();
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans antialiased selection:bg-cyan-500 selection:text-white">
      {/* Top Header Navigation */}
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        currentUser={currentUser}
        onOpenLogin={() => setIsLoginOpen(true)}
        onLogout={handleLogout}
      />

      {/* Main View Container */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {error && (
          <div className="mb-6 p-4 rounded-2xl bg-rose-500/10 border border-rose-500/30 text-rose-400 text-xs flex items-center justify-between">
            <span>{error}</span>
            <button
              onClick={fetchData}
              className="px-3 py-1 bg-rose-500/20 hover:bg-rose-500/30 border border-rose-500/40 rounded-lg text-[11px] font-semibold"
            >
              Retry Connection
            </button>
          </div>
        )}

        {activeTab === 'executive' && (
          <ExecutiveDashboard
            data={{ snapshot, failureRisk, recommendations, demand }}
            loading={loading}
            onNavigate={setActiveTab}
          />
        )}

        {activeTab === 'risk' && (
          <FailureRiskDashboard failureRisk={failureRisk} loading={loading} />
        )}

        {activeTab === 'demand' && (
          <DemandForecastDashboard
            demand={demand}
            horizonDays={horizonDays}
            setHorizonDays={setHorizonDays}
            loading={loading}
          />
        )}

        {activeTab === 'inventory' && (
          <InventoryOptimization
            recommendations={recommendations}
            loading={loading}
            onOpenOverride={handleOpenOverride}
            currentUser={currentUser}
          />
        )}

        {activeTab === 'maintenance' && (
          <MaintenancePlanning
            failureRisk={failureRisk}
            snapshot={snapshot}
            loading={loading}
          />
        )}

        {activeTab === 'override' && (
          <div className="space-y-6">
            <div className="p-4 rounded-2xl bg-slate-900 border border-slate-800 text-xs text-slate-400">
              Select an item from the <button onClick={() => setActiveTab('inventory')} className="text-cyan-400 font-bold underline">Inventory Tab</button> to launch the Dispatcher Override modal.
            </div>
            <AuditGovernance auditLogs={auditLogs} loading={loading} />
          </div>
        )}

        {activeTab === 'audit' && (
          <AuditGovernance auditLogs={auditLogs} loading={loading} />
        )}

        {activeTab === 'monitoring' && (
          <ModelMonitoring currentUser={currentUser} />
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-800/80 bg-slate-900/40 py-4 mt-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between text-xs text-slate-500 gap-2">
          <div>MinePulse AI — Stochastic Mining Inventory & Maintenance Platform</div>
          <div className="font-mono text-[11px]">Backend API: FastAPI | DB: PostgreSQL/SQLite | Q* Engine</div>
        </div>
      </footer>

      {/* Modals */}
      <LoginModal
        isOpen={isLoginOpen}
        onClose={() => setIsLoginOpen(false)}
        onLoginSuccess={handleLoginSuccess}
      />

      {selectedOverrideItem && (
        <DispatcherOverrideModal
          item={selectedOverrideItem}
          onClose={() => setSelectedOverrideItem(null)}
          onSuccess={handleOverrideSuccess}
        />
      )}
    </div>
  );
}
