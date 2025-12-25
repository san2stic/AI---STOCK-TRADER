'use client';

import { useState, useEffect } from 'react';
import {
    LayoutDashboard,
    LineChart,
    Users,
    Activity,
    Brain,
    Play,
    Pause,
    Zap,
    Menu,
    X,
    Cpu
} from 'lucide-react';

interface ShellProps {
    children: React.ReactNode;
    activeTab: string;
    onTabChange: (tab: string) => void;
    wsStatus: 'connecting' | 'connected' | 'disconnected';
    onPause: () => void;
    onResume: () => void;
    isPaused: boolean;
}

export default function Shell({
    children,
    activeTab,
    onTabChange,
    wsStatus,
    onPause,
    onResume,
    isPaused
}: ShellProps) {
    const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
    const [mounted, setMounted] = useState(false);

    useEffect(() => {
        setMounted(true);
    }, []);

    const tabs = [
        { id: 'overview', label: "Vue d'ensemble", icon: LayoutDashboard },
        { id: 'charts', label: 'Graphiques', icon: LineChart },
        { id: 'learning', label: 'Cerveau Alpha', icon: Brain },
        { id: 'crew', label: 'Équipe Agents', icon: Users },
        { id: 'live', label: 'Flux Live', icon: Activity },
    ];

    const getStatusColor = () => {
        switch (wsStatus) {
            case 'connected': return 'text-status-success shadow-neon-blue';
            case 'connecting': return 'text-status-warning';
            case 'disconnected': return 'text-status-error';
            default: return 'text-gray-500';
        }
    };

    if (!mounted) return null;

    return (
        <div className="min-h-screen bg-background text-white font-sans selection:bg-primary/20">
            {/* Background Ambience */}
            <div className="fixed inset-0 z-0 pointer-events-none overflow-hidden">
                <div className="absolute top-0 left-0 w-full h-full bg-cyber-grid opacity-20" />
                <div className="absolute top-[-20%] left-[-10%] w-[500px] h-[500px] bg-primary/20 blur-[120px] rounded-full mix-blend-screen animate-pulse-slow" />
                <div className="absolute bottom-[-20%] right-[-10%] w-[600px] h-[600px] bg-secondary/10 blur-[120px] rounded-full mix-blend-screen animate-pulse-slow delay-700" />
            </div>

            {/* Sidebar Navigation - Desktop */}
            <aside className="fixed left-0 top-0 h-full w-20 lg:w-64 glass-panel border-r border-surface-border z-40 hidden md:flex flex-col transition-all duration-300">
                <div className="h-20 flex items-center justify-center lg:justify-start lg:px-6 border-b border-surface-border">
                    <div className="flex items-center gap-3">
                        <div className="relative">
                            <div className="absolute inset-0 bg-primary blur-md opacity-50 animate-pulse" />
                            <Cpu className="w-8 h-8 text-primary relative z-10" />
                        </div>
                        <span className="hidden lg:block font-display font-bold text-xl tracking-wider text-transparent bg-clip-text bg-gradient-to-r from-primary to-secondary">
                            NEXUS TRADER
                        </span>
                    </div>
                </div>

                <nav className="flex-1 py-8 px-2 lg:px-4 space-y-2">
                    {tabs.map(tab => {
                        const Icon = tab.icon;
                        const isActive = activeTab === tab.id;
                        return (
                            <button
                                key={tab.id}
                                onClick={() => onTabChange(tab.id)}
                                className={`
                                    w-full flex items-center justify-center lg:justify-start gap-4 p-3 rounded-xl transition-all duration-200 group relative
                                    ${isActive
                                        ? 'bg-primary/10 text-primary shadow-neon-blue'
                                        : 'text-gray-400 hover:text-white hover:bg-white/5'
                                    }
                                `}
                            >
                                <Icon className={`w-6 h-6 ${isActive ? 'animate-pulse' : 'group-hover:scale-110 transition-transform'}`} />
                                <span className="hidden lg:block font-medium tracking-wide">{tab.label}</span>
                                {isActive && <div className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-8 bg-primary rounded-r-full" />}
                            </button>
                        );
                    })}
                </nav>

                <div className="p-4 border-t border-surface-border">
                    <div className="glass-panel p-4 rounded-xl flex items-center justify-center lg:justify-start gap-3">
                        <div className={`w-3 h-3 rounded-full ${wsStatus === 'connected' ? 'bg-status-success animate-pulse' : 'bg-status-error'}`} />
                        <div className="hidden lg:block">
                            <p className="text-xs text-gray-400 uppercase font-bold tracking-widest">System Status</p>
                            <p className={`text-sm font-bold ${getStatusColor()}`}>
                                {wsStatus === 'connected' ? 'ONLINE' : 'OFFLINE'}
                            </p>
                        </div>
                    </div>
                </div>
            </aside>

            {/* Mobile Header */}
            <header className="md:hidden fixed top-0 w-full z-50 glass-panel border-b border-surface-border h-16 flex items-center justify-between px-4">
                <div className="flex items-center gap-2">
                    <Cpu className="w-6 h-6 text-primary" />
                    <span className="font-display font-bold text-lg">NEXUS</span>
                </div>
                <button
                    onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
                    className="p-2 text-gray-400 hover:text-white"
                >
                    {isMobileMenuOpen ? <X /> : <Menu />}
                </button>
            </header>

            {/* Main Content Area */}
            <main className="md:pl-20 lg:pl-64 pt-20 md:pt-0 min-h-screen relative z-10 flex flex-col">
                {/* Top Bar */}
                <header className="h-20 px-8 flex items-center justify-between sticky top-0 z-30 glass-panel border-b border-surface-border backdrop-blur-md">
                    <div>
                        <h2 className="text-2xl font-bold text-white capitalize tracking-tight flex items-center gap-3">
                            {tabs.find(t => t.id === activeTab)?.icon && (
                                <span className="p-2 bg-surface rounded-lg border border-surface-border">
                                    {(() => {
                                        const Icon = tabs.find(t => t.id === activeTab)?.icon;
                                        return Icon ? <Icon className="w-5 h-5 text-primary" /> : null;
                                    })()}
                                </span>
                            )}
                            {tabs.find(t => t.id === activeTab)?.label}
                        </h2>
                    </div>

                    <div className="flex items-center gap-4">
                        {/* Trading Control Button */}
                        <button
                            onClick={isPaused ? onResume : onPause}
                            className={`
                                flex items-center gap-3 px-6 py-2.5 rounded-lg font-bold tracking-wide transition-all duration-300 border
                                ${isPaused
                                    ? 'bg-status-warning/10 text-status-warning border-status-warning/50 hover:bg-status-warning/20'
                                    : 'bg-primary/10 text-primary border-primary/50 hover:bg-primary/20 hover:shadow-neon-blue'
                                }
                            `}
                        >
                            {isPaused ? (
                                <>
                                    <Pause size={18} fill="currentColor" />
                                    <span>TRADING EN PAUSE</span>
                                </>
                            ) : (
                                <>
                                    <Zap size={18} className="animate-pulse" />
                                    <span>SYSTEM ACTIVE</span>
                                </>
                            )}
                        </button>
                    </div>
                </header>

                {/* Dashboard Content */}
                <div className="flex-1 p-6 lg:p-10 overflow-x-hidden">
                    <div className="animate-slide-up">
                        {children}
                    </div>
                </div>
            </main>

            {/* Mobile Menu Overlay */}
            {isMobileMenuOpen && (
                <div className="fixed inset-0 z-50 md:hidden bg-background">
                    <div className="p-4 flex flex-col h-full">
                        <div className="flex justify-end mb-8">
                            <button onClick={() => setIsMobileMenuOpen(false)}><X className="w-8 h-8" /></button>
                        </div>
                        <nav className="space-y-4">
                            {tabs.map(tab => (
                                <button
                                    key={tab.id}
                                    onClick={() => {
                                        onTabChange(tab.id);
                                        setIsMobileMenuOpen(false);
                                    }}
                                    className={`w-full text-left p-4 rounded-xl text-lg font-medium border border-transparent ${activeTab === tab.id
                                            ? 'bg-primary/10 text-primary border-primary/30'
                                            : 'text-gray-400'
                                        }`}
                                >
                                    <div className="flex items-center gap-3">
                                        <tab.icon />
                                        {tab.label}
                                    </div>
                                </button>
                            ))}
                        </nav>
                    </div>
                </div>
            )}
        </div>
    );
}
