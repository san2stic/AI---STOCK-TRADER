'use client';

import { TrendingUp, TrendingDown, Activity, DollarSign, Brain, Trophy } from 'lucide-react';
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

    // Simulate sparkline data based on performance
    // In a real scenario, this would come from the API history
    const sparklineData = Array.from({ length: 20 }, (_, i) => ({
        value: 100 + (Math.random() * 10 - 5) + (isProfitable ? i * 0.5 : -i * 0.5)
    }));

    return (
        <div
            onClick={onClick}
            className="group relative bg-[#13131f] border border-white/5 rounded-2xl overflow-hidden cursor-pointer transition-all duration-300 hover:border-primary/50 hover:shadow-[0_0_30px_rgba(0,242,254,0.1)] hover:-translate-y-1"
        >
            {/* Background Gradient Effect */}
            <div className="absolute inset-0 bg-gradient-to-br from-white/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300" />

            <div className="relative p-6 z-10">
                {/* Header */}
                <div className="flex items-start justify-between mb-6">
                    <div>
                        <div className="flex items-center gap-2 mb-1">
                            <h3 className="text-xl font-bold text-white group-hover:text-primary transition-colors">
                                {agent.name}
                            </h3>
                            {agent.total_trades > 0 && (
                                <span className="relative flex h-2 w-2">
                                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-success opacity-75"></span>
                                    <span className="relative inline-flex rounded-full h-2 w-2 bg-success"></span>
                                </span>
                            )}
                        </div>

                        <div className="flex items-center gap-2">
                            {agent.model && (
                                <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-md bg-white/5 border border-white/10 text-xs text-gray-400">
                                    <Brain className="w-3 h-3 text-accent" />
                                    {agent.model.split('/').pop()}
                                </div>
                            )}
                        </div>
                    </div>

                    <div className={`p-2 rounded-xl bg-white/5 border border-white/10 ${isProfitable ? 'text-success' : 'text-danger'}`}>
                        {isProfitable ? <TrendingUp className="w-6 h-6" /> : <TrendingDown className="w-6 h-6" />}
                    </div>
                </div>

                {/* Main Stats with Sparkline Background */}
                <div className="relative mb-6">
                    <div className="mb-1 text-sm text-gray-400">P&L Total</div>
                    <div className="flex items-baseline gap-2">
                        <span className={`text-3xl font-bold tracking-tight ${isProfitable ? 'text-success text-shadow-success' : 'text-danger'}`}>
                            {isProfitable ? '+' : ''}{agent.pnl_percent.toFixed(2)}%
                        </span>
                        <span className={`text-sm font-medium ${isProfitable ? 'text-success' : 'text-danger'}`}>
                            (${agent.pnl?.toFixed(2)})
                        </span>
                    </div>

                    {/* Sparkline Overlay */}
                    <div className="absolute top-0 right-0 w-24 h-16 opacity-30 group-hover:opacity-50 transition-opacity">
                        <ResponsiveContainer width="100%" height="100%">
                            <AreaChart data={sparklineData}>
                                <defs>
                                    <linearGradient id={`gradient-${agent.name}`} x1="0" y1="0" x2="0" y2="1">
                                        <stop offset="5%" stopColor={isProfitable ? '#00e676' : '#ff5252'} stopOpacity={0.8} />
                                        <stop offset="95%" stopColor={isProfitable ? '#00e676' : '#ff5252'} stopOpacity={0} />
                                    </linearGradient>
                                </defs>
                                <Area
                                    type="monotone"
                                    dataKey="value"
                                    stroke={isProfitable ? '#00e676' : '#ff5252'}
                                    fill={`url(#gradient-${agent.name})`}
                                    strokeWidth={2}
                                />
                            </AreaChart>
                        </ResponsiveContainer>
                    </div>
                </div>

                {/* Metrics Grid */}
                <div className="grid grid-cols-2 gap-4 mb-4">
                    <div className="bg-white/5 rounded-xl p-3 border border-white/5 group-hover:border-white/10 transition-colors">
                        <div className="flex items-center gap-2 text-xs text-gray-400 mb-1">
                            <DollarSign className="w-3.5 h-3.5" />
                            Valeur
                        </div>
                        <div className="text-lg font-semibold text-white">
                            ${agent.total_value.toFixed(0)}
                        </div>
                    </div>
                    <div className="bg-white/5 rounded-xl p-3 border border-white/5 group-hover:border-white/10 transition-colors">
                        <div className="flex items-center gap-2 text-xs text-gray-400 mb-1">
                            <Trophy className="w-3.5 h-3.5" />
                            Win Rate
                        </div>
                        <div className={`text-lg font-semibold ${agent.win_rate >= 60 ? 'text-warning' : 'text-white'
                            }`}>
                            {agent.win_rate.toFixed(1)}%
                        </div>
                    </div>
                </div>

                {/* Footer Stats */}
                <div className="flex items-center justify-between text-xs text-gray-500 pt-4 border-t border-white/5">
                    <div className="flex items-center gap-4">
                        <span>Trades: <span className="text-gray-300">{agent.total_trades}</span></span>
                        <span>Cash: <span className="text-gray-300">${agent.cash.toFixed(0)}</span></span>
                    </div>
                    <div className="opacity-0 group-hover:opacity-100 transition-opacity text-primary font-medium flex items-center gap-1">
                        Détails <span className="text-lg leading-none">→</span>
                    </div>
                </div>
            </div>
        </div>
    );
}
