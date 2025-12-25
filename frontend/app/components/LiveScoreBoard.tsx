'use client';

import { useEffect, useState } from 'react';
import { Trophy, TrendingUp, TrendingDown, Medal, Star, Zap, Target, Award } from 'lucide-react';

interface AgentScore {
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

interface LiveScoreBoardProps {
    agents: AgentScore[];
}

export default function LiveScoreBoard({ agents }: LiveScoreBoardProps) {
    const [sortedAgents, setSortedAgents] = useState<AgentScore[]>([]);
    const [sortBy, setSortBy] = useState<'pnl_percent' | 'total_value' | 'win_rate'>('pnl_percent');

    useEffect(() => {
        if (!agents || agents.length === 0) {
            setSortedAgents([]);
            return;
        }

        const sorted = [...agents].sort((a, b) => {
            const aValue = a?.[sortBy] ?? 0;
            const bValue = b?.[sortBy] ?? 0;
            return bValue - aValue;
        });
        setSortedAgents(sorted);
    }, [agents, sortBy]);

    if (!agents || agents.length === 0) {
        return (
            <div className="glass-panel rounded-3xl p-8 flex flex-col items-center justify-center min-h-[300px]">
                <Trophy className="w-16 h-16 text-gray-600 mb-4" />
                <h2 className="text-xl font-bold text-gray-500">En attente de données live...</h2>
            </div>
        );
    }

    const getMedalIcon = (rank: number) => {
        switch (rank) {
            case 0: return <Trophy className="w-6 h-6 text-yellow-400 animate-pulse drop-shadow-[0_0_8px_rgba(250,204,21,0.5)]" />;
            case 1: return <Medal className="w-5 h-5 text-gray-300" />;
            case 2: return <Medal className="w-5 h-5 text-orange-400" />;
            default: return <span className="text-sm font-bold text-gray-500 font-mono">#{rank + 1}</span>;
        }
    };

    const getRowStyle = (rank: number) => {
        if (rank === 0) return 'bg-yellow-500/10 border-yellow-500/30 hover:bg-yellow-500/20';
        return 'bg-surface/30 border-surface-border hover:bg-surface/50';
    };

    return (
        <div className="glass-panel rounded-3xl p-6 lg:p-8">
            {/* Header */}
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 mb-8">
                <div>
                    <h2 className="text-2xl font-bold text-white flex items-center gap-3">
                        <Award className="w-8 h-8 text-secondary" />
                        Classement Alpha
                    </h2>
                    <p className="text-sm text-gray-400 mt-1">Performance en temps réel des agents</p>
                </div>

                {/* Sort Controls */}
                <div className="flex bg-surface-active rounded-xl p-1 border border-surface-border">
                    {[
                        { id: 'pnl_percent', label: 'P&L %', icon: TrendingUp },
                        { id: 'total_value', label: 'Valeur', icon: Target },
                        { id: 'win_rate', label: 'Win Rate', icon: Star },
                    ].map(btn => (
                        <button
                            key={btn.id}
                            onClick={() => setSortBy(btn.id as any)}
                            className={`
                                flex items-center gap-2 px-4 py-2 rounded-lg font-medium text-sm transition-all duration-300
                                ${sortBy === btn.id
                                    ? 'bg-primary/20 text-primary shadow-neon-blue'
                                    : 'text-gray-400 hover:text-white hover:bg-white/5'
                                }
                            `}
                        >
                            <btn.icon className="w-4 h-4" />
                            {btn.label}
                        </button>
                    ))}
                </div>
            </div>

            {/* List */}
            <div className="space-y-3">
                {sortedAgents.map((agent, index) => {
                    const isProfitable = agent.pnl_percent >= 0;
                    return (
                        <div
                            key={agent.name}
                            className={`
                                relative rounded-xl p-4 border transition-all duration-300 group
                                ${getRowStyle(index)}
                            `}
                        >
                            <div className="flex items-center gap-4 lg:gap-8">
                                {/* Rank */}
                                <div className="w-8 flex justify-center">
                                    {getMedalIcon(index)}
                                </div>

                                {/* Agent Main Info */}
                                <div className="flex-1 min-w-[150px]">
                                    <h3 className="text-base font-bold text-white group-hover:text-primary transition-colors">
                                        {agent.name}
                                    </h3>
                                    <div className="flex items-center gap-2 mt-1">
                                        <div className="w-20 h-1.5 bg-gray-700 rounded-full overflow-hidden">
                                            <div
                                                className={`h-full rounded-full ${agent.win_rate >= 50 ? 'bg-status-success' : 'bg-status-error'}`}
                                                style={{ width: `${agent.win_rate}%` }}
                                            />
                                        </div>
                                        <span className="text-xs text-gray-400">{agent.win_rate.toFixed(0)}% WR</span>
                                    </div>
                                </div>

                                {/* Metrics */}
                                <div className="grid grid-cols-2 md:grid-cols-3 gap-6 lg:gap-12 text-sm">
                                    <div className="hidden md:block">
                                        <div className="text-xs text-gray-500 uppercase">Trades</div>
                                        <div className="font-mono text-gray-300">{agent.total_trades}</div>
                                    </div>
                                    <div>
                                        <div className="text-xs text-gray-500 uppercase">Valeur</div>
                                        <div className="font-mono text-white">${agent.total_value.toFixed(0)}</div>
                                    </div>
                                    <div className="min-w-[80px] text-right">
                                        <div className="text-xs text-gray-500 uppercase">P&L</div>
                                        <div className={`font-bold font-mono ${isProfitable ? 'text-status-success' : 'text-status-error'}`}>
                                            {isProfitable ? '+' : ''}{agent.pnl_percent.toFixed(2)}%
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}
