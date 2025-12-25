'use client';

import { useEffect, useState } from 'react';
import { DollarSign, TrendingUp, TrendingDown, Wallet, PieChart, Zap } from 'lucide-react';

interface FundsData {
    timestamp: string;
    totals: {
        cash: number;
        total_value: number;
        stock_value: number;
        crypto_value: number;
        pnl: number;
        pnl_percent: number;
        positions_count: number;
        initial_capital: number;
    };
}

export default function RealTimeFunds() {
    const [funds, setFunds] = useState<FundsData | null>(null);
    const [loading, setLoading] = useState(true);
    const [isPulsing, setIsPulsing] = useState(false);

    useEffect(() => {
        fetchFunds();
        const interval = setInterval(fetchFunds, 5000); // Update every 5 seconds
        return () => clearInterval(interval);
    }, []);

    const fetchFunds = async () => {
        try {
            const res = await fetch('/api/funds/realtime');
            if (!res.ok) throw new Error('Failed to fetch funds');
            const data = await res.json();
            if (!data || !data.totals) throw new Error('Invalid funds data');
            setFunds(data);
            setLoading(false);

            // Trigger pulse animation on update
            setIsPulsing(true);
            setTimeout(() => setIsPulsing(false), 1000);
        } catch (error) {
            console.error('Failed to fetch funds:', error);
            setLoading(false);
        }
    };

    if (loading || !funds) {
        return (
            <div className="bg-gradient-to-br from-indigo-600/20 to-purple-600/20 backdrop-blur-xl rounded-3xl p-6 border border-white/20 shadow-2xl">
                <div className="animate-pulse flex items-center gap-4">
                    <div className="h-12 w-12 bg-white/20 rounded-full"></div>
                    <div className="flex-1">
                        <div className="h-6 bg-white/20 rounded w-1/3 mb-2"></div>
                        <div className="h-8 bg-white/20 rounded w-1/2"></div>
                    </div>
                </div>
            </div>
        );
    }

    const isProfitable = funds?.totals?.pnl ? funds.totals.pnl >= 0 : false;
    const stockPercentage = funds.totals.total_value > 0
        ? (funds.totals.stock_value / funds.totals.total_value) * 100
        : 0;
    const cryptoPercentage = funds.totals.total_value > 0
        ? (funds.totals.crypto_value / funds.totals.total_value) * 100
        : 0;

    return (
        <div className={`bg-gradient-to-br from-indigo-600/20 to-purple-600/20 backdrop-blur-xl rounded-3xl p-8 border border-white/30 shadow-2xl transition-all duration-300 ${isPulsing ? 'scale-[1.01] shadow-cyan-500/50' : ''}`}>
            {/* Header with Live Indicator */}
            <div className="flex items-center justify-between mb-6">
                <div className="flex items-center gap-3">
                    <div className="relative">
                        <Wallet className="w-10 h-10 text-cyan-400" />
                        <div className="absolute -top-1 -right-1 w-3 h-3 bg-green-500 rounded-full animate-pulse"></div>
                    </div>
                    <div>
                        <h2 className="text-2xl font-bold text-white">Fonds en Temps Réel</h2>
                        <p className="text-xs text-gray-300 flex items-center gap-1">
                            <Zap className="w-3 h-3 text-yellow-400" />
                            Mise à jour live
                        </p>
                    </div>
                </div>
            </div>

            {/* Main Value Display */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
                {/* Total Value */}
                <div className="bg-white/10 backdrop-blur-sm rounded-2xl p-6 border border-white/20 hover:border-cyan-400/50 transition-all">
                    <div className="flex items-center gap-2 mb-2">
                        <DollarSign className="w-5 h-5 text-cyan-400" />
                        <span className="text-sm text-gray-300">Valeur Totale</span>
                    </div>
                    <div className="text-4xl font-bold text-white">
                        ${funds.totals.total_value.toLocaleString('en-US', { maximumFractionDigits: 2 })}
                    </div>
                </div>

                {/* P&L */}
                <div className={`bg-gradient-to-br ${isProfitable ? 'from-green-500/20 to-emerald-500/20 border-green-500/30' : 'from-red-500/20 to-rose-500/20 border-red-500/30'} backdrop-blur-sm rounded-2xl p-6 border hover:scale-[1.02] transition-all`}>
                    <div className="flex items-center gap-2 mb-2">
                        {isProfitable ? (
                            <TrendingUp className="w-5 h-5 text-green-400" />
                        ) : (
                            <TrendingDown className="w-5 h-5 text-red-400" />
                        )}
                        <span className="text-sm text-gray-300">Profit & Loss</span>
                    </div>
                    <div className={`text-4xl font-bold ${isProfitable ? 'text-green-400' : 'text-red-400'}`}>
                        {isProfitable ? '+' : ''}
                        {funds.totals.pnl_percent.toFixed(2)}%
                    </div>
                </div>

                {/* Cash Available */}
                <div className="bg-white/10 backdrop-blur-sm rounded-2xl p-6 border border-white/20 hover:border-purple-400/50 transition-all">
                    <div className="flex items-center gap-2 mb-2">
                        <Wallet className="w-5 h-5 text-purple-400" />
                        <span className="text-sm text-gray-300">Cash Disponible</span>
                    </div>
                    <div className="text-4xl font-bold text-white mb-2">
                        ${funds.totals.cash.toLocaleString('en-US', { maximumFractionDigits: 2 })}
                    </div>
                    <div className="text-xs text-gray-400">
                        {funds.totals.positions_count} positions ouvertes
                    </div>
                </div>
            </div>

            {/* Stock vs Crypto Breakdown */}
            <div className="bg-white/5 backdrop-blur-sm rounded-2xl p-6 border border-white/10">
                <div className="flex items-center gap-2 mb-4">
                    <PieChart className="w-5 h-5 text-pink-400" />
                    <h3 className="text-lg font-semibold text-white">Répartition Stocks / Crypto</h3>
                </div>

                {/* Progress Bar */}
                <div className="mb-4">
                    <div className="w-full bg-gray-700 rounded-full h-4 overflow-hidden flex">
                        <div
                            className="bg-gradient-to-r from-blue-500 to-cyan-400 h-full flex items-center justify-center transition-all duration-500"
                            style={{ width: `${stockPercentage}%` }}
                        >
                            {stockPercentage > 10 && (
                                <span className="text-xs font-semibold text-white">
                                    {stockPercentage.toFixed(0)}%
                                </span>
                            )}
                        </div>
                        <div
                            className="bg-gradient-to-r from-orange-500 to-pink-400 h-full flex items-center justify-center transition-all duration-500"
                            style={{ width: `${cryptoPercentage}%` }}
                        >
                            {cryptoPercentage > 10 && (
                                <span className="text-xs font-semibold text-white">
                                    {cryptoPercentage.toFixed(0)}%
                                </span>
                            )}
                        </div>
                    </div>
                </div>

                {/* Values */}
                <div className="grid grid-cols-2 gap-4">
                    <div className="bg-blue-500/10 rounded-lg p-4 border border-blue-500/30">
                        <div className="text-sm text-blue-300 mb-1">📈 Stocks</div>
                        <div className="text-2xl font-bold text-white">
                            ${funds.totals.stock_value.toLocaleString('en-US', { maximumFractionDigits: 0 })}
                        </div>
                        <div className="text-xs text-gray-400 mt-1">
                            {stockPercentage.toFixed(1)}% du portfolio
                        </div>
                    </div>
                    <div className="bg-orange-500/10 rounded-lg p-4 border border-orange-500/30">
                        <div className="text-sm text-orange-300 mb-1">₿ Crypto</div>
                        <div className="text-2xl font-bold text-white">
                            ${funds.totals.crypto_value.toLocaleString('en-US', { maximumFractionDigits: 0 })}
                        </div>
                        <div className="text-xs text-gray-400 mt-1">
                            {cryptoPercentage.toFixed(1)}% du portfolio
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
