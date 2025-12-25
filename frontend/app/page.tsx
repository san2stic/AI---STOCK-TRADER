'use client';

import { useState, useEffect } from 'react';
import { Activity } from 'lucide-react';
import Shell from './components/layout/Shell';
import AgentCard from './components/AgentCard';
import LiveMessageFeed from './components/LiveMessageFeed';
import PerformanceCharts from './components/PerformanceCharts';
import CrewDashboard from './components/CrewDashboard';
import RealTimeFunds from './components/RealTimeFunds';
import LiveScoreBoard from './components/LiveScoreBoard';
import StockCryptoSplit from './components/StockCryptoSplit';
import EconomicCalendar from './components/EconomicCalendar';
import EconomicCalendarAnalysis from './components/EconomicCalendarAnalysis';
import ErrorBoundary from './components/ErrorBoundary';
import ModelDisplay from './components/ModelDisplay';
import LearningDashboard from './components/LearningDashboard';
import AgentDetailModal from './components/AgentDetailModal';
import useApi from './hooks/useApi';

interface Agent {
    name: string;
    total_value: number;
    pnl: number;
    pnl_percent: number;
    total_trades: number;
    win_rate: number;
    cash: number;
    positions_count: number;
    stock_value?: number;
    crypto_value?: number;
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
    const [messages, setMessages] = useState<Message[]>([]);
    const [wsStatus, setWsStatus] = useState<'connecting' | 'connected' | 'disconnected'>('connecting');
    const [ws, setWs] = useState<WebSocket | null>(null);
    const [selectedAgent, setSelectedAgent] = useState<string | null>(null);
    const [isPaused, setIsPaused] = useState(false);

    // Use useApi handling
    const {
        data: agentsData,
        loading: agentsLoading,
        refetch: refetchAgents
    } = useApi<{ agents: Agent[] }>('/api/agents', {
        autoFetch: true,
        cacheDuration: 1000
    });

    const {
        data: modelsData
    } = useApi<{ agents: Record<string, any> }>('/api/models/current', {
        autoFetch: true
    });

    const agents = agentsData?.agents || [];
    const agentModels = modelsData?.agents || {};

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

    // WebSocket logic kept here for real-time updates
    useEffect(() => {
        const connectWebSocket = () => {
            let wsUrl;
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
                    setMessages(prev => [message, ...prev].slice(0, 200));

                    // Refresh agents on important events
                    if (['trade', 'decision', 'agent_decision'].includes(data.type)) {
                        refetchAgents();
                    }
                } catch (error) {
                    console.error('Failed to parse WebSocket message:', error);
                }
            };

            websocket.onerror = (error) => {
                console.error('WebSocket error:', error);
                setWsStatus('disconnected');
            };

            websocket.onclose = () => {
                console.log('WebSocket disconnected, reconnecting...');
                setWsStatus('disconnected');
                setTimeout(connectWebSocket, 3000);
            };

            setWs(websocket);
        };

        connectWebSocket();

        return () => {
            if (ws) {
                ws.close();
            }
        };
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []); // Empty dependency array as we want this to run once

    if (agentsLoading && agents.length === 0) {
        return (
            <div className="min-h-screen bg-background flex items-center justify-center">
                <div className="text-center">
                    <div className="animate-spin rounded-full h-16 w-16 border-b-4 border-primary mx-auto mb-4"></div>
                    <div className="text-white text-2xl font-semibold animate-pulse">Chargement AI System...</div>
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
                {/* Real-Time Funds Display */}
                <div className="mb-8">
                    <RealTimeFunds />
                </div>

                {/* Tab Content */}
                <div className="animate-fade-in-up">
                    {activeTab === 'overview' && (
                        <div className="space-y-8">
                            {/* Live ScoreBoard */}
                            <LiveScoreBoard agents={agents} />

                            {/* Stock/Crypto Split */}
                            <StockCryptoSplit />

                            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                                {/* Economic Calendar */}
                                <EconomicCalendar daysAhead={7} minImpact="MEDIUM" />

                                {/* AI Economic Calendar Analysis */}
                                <EconomicCalendarAnalysis daysAhead={7} />
                            </div>

                            {/* AI Models Display */}
                            <ModelDisplay />

                            {/* Agent Cards Grid */}
                            <div>
                                <h2 className="text-2xl font-bold text-white mb-6 flex items-center gap-2">
                                    <span className="w-1 h-8 bg-primary rounded-full" />
                                    Détails par Agent
                                </h2>
                                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                                    {agents.map(agent => {
                                        // Find matching model info
                                        const modelInfo = Object.values(agentModels).find(
                                            (m: any) => m.name === agent.name
                                        ) as any;

                                        return (
                                            <AgentCard
                                                key={agent.name}
                                                agent={{
                                                    ...agent,
                                                    model: modelInfo?.model,
                                                    model_category: modelInfo?.category,
                                                }}
                                                onClick={() => setSelectedAgent(agent.name)}
                                            />
                                        );
                                    })}
                                </div>
                            </div>

                            {/* Quick Stats */}
                            <div className="glass-card p-8">
                                <h2 className="text-2xl font-bold mb-6 text-glow">Statistiques Rapides</h2>
                                <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
                                    <div className="text-center group hover:scale-105 transition-transform">
                                        <div className="text-4xl font-bold text-primary mb-2 group-hover:text-primary-glow transition-colors">
                                            {agents.length}
                                        </div>
                                        <div className="text-sm text-gray-400 uppercase tracking-wider">Agents Actifs</div>
                                    </div>
                                    <div className="text-center group hover:scale-105 transition-transform">
                                        <div className="text-4xl font-bold text-success mb-2 group-hover:text-success-glow transition-colors">
                                            {agents.reduce((sum, a) => sum + a.total_trades, 0)}
                                        </div>
                                        <div className="text-sm text-gray-400 uppercase tracking-wider">Trades Totaux</div>
                                    </div>
                                    <div className="text-center group hover:scale-105 transition-transform">
                                        <div className="text-4xl font-bold text-accent mb-2">
                                            {agents.length > 0 ? (agents.reduce((sum, a) => sum + (a.win_rate || 0), 0) / agents.length).toFixed(1) : '0.0'}%
                                        </div>
                                        <div className="text-sm text-gray-400 uppercase tracking-wider">Taux Moyen</div>
                                    </div>
                                    <div className="text-center group hover:scale-105 transition-transform">
                                        <div className="text-4xl font-bold text-accent-pink mb-2">
                                            ${agents.reduce((sum, a) => sum + a.total_value, 0).toFixed(0)}
                                        </div>
                                        <div className="text-sm text-gray-400 uppercase tracking-wider">Valeur Totale</div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    )}

                    {activeTab === 'charts' && (
                        <ErrorBoundary>
                            <PerformanceCharts agents={agents} />
                        </ErrorBoundary>
                    )}

                    {activeTab === 'learning' && (
                        <ErrorBoundary>
                            <LearningDashboard />
                        </ErrorBoundary>
                    )}

                    {activeTab === 'crew' && (
                        <ErrorBoundary>
                            <CrewDashboard />
                        </ErrorBoundary>
                    )}

                    {activeTab === 'live' && (
                        <div className="glass-card p-6 min-h-[600px]">
                            <h2 className="text-3xl font-bold mb-6 flex items-center gap-3">
                                <Activity className="text-primary animate-pulse" />
                                Messages en Temps Réel
                            </h2>
                            <LiveMessageFeed messages={messages} maxMessages={100} />
                        </div>
                    )}
                </div>
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
