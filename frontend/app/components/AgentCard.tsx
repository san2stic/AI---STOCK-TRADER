'use client';

import { TrendingUp, TrendingDown, DollarSign, Brain, Activity } from 'lucide-react';
import { AreaChart, Area, ResponsiveContainer } from 'recharts';

interface Agent {
    name: string;
    total_value: number;
    pnl: number;
    pnl_percent: number;
    cash: number;
    positions_count: number;
    total_trades: number;
    win_rate: number;
    stock_value?: number;
    crypto_value?: number;
    model?: string;
    model_category?: string;
}

interface AgentCardProps {
    agent: Agent;
    onClick?: () => void;
}

export default function AgentCard({ agent, onClick }: AgentCardProps) {
    const isProfitable = agent.pnl_percent >= 0;

    // Simulate sparkline data
    const sparklineData = Array.from({ length: 20 }, (_, i) => ({
        value: 100 + (Math.random() * 10 - 5) + (isProfitable ? i * 0.5 : -i * 0.5)
    }));

    return (
        <div
            onClick={onClick}
            className="group relative bg-surface border border-surface-border rounded-2xl overflow-hidden cursor-pointer transition-all duration-300 hover:border-primary/50 hover:shadow-neon-blue hover:-translate-y-1"
        >
            {/* Holographic Overlay Effect */}
            <div className="absolute inset-0 bg-gradient-to-br from-primary/5 via-transparent to-secondary/5 opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none" />

            <div className="relative p-5 z-10 flex flex-col h-full">
                {/* Header */}
                <div className="flex items-start justify-between mb-4">
                    <div>
                        <div className="flex items-center gap-2 mb-1">
                            {/* Status Dot */}
                            <span className={`flex h-2 w-2 rounded-full ${agent.total_trades > 0 ? 'bg-status-success shadow-[0_0_8px_#00e676]' : 'bg-gray-500'}`} />
                            <h3 className="text-lg font-bold text-white tracking-wide group-hover:text-primary transition-colors truncate max-w-[140px]">
                                {agent.name}
                            </h3>
                        </div>

                        {agent.model && (
                            <div className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-surface-active/50 border border-surface-border text-[10px] text-gray-400 font-mono tracking-tight">
                                <Brain className="w-3 h-3 text-secondary" />
                                {agent.model.split('/').pop()}
                            </div>
                        )}
                    </div>

                    <div className={`p-2 rounded-lg bg-surface-active/50 border border-surface-border ${isProfitable ? 'text-status-success' : 'text-status-error'}`}>
                        {isProfitable ? <TrendingUp className="w-5 h-5" /> : <TrendingDown className="w-5 h-5" />}
                    </div>
                </div>

                {/* Main Stats Area */}
                <div className="relative mb-6 flex-1">
                    <div className="text-xs text-gray-500 uppercase tracking-wider mb-1">Performance Globale</div>
                    <div className="flex items-baseline gap-2 z-10 relative">
                        <span className={`text-3xl font-bold tracking-tight ${isProfitable ? 'text-status-success drop-shadow-[0_0_8px_rgba(0,230,118,0.3)]' : 'text-status-error'}`}>
                            {isProfitable ? '+' : ''}{agent.pnl_percent.toFixed(2)}%
                        </span>
                    </div>
                    <div className={`text-sm font-medium ${isProfitable ? 'text-status-success/80' : 'text-status-error/80'}`}>
                        {isProfitable ? '+' : ''}${agent.pnl?.toFixed(2)}
                    </div>

                    {/* Background Chart */}
                    <div className="absolute top-[-10px] right-[-10px] w-32 h-24 opacity-20 group-hover:opacity-40 transition-opacity pointer-events-none">
                        <ResponsiveContainer width="100%" height="100%">
                            <AreaChart data={sparklineData}>
                                <defs>
                                    <linearGradient id={`gradient-${agent.name}`} x1="0" y1="0" x2="0" y2="1">
                                        <stop offset="5%" stopColor={isProfitable ? '#00E676' : '#FF1744'} stopOpacity={0.8} />
                                        <stop offset="95%" stopColor={isProfitable ? '#00E676' : '#FF1744'} stopOpacity={0} />
                                    </linearGradient>
                                </defs>
                                <Area
                                    type="monotone"
                                    dataKey="value"
                                    stroke={isProfitable ? '#00E676' : '#FF1744'}
                                    fill={`url(#gradient-${agent.name})`}
                                    strokeWidth={2}
                                />
                            </AreaChart>
                        </ResponsiveContainer>
                    </div>
                </div>

                {/* Metrics Grid */}
                <div className="grid grid-cols-2 gap-3 pt-4 border-t border-surface-border">
                    <div>
                        <div className="flex items-center gap-1.5 text-[10px] text-gray-500 uppercase mb-1">
                            <DollarSign className="w-3 h-3" />
                            Valeur
                        </div>
                        <div className="text-base font-semibold text-white tracking-wide">
                            ${agent.total_value.toFixed(0)}
                        </div>
                    </div>
                    <div>
                        <div className="flex items-center gap-1.5 text-[10px] text-gray-500 uppercase mb-1">
                            <Activity className="w-3 h-3" />
                            Win Rate
                        </div>
                        <div className={`text-base font-semibold ${agent.win_rate >= 60 ? 'text-status-success' :
                                agent.win_rate >= 40 ? 'text-status-warning' : 'text-gray-400'
                            }`}>
                            {agent.win_rate.toFixed(1)}%
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
