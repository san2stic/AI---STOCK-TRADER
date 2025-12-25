'use client';

import { useState, useEffect } from 'react';
import { Activity } from 'lucide-react';
import Shell from './components/layout/Shell';
import AgentCard from './components/dashboard/AgentCard';
import RealTimeFunds from './components/dashboard/RealTimeFunds';
import NextScanCountdown from './components/dashboard/NextScanCountdown';
import ManualScanButton from './components/dashboard/ManualScanButton';
import TradingModeControl from './components/dashboard/TradingModeControl';
import StockCryptoSplit from './components/dashboard/StockCryptoSplit';
import LiveScoreBoard from './components/dashboard/LiveScoreBoard';
import AgentDetailModal from './components/dashboard/AgentDetailModal';
import LiveMessageFeed from './components/trading/LiveMessageFeed';
import PerformanceCharts from './components/trading/PerformanceCharts';
import EconomicCalendar from './components/trading/EconomicCalendar';
import CrewDashboard from './components/trading/CrewDashboard';
import LearningDashboard from './components/trading/LearningDashboard';
import ErrorBoundary from './components/ErrorBoundary';
import Card from './components/ui/Card';
import Badge from './components/ui/Badge';

interface Agent {
    name: string;
    total_value: number;
    pnl: number;
    pnl_percent: number;
    total_trades: number;
    win_rate: number;
    cash: number;
    positions_count: number;
}

interface Message {
    type: string;
    timestamp: string;
    agent?: string;
    data: any;
}

type TabType = 'overview' | 'charts' | 'crew' | 'live' | 'learning';

export default function Home() {
    const [activeTab, setActiveTab] = useState<TabType>('overview');
    const [agents, setAgents] = useState<Agent[]>([]);
    const [loading, setLoading] = useState(true);
    const [messages, setMessages] = useState<Message[]>([]);
    const [wsStatus, setWsStatus] = useState<'connecting' | 'connected' | 'disconnected'>('connecting');
    const [selectedAgent, setSelectedAgent] = useState<string | null>(null);
    const [isPaused, setIsPaused] = useState(false);

    // Fetch agents data
    useEffect(() => {
        const fetchAgents = async () => {
            try {
                const res = await fetch('/api/agents');
                if (res.ok) {
                    const data = await res.json();
                    setAgents(data.agents || []);
                }
            } catch (error) {
                console.error('Failed to fetch agents:', error);
            } finally {
                setLoading(false);
            }
        };

        fetchAgents();
        const interval = setInterval(fetchAgents, 30000);
        return () => clearInterval(interval);
    }, []);

    // WebSocket connection
    useEffect(() => {
        const connectWebSocket = () => {
            let wsUrl: string;
            if (typeof window !== 'undefined') {
                const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                const host = window.location.host;
                wsUrl = `${protocol}//${host}/ws`;
            } else {
                wsUrl = 'ws://backend:8000/ws';
            }

            const websocket = new WebSocket(wsUrl);

            websocket.onopen = () => {
                console.log('WebSocket connected');
                setWsStatus('connected');
            };

            websocket.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    const message: Message = {
                        type: data.type || 'unknown',
                        timestamp: data.timestamp || new Date().toISOString(),
                        agent: data.agent,
                        data: data,
                    };
                    setMessages((prev) => [message, ...prev].slice(0, 200));

                    // Refresh agents on important events
                    if (['trade', 'decision', 'agent_decision'].includes(data.type)) {
                        fetch('/api/agents')
                            .then((res) => res.json())
                            .then((data) => setAgents(data.agents || []))
                            .catch(console.error);
                    }
                } catch (error) {
                    console.error('Failed to parse WebSocket message:', error);
                }
            };

            websocket.onerror = () => {
                setWsStatus('disconnected');
            };

            websocket.onclose = () => {
                console.log('WebSocket disconnected, reconnecting...');
                setWsStatus('disconnected');
                setTimeout(connectWebSocket, 3000);
            };

            return websocket;
        };

        const ws = connectWebSocket();
        return () => ws.close();
    }, []);

    const handlePause = async () => {
        try {
            await fetch('/api/trading/pause', { method: 'POST' });
            setIsPaused(true);
        } catch (error) {
            console.error('Failed to pause trading:', error);
        }
    };

    const handleResume = async () => {
        try {
            await fetch('/api/trading/resume', { method: 'POST' });
            setIsPaused(false);
        } catch (error) {
            console.error('Failed to resume trading:', error);
        }
    };

    if (loading && agents.length === 0) {
        return (
            <div className="min-h-screen bg-background flex items-center justify-center">
                <div className="text-center">
                    <div className="loading-spinner mx-auto mb-4" />
                    <p className="text-white text-xl font-semibold animate-pulse">
                        Initializing NexusAI...
                    </p>
                </div>
            </div>
        );
    }

    return (
        <>
            <Shell
                activeTab={activeTab}
                onTabChange={(tab) => setActiveTab(tab as TabType)}
                wsStatus={wsStatus}
                onPause={handlePause}
                onResume={handleResume}
                isPaused={isPaused}
            >
                {/* Overview Tab */}
                {activeTab === 'overview' && (
                    <div className="space-y-8 animate-fade-in">
                        {/* Top Stats Row */}
                        <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
                            <div className="xl:col-span-2">
                                <ErrorBoundary>
                                    <RealTimeFunds />
                                </ErrorBoundary>
                            </div>
                            <div className="xl:col-span-1 space-y-4">
                                <ErrorBoundary>
                                    <NextScanCountdown />
                                </ErrorBoundary>
                                <ErrorBoundary>
                                    <ManualScanButton />
                                </ErrorBoundary>
                            </div>
                        </div>

                        {/* Controls Row */}
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                            <ErrorBoundary>
                                <TradingModeControl />
                            </ErrorBoundary>
                            <ErrorBoundary>
                                <StockCryptoSplit />
                            </ErrorBoundary>
                        </div>

                        {/* Leaderboard & Calendar */}
                        <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
                            <div className="xl:col-span-2">
                                <ErrorBoundary>
                                    <LiveScoreBoard agents={agents} />
                                </ErrorBoundary>
                            </div>
                            <div className="xl:col-span-1">
                                <ErrorBoundary>
                                    <EconomicCalendar daysAhead={7} minImpact="MEDIUM" />
                                </ErrorBoundary>
                            </div>
                        </div>

                        {/* Agent Grid */}
                        <div>
                            <div className="flex items-center justify-between mb-6">
                                <h2 className="text-2xl font-bold text-white flex items-center gap-3">
                                    <span className="w-1.5 h-8 bg-gradient-to-b from-primary to-secondary rounded-full" />
                                    AI Trading Agents
                                </h2>
                                <Badge variant="info" dot pulse>
                                    {agents.length} Active
                                </Badge>
                            </div>

                            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
                                {agents.map((agent) => (
                                    <AgentCard
                                        key={agent.name}
                                        agent={agent}
                                        onClick={() => setSelectedAgent(agent.name)}
                                    />
                                ))}
                            </div>
                        </div>
                    </div>
                )}

                {/* Charts Tab */}
                {activeTab === 'charts' && (
                    <ErrorBoundary>
                        <PerformanceCharts agents={agents} />
                    </ErrorBoundary>
                )}

                {/* Crew Tab */}
                {activeTab === 'crew' && (
                    <ErrorBoundary>
                        <CrewDashboard />
                    </ErrorBoundary>
                )}

                {/* Live Tab */}
                {activeTab === 'live' && (
                    <Card variant="glass" padding="none" className="min-h-[80vh] flex flex-col">
                        <div className="p-6 border-b border-surface-border">
                            <h2 className="text-2xl font-bold flex items-center gap-3">
                                <Activity className="text-primary animate-pulse" />
                                Real-Time Activity Feed
                            </h2>
                        </div>
                        <div className="flex-1 overflow-hidden">
                            <LiveMessageFeed messages={messages} maxMessages={200} />
                        </div>
                    </Card>
                )}

                {/* Learning Tab */}
                {activeTab === 'learning' && (
                    <ErrorBoundary>
                        <LearningDashboard />
                    </ErrorBoundary>
                )}
            </Shell>

            {/* Agent Detail Modal */}
            {selectedAgent && (
                <AgentDetailModal
                    agentName={selectedAgent}
                    onClose={() => setSelectedAgent(null)}
                />
            )}
        </>
    );
}
