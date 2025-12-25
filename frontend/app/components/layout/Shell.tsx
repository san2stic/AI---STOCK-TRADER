'use client';

import { useState } from 'react';
import { BarChart3, LineChart as LineChartIcon, Users, Activity } from 'lucide-react';

interface ShellProps {
    children: React.ReactNode;
    activeTab: string;
    onTabChange: (tab: string) => void;
    wsStatus: 'connecting' | 'connected' | 'disconnected';
}

export default function Shell({ children, activeTab, onTabChange, wsStatus }: ShellProps) {
    const tabs = [
        { id: 'overview', label: "Vue d'ensemble", icon: BarChart3 },
        { id: 'charts', label: 'Graphiques', icon: LineChartIcon },
        { id: 'crew', label: 'Équipe', icon: Users },
        { id: 'live', label: 'Messages Live', icon: Activity },
    ];

    return (
        <div className="min-h-screen relative overflow-hidden">
            {/* Background Ambience */}
            <div className="fixed inset-0 pointer-events-none z-0">
                <div className="absolute top-[-10%] left-[-10%] w-[50%] h-[50%] bg-primary-glow blur-[120px] opacity-20 animate-pulse-glow" />
                <div className="absolute bottom-[-10%] right-[-10%] w-[50%] h-[50%] bg-accent-purple blur-[120px] opacity-10 animate-pulse delay-1000" />
            </div>

            <div className="relative z-10 max-w-7xl mx-auto p-6 lg:p-8">
                {/* Header */}
                <header className="mb-8 animate-fade-in-up">
                    <div className="flex items-center justify-between mb-8">
                        <div>
                            <h1 className="text-4xl lg:text-5xl font-bold mb-2 bg-clip-text text-transparent bg-gradient-to-r from-primary via-secondary to-accent animate-gradient">
                                AI Trading System
                            </h1>
                            <p className="text-lg text-gray-400 font-light">
                                Système autonome multi-agents avec <span className="text-primary font-mono">6 IA</span>
                            </p>
                        </div>

                        {/* Status Indicator */}
                        <div className="glass px-4 py-2 rounded-full flex items-center gap-3">
                            <div className={`relative w-3 h-3`}>
                                <div className={`absolute inset-0 rounded-full animate-ping opacity-75 ${wsStatus === 'connected' ? 'bg-success' :
                                        wsStatus === 'connecting' ? 'bg-warning' : 'bg-danger'
                                    }`} />
                                <div className={`relative w-3 h-3 rounded-full ${wsStatus === 'connected' ? 'bg-success shadow-[0_0_10px_#00e676]' :
                                        wsStatus === 'connecting' ? 'bg-warning' : 'bg-danger'
                                    }`} />
                            </div>
                            <span className="text-sm font-medium tracking-wide">
                                {wsStatus === 'connected' ? 'SYSTEM ONLINE' :
                                    wsStatus === 'connecting' ? 'CONNECTING...' : 'OFFLINE'}
                            </span>
                        </div>
                    </div>

                    {/* Navigation Tabs */}
                    <nav className="flex gap-4 overflow-x-auto pb-4 custom-scrollbar">
                        {tabs.map(tab => {
                            const Icon = tab.icon;
                            const isActive = activeTab === tab.id;

                            return (
                                <button
                                    key={tab.id}
                                    onClick={() => onTabChange(tab.id)}
                                    className={`
                    group flex items-center gap-3 px-6 py-3 rounded-xl font-medium transition-all duration-300 relative overflow-hidden
                    ${isActive
                                            ? 'text-white shadow-neon'
                                            : 'text-gray-400 hover:text-white hover:bg-white/5'
                                        }
                  `}
                                >
                                    {isActive && (
                                        <div className="absolute inset-0 bg-gradient-to-r from-primary/20 to-secondary/20 backdrop-blur-sm border border-primary/30 rounded-xl" />
                                    )}

                                    <Icon className={`w-5 h-5 relative z-10 transition-transform group-hover:scale-110 ${isActive ? 'text-primary' : ''}`} />
                                    <span className="relative z-10">{tab.label}</span>
                                </button>
                            );
                        })}
                    </nav>
                </header>

                {/* Content Area */}
                <main className="animate-fade-in-up md:delay-100">
                    {children}
                </main>
            </div>
        </div>
    );
}
