'use client';

import { useEffect, useState } from 'react';
import { BarChart3, Bitcoin, TrendingUp, Activity, Filter } from 'lucide-react';

interface PerformanceData {
    timestamp: string;
    breakdown: {
        stocks: {
            total_value: number;
            total_trades: number;
            pending_trades: number;
        };
        crypto: {
            total_value: number;
            total_trades: number;
            pending_trades: number;
        };
    };
    agents: Array<{
        agent_name: string;
        stock: {
            value: number;
            trades_count: number;
        };
        crypto: {
            value: number;
            trades_count: number;
        };
        total_pnl: number;
        pnl_percent: number;
    }>;
}

type FilterType = 'all' | 'stocks' | 'crypto';

export default function StockCryptoSplit() {
    const [data, setData] = useState<PerformanceData | null>(null);
    const [loading, setLoading] = useState(true);
    const [filter, setFilter] = useState<FilterType>('all');

    useEffect(() => {
        fetchData();
        const interval = setInterval(fetchData, 10000); // Update every 10 seconds
        return () => clearInterval(interval);
    }, []);

    const fetchData = async () => {
        try {
            const res = await fetch('/api/performance/breakdown');
            if (!res.ok) throw new Error('Failed to fetch breakdown');
            const result = await res.json();
            if (!result || !result.breakdown) throw new Error('Invalid breakdown data');
            setData(result);
            setLoading(false);
        } catch (error) {
            console.error('Failed to fetch performance breakdown:', error);
            setLoading(false);
        }
    };

    if (loading || !data) {
        return (
            <div className="glass-panel rounded-3xl p-6 border border-surface-border">
                <div className="animate-pulse space-y-4">
                    <div className="h-8 bg-surface-active/50 rounded w-1/3"></div>
                    <div className="grid grid-cols-2 gap-4">
                        <div className="h-32 bg-surface-active/50 rounded"></div>
                        <div className="h-32 bg-surface-active/50 rounded"></div>
                    </div>
                </div>
            </div>
        );
    }

    const totalValue = data.breakdown.stocks.total_value + data.breakdown.crypto.total_value;
    const stockPercentage = totalValue > 0 ? (data.breakdown.stocks.total_value / totalValue) * 100 : 0;
    const cryptoPercentage = totalValue > 0 ? (data.breakdown.crypto.total_value / totalValue) * 100 : 0;

    const filteredAgents = data.agents.filter(agent => {
        if (filter === 'stocks') return agent.stock.trades_count > 0;
        if (filter === 'crypto') return agent.crypto.trades_count > 0;
        return true;
    });

    return (
        <div className="glass-panel rounded-3xl p-6 border border-surface-border shadow-2xl">
            {/* Header with Toggle Switch */}
            <div className="flex items-center justify-between mb-6">
                <div className="flex items-center gap-3">
                    <BarChart3 className="w-8 h-8 text-secondary" />
                    <h2 className="text-3xl font-bold text-white">Assets Breakdown</h2>
                </div>

                {/* Modern Toggle Switch */}
                <div className="flex items-center gap-3 bg-surface-active/50 backdrop-blur-sm rounded-full p-1 border border-surface-border">
                    <button
                        onClick={() => setFilter('stocks')}
                        className={`relative px-6 py-2 rounded-full font-semibold text-sm transition-all duration-300 ${filter === 'stocks'
                            ? 'bg-primary text-background shadow-neon-blue'
                            : 'text-gray-400 hover:text-white'
                            }`}
                    >
                        <span className="flex items-center gap-2">
                            <TrendingUp className="w-4 h-4" />
                            Stocks
                        </span>
                    </button>
                    <button
                        onClick={() => setFilter('all')}
                        className={`relative px-6 py-2 rounded-full font-semibold text-sm transition-all duration-300 ${filter === 'all'
                            ? 'bg-secondary text-white shadow-neon-purple'
                            : 'text-gray-400 hover:text-white'
                            }`}
                    >
                        Tous
                    </button>
                    <button
                        onClick={() => setFilter('crypto')}
                        className={`relative px-6 py-2 rounded-full font-semibold text-sm transition-all duration-300 ${filter === 'crypto'
                            ? 'bg-orange-500 text-white shadow-[0_0_15px_rgba(249,115,22,0.4)]'
                            : 'text-gray-400 hover:text-white'
                            }`}
                    >
                        <span className="flex items-center gap-2">
                            <Bitcoin className="w-4 h-4" />
                            Crypto
                        </span>
                    </button>
                </div>
            </div>

            {/* Overview Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
                {/* Stocks Card */}
                <div className="bg-gradient-to-br from-primary/5 to-primary/10 backdrop-blur-sm rounded-2xl p-6 border border-primary/20">
                    <div className="flex items-center gap-3 mb-4">
                        <TrendingUp className="w-8 h-8 text-primary" />
                        <div>
                            <h3 className="text-xl font-bold text-white">Stocks</h3>
                            <p className="text-xs text-primary/70">{stockPercentage.toFixed(1)}% du portfolio</p>
                        </div>
                    </div>
                    <div className="text-3xl font-bold text-white mb-2">
                        ${data.breakdown.stocks.total_value.toLocaleString('en-US', { maximumFractionDigits: 0 })}
                    </div>
                    <div className="grid grid-cols-2 gap-2 text-sm">
                        <div>
                            <div className="text-xs text-primary/70">Trades exécutés</div>
                            <div className="font-semibold text-white">{data.breakdown.stocks.total_trades}</div>
                        </div>
                        <div>
                            <div className="text-xs text-primary/70">En attente</div>
                            <div className="font-semibold text-white">{data.breakdown.stocks.pending_trades}</div>
                        </div>
                    </div>
                    {/* Progress bar for stocks */}
                    <div className="mt-4 w-full bg-surface-active rounded-full h-1.5 overflow-hidden">
                        <div
                            className="bg-primary h-full transition-all duration-500 shadow-[0_0_10px_#00E676]"
                            style={{ width: `${stockPercentage}%` }}
                        />
                    </div>
                </div>

                {/* Crypto Card */}
                <div className="bg-gradient-to-br from-orange-500/5 to-orange-600/10 backdrop-blur-sm rounded-2xl p-6 border border-orange-500/20">
                    <div className="flex items-center gap-3 mb-4">
                        <Bitcoin className="w-8 h-8 text-orange-500" />
                        <div>
                            <h3 className="text-xl font-bold text-white">Crypto</h3>
                            <p className="text-xs text-orange-500/70">{cryptoPercentage.toFixed(1)}% du portfolio</p>
                        </div>
                    </div>
                    <div className="text-3xl font-bold text-white mb-2">
                        ${data.breakdown.crypto.total_value.toLocaleString('en-US', { maximumFractionDigits: 0 })}
                    </div>
                    <div className="grid grid-cols-2 gap-2 text-sm">
                        <div>
                            <div className="text-xs text-orange-500/70">Trades exécutés</div>
                            <div className="font-semibold text-white">{data.breakdown.crypto.total_trades}</div>
                        </div>
                        <div>
                            <div className="text-xs text-orange-500/70">En attente</div>
                            <div className="font-semibold text-white">{data.breakdown.crypto.pending_trades}</div>
                        </div>
                    </div>
                    {/* Progress bar for crypto */}
                    <div className="mt-4 w-full bg-surface-active rounded-full h-1.5 overflow-hidden">
                        <div
                            className="bg-orange-500 h-full transition-all duration-500 shadow-[0_0_10px_#f97316]"
                            style={{ width: `${cryptoPercentage}%` }}
                        />
                    </div>
                </div>
            </div>

            {/* Agent Performance by Asset Type */}
            <div className="bg-surface/30 rounded-2xl p-4 border border-surface-border">
                <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                    <Activity className="w-5 h-5 text-primary" />
                    Performance par Agent {filter !== 'all' && `(${filter})`}
                </h3>
                <div className="space-y-2 max-h-[400px] overflow-y-auto custom-scrollbar">
                    {filteredAgents.length === 0 ? (
                        <div className="text-center py-8 text-gray-400">
                            Aucun agent ne correspond aux filtres sélectionnés
                        </div>
                    ) : (
                        filteredAgents.map(agent => {
                            const isProfitable = agent.pnl_percent >= 0;
                            return (
                                <div
                                    key={agent.agent_name}
                                    className="bg-surface rounded-lg p-3 hover:bg-surface-hover transition-all"
                                >
                                    <div className="flex items-center justify-between mb-2">
                                        <span className="font-semibold text-white">{agent.agent_name}</span>
                                        <span className={`text-sm font-bold ${isProfitable ? 'text-status-success' : 'text-status-error'}`}>
                                            {isProfitable ? '+' : ''}{agent.pnl_percent.toFixed(2)}%
                                        </span>
                                    </div>
                                    <div className="grid grid-cols-2 gap-3 text-xs">
                                        <div className="bg-primary/5 rounded p-2 border border-primary/20">
                                            <div className="text-primary/70 mb-1">📈 Stocks</div>
                                            <div className="font-semibold text-white">
                                                ${agent.stock.value.toLocaleString('en-US', { maximumFractionDigits: 0 })}
                                            </div>
                                            <div className="text-gray-400">{agent.stock.trades_count} trades</div>
                                        </div>
                                        <div className="bg-orange-500/5 rounded p-2 border border-orange-500/20">
                                            <div className="text-orange-500/70 mb-1">₿ Crypto</div>
                                            <div className="font-semibold text-white">
                                                ${agent.crypto.value.toLocaleString('en-US', { maximumFractionDigits: 0 })}
                                            </div>
                                            <div className="text-gray-400">{agent.crypto.trades_count} trades</div>
                                        </div>
                                    </div>
                                </div>
                            );
                        })
                    )}
                </div>
            </div>
        </div>
    );
}
