import React, { useState, useEffect } from 'react';
import { Sidebar, NAVIGATION_ITEMS } from './components/Sidebar';
import { Header } from './components/Header';
import { DemoBanner } from './components/DemoBanner';
import { Dashboard } from './pages/Dashboard';
import { ContractExplorer } from './pages/ContractExplorer';
import { RelativeValueAnalytics } from './pages/RelativeValueAnalytics';
import { BacktestingLab } from './pages/BacktestingLab';
import { SignalCenter } from './pages/SignalCenter';
import { AlertHistory } from './pages/AlertHistory';
import { BhavcopyIngestion } from './pages/BhavcopyIngestion';
import { DataQuality } from './pages/DataQuality';
import { AdminPanel } from './pages/AdminPanel';
import { endpoints } from './api/client';

export const App = () => {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [systemStatus, setSystemStatus] = useState('connecting');
  const [isDemo, setIsDemo] = useState(true);
  const [refreshKey, setRefreshKey] = useState(0);

  const checkHealth = async () => {
    try {
      const res = await endpoints.getHealth();
      setSystemStatus(res.data.status);
      try {
        const dq = await endpoints.getDataQualityReport();
        if (dq.data && typeof dq.data.is_demo_dataset === 'boolean') {
          setIsDemo(dq.data.is_demo_dataset);
        }
      } catch {
        // retain previous state if report check is transient
      }
    } catch {
      setSystemStatus('offline');
    }
  };

  useEffect(() => {
    checkHealth();
    const interval = setInterval(checkHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  const currentNav = NAVIGATION_ITEMS.find((item) => item.id === activeTab) || NAVIGATION_ITEMS[0];

  const handleGlobalRefresh = () => {
    setRefreshKey((prev) => prev + 1);
    checkHealth();
  };

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-navy-950 font-sans text-slate-100">
      {/* Sidebar Navigation */}
      <Sidebar
        activeTab={activeTab}
        onSelectTab={setActiveTab}
        systemStatus={systemStatus}
      />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Top Demo Notification Banner */}
        <DemoBanner isDemo={isDemo} />

        {/* Top Header */}
        <Header
          title={currentNav.label}
          subtitle={`MCX Gold Relative Value Analytics • COZY NEXUS Platform`}
          onRefresh={handleGlobalRefresh}
          isDemo={isDemo}
        />

        {/* Dynamic Page Views */}
        <main className="flex-1 overflow-y-auto p-6">
          <div className="max-w-7xl mx-auto pb-12">
            {activeTab === 'dashboard' && <Dashboard key={refreshKey} onNavigate={setActiveTab} />}
            {activeTab === 'contracts' && <ContractExplorer key={refreshKey} />}
            {activeTab === 'analytics' && <RelativeValueAnalytics key={refreshKey} />}
            {activeTab === 'backtest' && <BacktestingLab key={refreshKey} />}
            {activeTab === 'signals' && <SignalCenter key={refreshKey} />}
            {activeTab === 'alerts' && <AlertHistory key={refreshKey} />}
            {activeTab === 'ingestion' && <BhavcopyIngestion key={refreshKey} onDataChanged={handleGlobalRefresh} />}
            {activeTab === 'quality' && <DataQuality key={refreshKey} />}
            {activeTab === 'admin' && <AdminPanel key={refreshKey} onDataChanged={handleGlobalRefresh} />}
          </div>
        </main>
      </div>
    </div>
  );
};

export default App;
