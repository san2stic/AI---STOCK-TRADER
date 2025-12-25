'use client';

import { useEffect, useState } from 'react';
import { Trophy, TrendingUp, TrendingDown, Medal, Star, Zap, Target } from 'lucide-react';

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
        // Only sort if we have valid agents data
        if (!agents || agents.length === 0) {
            setSortedAgents([]);
            return;
        }

        // Sort agents by selected metric with safety checks
        const sorted = [...agents].sort((a, b) => {
            const aValue = a?.[sortBy] ?? 0;
            const bValue = b?.[sortBy] ?? 0;
            return bValue - aValue;
        });
        setSortedAgents(sorted);
    }, [agents, sortBy]);

    // If no agents, show empty state
    if (!agents || agents.length === 0) {
        return (
            <div className="bg-white/5 backdrop-blur-xl rounded-3xl p-6 border border-white/20 shadow-2xl">
                <div className="flex items-center gap-3 mb-6">
                    <Trophy className="w-8 h-8 text-yellow-400" />
                    <h2 className="text-3xl font-bold text-white">Classement Live</h2>
                </div>
                <div className="text-center py-12 text-gray-400">
                    Aucun agent disponible pour le moment
                </div>
            </div>
        );
    }

    const getMedalIcon = (rank: number) => {
        switch (rank) {
            case 0:
                return <Trophy className="w-7 h-7 text-yellow-400 animate-pulse" />;
            case 1:
                return <Medal className="w-6 h-6 text-gray-300" />;
            case 2:
                return <Medal className="w-6 h-6 text-orange-400" />;
            default:
                return <Star className="w-5 h-5 text-gray-500" />;
        }
    };

    const getScoreColor = (rank: number) => {
        if (rank === 0) return 'from-yellow-500/30 to-orange-500/30 border-yellow-500/50';
        if (rank === 1) return 'from-gray-400/20 to-gray-500/20 border-gray-400/40';
        if (rank === 2) return 'from-orange-400/20 to-orange-500/20 border-orange-400/40';
        return 'from-white/5 to-white/10 border-white/10';
    };

    const getAgentPrimaryAsset = (agent: AgentScore): 'stock' | 'crypto' | 'mixed' => {
        const stockVal = agent.stock_value || 0;
        const cryptoVal = agent.crypto_value || 0;

        if (stockVal === 0 && cryptoVal === 0) return 'mixed';
        if (stockVal > cryptoVal * 2) return 'stock';
        if (cryptoVal > stockVal * 2) return 'crypto';
        return 'mixed';
    };

    const getAssetBadge = (type: 'stock' | 'crypto' | 'mixed') => {
        if (type === 'stock') {
            return <span className="text-xs bg-blue-500/20 text-blue-300 px-2 py-1 rounded-full border border-blue-500/30">📈 Stocks</span>;
        }
        if (type === 'crypto') {
            return <span className="text-xs bg-orange-500/20 text-orange-300 px-2 py-1 rounded-full border border-orange-500/30">₿ Crypto</span>;
        }
        return <span className="text-xs bg-purple-500/20 text-purple-300 px-2 py-1 rounded-full border border-purple-500/30">🔀 Mixte</span>;
    };

    return (
        <div className="bg-white/5 backdrop-blur-xl rounded-3xl p-6 border border-white/20 shadow-2xl">
            {/* Header */}
            <div className="flex items-center justify-between mb-6">
                <div className="flex items-center gap-3">
                    <Trophy className="w-8 h-8 text-yellow-400" />
                    <h2 className="text-3xl font-bold text-white">Classement Live</h2>
                </div>
                <div className="flex items-center gap-1 bg-green-500/20 px-3 py-1 rounded-full border border-green-500/30">
                    <Zap className="w-4 h-4 text-green-400 animate-pulse" />
                    <span className="text-xs text-green-300 font-semibold">LIVE</span>
                </div>
            </div>

            {/* Sort Buttons */}
            <div className="flex gap-2 mb-6 overflow-x-auto pb-2">
                <button
                    onClick={() => setSortBy('pnl_percent')}
                    className={`flex items-center gap-2 px-4 py-2 rounded-lg font-semibold text-sm whitespace-nowrap transition-all ${sortBy === 'pnl_percent'
                        ? 'bg-gradient-to-r from-cyan-500 to-blue-600 text-white shadow-lg'
                        : 'bg-white/10 text-gray-300 hover:bg-white/15'
                        }`}
                >
                    <TrendingUp className="w-4 h-4" />
                    P&L %
                </button>
                <button
                    onClick={() => setSortBy('total_value')}
                    className={`flex items-center gap-2 px-4 py-2 rounded-lg font-semibold text-sm whitespace-nowrap transition-all ${sortBy === 'total_value'
                        ? 'bg-gradient-to-r from-cyan-500 to-blue-600 text-white shadow-lg'
                        : 'bg-white/10 text-gray-300 hover:bg-white/15'
                        }`}
                >
                    <Target className="w-4 h-4" />
                    Valeur Totale
                </button>
                <button
                    onClick={() => setSortBy('win_rate')}
                    className={`flex items-center gap-2 px-4 py-2 rounded-lg font-semibold text-sm whitespace-nowrap transition-all ${sortBy === 'win_rate'
                        ? 'bg-gradient-to-r from-cyan-500 to-blue-600 text-white shadow-lg'
                        : 'bg-white/10 text-gray-300 hover:bg-white/15'
                        }`}
                >
                    <Star className="w-4 h-4" />
                    Taux Victoires
                </button>
            </div>

            {/* Leaderboard */}
            <div className="space-y-3">
                {sortedAgents.map((agent, index) => {
                    const isProfitable = agent.pnl_percent >= 0;
                    const assetType = getAgentPrimaryAsset(agent);

                    return (
                        <div
                            key={agent.name}
                            className={`bg-gradient-to-r ${getScoreColor(index)} backdrop-blur-sm rounded-2xl p-4 border hover:scale-[1.02] transition-all duration-300`}
                        >
                            <div className="flex items-center gap-4">
                                {/* Rank */}
                                <div className="flex flex-col items-center min-w-[60px]">
                                    {getMedalIcon(index)}
                                    <span className="text-sm font-bold text-gray-300 mt-1">#{index + 1}</span>
                                </div>

                                {/* Agent Info */}
                                <div className="flex-1">
                                    <div className="flex items-center gap-2 mb-2">
                                        <h3 className="text-lg font-bold text-white">{agent.name}</h3>
                                        {getAssetBadge(assetType)}
                                    </div>

                                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
                                        <div>
                                            <div className="text-xs text-gray-400">Valeur</div>
                                            <div className="font-semibold text-white">
                                                ${agent.total_value.toLocaleString('en-US', { maximumFractionDigits: 0 })}
                                            </div>
                                        </div>
                                        <div>
                                            <div className="text-xs text-gray-400">P&L</div>
                                            <div className={`font-semibold ${isProfitable ? 'text-green-400' : 'text-red-400'}`}>
                                                {isProfitable ? '+' : ''}{agent.pnl_percent.toFixed(2)}%
                                            </div>
                                        </div>
                                        <div>
                                            <div className="text-xs text-gray-400">Trades</div>
                                            <div className="font-semibold text-white">{agent.total_trades}</div>
                                        </div>
                                        <div>
                                            <div className="text-xs text-gray-400">Win Rate</div>
                                            <div className={`font-semibold ${agent.win_rate >= 60 ? 'text-green-400' :
                                                agent.win_rate >= 40 ? 'text-yellow-400' : 'text-red-400'
                                                }`}>
                                                {agent.win_rate.toFixed(1)}%
                                            </div>
                                        </div>
                                    </div>
                                </div>

                                {/* Performance Indicator */}
                                <div className="hidden lg:flex flex-col items-center min-w-[80px]">
                                    {isProfitable ? (
                                        <TrendingUp className="w-8 h-8 text-green-400 mb-1" />
                                    ) : (
                                        <TrendingDown className="w-8 h-8 text-red-400 mb-1" />
                                    )}
                                    <div className={`text-xl font-bold ${isProfitable ? 'text-green-400' : 'text-red-400'}`}>
                                        {isProfitable ? '+' : ''}{agent.pnl.toFixed(0)}$
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
