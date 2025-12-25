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
            const result = await res.json();
            setData(result);
            setLoading(false);
        } catch (error) {
            console.error('Failed to fetch performance breakdown:', error);
            setLoading(false);
        }
    };

    if (loading || !data) {
        return (
            <div className="bg-white/5 backdrop-blur-xl rounded-3xl p-6 border border-white/20">
                <div className="animate-pulse space-y-4">
                    <div className="h-8 bg-white/10 rounded w-1/3"></div>
                    <div className="grid grid-cols-2 gap-4">
                        <div className="h-32 bg-white/10 rounded"></div>
                        <div className="h-32 bg-white/10 rounded"></div>
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
        <div className="bg-white/5 backdrop-blur-xl rounded-3xl p-6 border border-white/20 shadow-2xl">
            {/* Header with Toggle Switch */}
            <div className="flex items-center justify-between mb-6">
                <div className="flex items-center gap-3">
                    <BarChart3 className="w-8 h-8 text-purple-400" />
                    <h2 className="text-3xl font-bold text-white">Stocks vs Crypto</h2>
                </div>

                {/* Modern Toggle Switch */}
                <div className="flex items-center gap-3 bg-white/5 backdrop-blur-sm rounded-full p-1 border border-white/10">
                    <button
                        onClick={() => setFilter('stocks')}
                        className={`relative px-6 py-2 rounded-full font-semibold text-sm transition-all duration-300 ${filter === 'stocks'
                                ? 'bg-gradient-to-r from-blue-500 to-cyan-600 text-white shadow-lg shadow-blue-500/50'
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
                                ? 'bg-gradient-to-r from-purple-500 to-pink-600 text-white shadow-lg shadow-purple-500/50'
                                : 'text-gray-400 hover:text-white'
                            }`}
                    >
                        Tous
                    </button>
                    <button
                        onClick={() => setFilter('crypto')}
                        className={`relative px-6 py-2 rounded-full font-semibold text-sm transition-all duration-300 ${filter === 'crypto'
                                ? 'bg-gradient-to-r from-orange-500 to-pink-600 text-white shadow-lg shadow-orange-500/50'
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
                <div className="bg-gradient-to-br from-blue-500/20 to-cyan-500/20 backdrop-blur-sm rounded-2xl p-6 border border-blue-500/30">
                    <div className="flex items-center gap-3 mb-4">
                        <TrendingUp className="w-8 h-8 text-blue-400" />
                        <div>
                            <h3 className="text-xl font-bold text-white">Stocks</h3>
                            <p className="text-xs text-blue-300">{stockPercentage.toFixed(1)}% du portfolio</p>
                        </div>
                    </div>
                    <div className="text-3xl font-bold text-white mb-2">
                        ${data.breakdown.stocks.total_value.toLocaleString('en-US', { maximumFractionDigits: 0 })}
                    </div>
                    <div className="grid grid-cols-2 gap-2 text-sm">
                        <div>
                            <div className="text-xs text-blue-300">Trades exécutés</div>
                            <div className="font-semibold text-white">{data.breakdown.stocks.total_trades}</div>
                        </div>
                        <div>
                            <div className="text-xs text-blue-300">En attente</div>
                            <div className="font-semibold text-white">{data.breakdown.stocks.pending_trades}</div>
                        </div>
                    </div>
                    {/* Progress bar for stocks */}
                    <div className="mt-4 w-full bg-blue-900/30 rounded-full h-2 overflow-hidden">
                        <div
                            className="bg-gradient-to-r from-blue-500 to-cyan-400 h-full transition-all duration-500"
                            style={{ width: `${stockPercentage}%` }}
                        />
                    </div>
                </div>

                {/* Crypto Card */}
                <div className="bg-gradient-to-br from-orange-500/20 to-pink-500/20 backdrop-blur-sm rounded-2xl p-6 border border-orange-500/30">
                    <div className="flex items-center gap-3 mb-4">
                        <Bitcoin className="w-8 h-8 text-orange-400" />
                        <div>
                            <h3 className="text-xl font-bold text-white">Crypto</h3>
                            <p className="text-xs text-orange-300">{cryptoPercentage.toFixed(1)}% du portfolio</p>
                        </div>
                    </div>
                    <div className="text-3xl font-bold text-white mb-2">
                        ${data.breakdown.crypto.total_value.toLocaleString('en-US', { maximumFractionDigits: 0 })}
                    </div>
                    <div className="grid grid-cols-2 gap-2 text-sm">
                        <div>
                            <div className="text-xs text-orange-300">Trades exécutés</div>
                            <div className="font-semibold text-white">{data.breakdown.crypto.total_trades}</div>
                        </div>
                        <div>
                            <div className="text-xs text-orange-300">En attente</div>
                            <div className="font-semibold text-white">{data.breakdown.crypto.pending_trades}</div>
                        </div>
                    </div>
                    {/* Progress bar for crypto */}
                    <div className="mt-4 w-full bg-orange-900/30 rounded-full h-2 overflow-hidden">
                        <div
                            className="bg-gradient-to-r from-orange-500 to-pink-400 h-full transition-all duration-500"
                            style={{ width: `${cryptoPercentage}%` }}
                        />
                    </div>
                </div>
            </div>

            {/* Agent Performance by Asset Type */}
            <div className="bg-white/5 rounded-2xl p-4 border border-white/10">
                <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                    <Activity className="w-5 h-5 text-cyan-400" />
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
                                    className="bg-white/5 rounded-lg p-3 hover:bg-white/10 transition-all"
                                >
                                    <div className="flex items-center justify-between mb-2">
                                        <span className="font-semibold text-white">{agent.agent_name}</span>
                                        <span className={`text-sm font-bold ${isProfitable ? 'text-green-400' : 'text-red-400'}`}>
                                            {isProfitable ? '+' : ''}{agent.pnl_percent.toFixed(2)}%
                                        </span>
                                    </div>
                                    <div className="grid grid-cols-2 gap-3 text-xs">
                                        <div className="bg-blue-500/10 rounded p-2 border border-blue-500/20">
                                            <div className="text-blue-300 mb-1">📈 Stocks</div>
                                            <div className="font-semibold text-white">
                                                ${agent.stock.value.toLocaleString('en-US', { maximumFractionDigits: 0 })}
                                            </div>
                                            <div className="text-gray-400">{agent.stock.trades_count} trades</div>
                                        </div>
                                        <div className="bg-orange-500/10 rounded p-2 border border-orange-500/20">
                                            <div className="text-orange-300 mb-1">₿ Crypto</div>
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
