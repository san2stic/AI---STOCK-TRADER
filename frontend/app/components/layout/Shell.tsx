'use client';

import { ReactNode } from 'react';
import {
    LayoutDashboard,
    LineChart,
    Users,
    Activity,
    Brain,
    Zap,
    Wifi,
    WifiOff,
    Pause,
    Play,
} from 'lucide-react';
import Button from '../ui/Button';
import Badge from '../ui/Badge';

interface ShellProps {
    children: ReactNode;
    activeTab: string;
    onTabChange: (tab: string) => void;
    wsStatus: 'connecting' | 'connected' | 'disconnected';
    onPause: () => void;
    onResume: () => void;
    isPaused: boolean;
}

const tabs = [
    { id: 'overview', label: 'Overview', icon: LayoutDashboard },
    { id: 'charts', label: 'Charts', icon: LineChart },
    { id: 'crew', label: 'Crew', icon: Users },
    { id: 'live', label: 'Live', icon: Activity },
    { id: 'learning', label: 'Learning', icon: Brain },
];

export default function Shell({
    children,
    activeTab,
    onTabChange,
    wsStatus,
    onPause,
    onResume,
    isPaused,
}: ShellProps) {
    return (
        <div className="min-h-screen bg-background">
            {/* Header */}
            <header className="sticky top-0 z-50 bg-surface/80 backdrop-blur-xl border-b border-surface-border">
                <div className="max-w-[1600px] mx-auto px-6 py-4">
                    <div className="flex items-center justify-between">
                        {/* Logo & Title */}
                        <div className="flex items-center gap-4">
                            <div className="relative">
                                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary to-secondary flex items-center justify-center shadow-glow-primary">
                                    <Zap className="w-5 h-5 text-white" />
                                </div>
                                <div className="absolute -top-1 -right-1 w-3 h-3 rounded-full bg-success animate-pulse" />
                            </div>
                            <div>
                                <h1 className="text-xl font-bold text-white">
                                    NEXUS<span className="text-primary">AI</span>
                                </h1>
                                <p className="text-xs text-gray-500">Trading System</p>
                            </div>
                        </div>

                        {/* Navigation Tabs */}
                        <nav className="hidden md:flex items-center gap-1 bg-surface-elevated/50 rounded-xl p-1">
                            {tabs.map((tab) => {
                                const Icon = tab.icon;
                                const isActive = activeTab === tab.id;
                                return (
                                    <button
                                        key={tab.id}
                                        onClick={() => onTabChange(tab.id)}
                                        className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${isActive
                                                ? 'bg-primary text-white shadow-glow-primary'
                                                : 'text-gray-400 hover:text-white hover:bg-surface-border'
                                            }`}
                                    >
                                        <Icon size={16} />
                                        {tab.label}
                                    </button>
                                );
                            })}
                        </nav>

                        {/* Status & Controls */}
                        <div className="flex items-center gap-4">
                            {/* WebSocket Status */}
                            <div className="flex items-center gap-2">
                                {wsStatus === 'connected' ? (
                                    <Wifi className="w-4 h-4 text-success" />
                                ) : wsStatus === 'connecting' ? (
                                    <Wifi className="w-4 h-4 text-warning animate-pulse" />
                                ) : (
                                    <WifiOff className="w-4 h-4 text-danger" />
                                )}
                                <Badge
                                    variant={
                                        wsStatus === 'connected'
                                            ? 'success'
                                            : wsStatus === 'connecting'
                                                ? 'warning'
                                                : 'danger'
                                    }
                                    size="sm"
                                >
                                    {wsStatus === 'connected'
                                        ? 'Live'
                                        : wsStatus === 'connecting'
                                            ? 'Connecting'
                                            : 'Offline'}
                                </Badge>
                            </div>

                            {/* Pause/Resume */}
                            {isPaused ? (
                                <Button
                                    variant="success"
                                    size="sm"
                                    onClick={onResume}
                                    icon={<Play size={14} />}
                                >
                                    Resume
                                </Button>
                            ) : (
                                <Button
                                    variant="secondary"
                                    size="sm"
                                    onClick={onPause}
                                    icon={<Pause size={14} />}
                                >
                                    Pause
                                </Button>
                            )}
                        </div>
                    </div>
                </div>

                {/* Mobile Navigation */}
                <div className="md:hidden px-4 pb-3">
                    <div className="flex items-center gap-1 overflow-x-auto no-scrollbar">
                        {tabs.map((tab) => {
                            const Icon = tab.icon;
                            const isActive = activeTab === tab.id;
                            return (
                                <button
                                    key={tab.id}
                                    onClick={() => onTabChange(tab.id)}
                                    className={`flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-medium whitespace-nowrap transition-all ${isActive
                                            ? 'bg-primary text-white'
                                            : 'text-gray-400 hover:text-white'
                                        }`}
                                >
                                    <Icon size={14} />
                                    {tab.label}
                                </button>
                            );
                        })}
                    </div>
                </div>
            </header>

            {/* Main Content */}
            <main className="max-w-[1600px] mx-auto px-6 py-8">{children}</main>

            {/* Footer */}
            <footer className="border-t border-surface-border py-6 mt-8">
                <div className="max-w-[1600px] mx-auto px-6">
                    <div className="flex items-center justify-between text-sm text-gray-500">
                        <p>© 2024 NexusAI Trading System</p>
                        <p className="font-mono">
                            Powered by <span className="text-primary">Gemini 3 Pro</span>
                        </p>
                    </div>
                </div>
            </footer>
        </div>
    );
}
