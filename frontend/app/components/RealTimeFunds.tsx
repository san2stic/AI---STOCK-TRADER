'use client';

import { useEffect, useState } from 'react';
import { DollarSign, TrendingUp, TrendingDown, Wallet, PieChart, Activity } from 'lucide-react';

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
            <div className="glass-panel p-8 rounded-3xl animate-pulse">
                <div className="h-20 bg-surface-active/50 rounded-xl mb-4" />
                <div className="grid grid-cols-3 gap-4">
                    <div className="h-32 bg-surface-active/50 rounded-xl" />
                    <div className="h-32 bg-surface-active/50 rounded-xl" />
                    <div className="h-32 bg-surface-active/50 rounded-xl" />
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
        <div className={`
            glass-panel rounded-3xl p-8 relative overflow-hidden transition-all duration-500
            ${isPulsing ? 'shadow-[0_0_40px_rgba(0,240,255,0.1)]' : ''}
        `}>
            {/* Background Glow */}
            <div className={`absolute top-0 right-0 w-[400px] h-[400px] bg-gradient-to-br from-primary/10 to-transparent blur-[80px] rounded-full pointer-events-none transition-opacity ${isPulsing ? 'opacity-50' : 'opacity-20'}`} />

            <div className="relative z-10">
                <div className="flex items-center justify-between mb-8">
                    <div>
                        <h2 className="text-sm font-bold text-gray-400 uppercase tracking-widest mb-1 flex items-center gap-2">
                            <Activity className="w-4 h-4 text-primary animate-pulse" />
                            Portfolio Live
                        </h2>
                        <div className="flex items-baseline gap-4">
                            <div className="text-5xl lg:text-6xl font-display font-bold text-transparent bg-clip-text bg-gradient-to-r from-white to-gray-300 tracking-tight">
                                ${funds.totals.total_value.toLocaleString('en-US', { maximumFractionDigits: 2 })}
                            </div>
                            <div className={`text-xl font-bold flex items-center gap-1 ${isProfitable ? 'text-status-success' : 'text-status-error'}`}>
                                {isProfitable ? <TrendingUp className="w-5 h-5" /> : <TrendingDown className="w-5 h-5" />}
                                {isProfitable ? '+' : ''}{funds.totals.pnl_percent.toFixed(2)}%
                            </div>
                        </div>
                    </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    {/* Cash Card */}
                    <div className="bg-surface/50 rounded-2xl p-5 border border-surface-border group hover:border-primary/30 transition-colors">
                        <div className="flex items-center gap-2 text-gray-400 mb-2">
                            <Wallet className="w-5 h-5 text-primary" />
                            <span className="text-sm font-medium">Cash Disponible</span>
                        </div>
                        <div className="text-2xl font-bold text-white group-hover:text-primary transition-colors">
                            ${funds.totals.cash.toLocaleString('en-US', { maximumFractionDigits: 2 })}
                        </div>
                        <div className="text-xs text-gray-500 mt-1">Liquidité immédiate</div>
                    </div>

                    {/* Stock Card */}
                    <div className="bg-surface/50 rounded-2xl p-5 border border-surface-border group hover:border-blue-400/30 transition-colors">
                        <div className="flex items-center gap-2 text-gray-400 mb-2">
                            <PieChart className="w-5 h-5 text-blue-400" />
                            <span className="text-sm font-medium">Action Value</span>
                        </div>
                        <div className="text-2xl font-bold text-white group-hover:text-blue-400 transition-colors">
                            ${funds.totals.stock_value.toLocaleString('en-US', { maximumFractionDigits: 0 })}
                        </div>
                        <div className="w-full bg-gray-800 h-1.5 rounded-full mt-3 overflow-hidden">
                            <div className="bg-blue-400 h-full rounded-full transition-all duration-1000" style={{ width: `${stockPercentage}%` }} />
                        </div>
                    </div>

                    {/* Crypto Card */}
                    <div className="bg-surface/50 rounded-2xl p-5 border border-surface-border group hover:border-orange-400/30 transition-colors">
                        <div className="flex items-center gap-2 text-gray-400 mb-2">
                            <PieChart className="w-5 h-5 text-orange-400" />
                            <span className="text-sm font-medium">Crypto Value</span>
                        </div>
                        <div className="text-2xl font-bold text-white group-hover:text-orange-400 transition-colors">
                            ${funds.totals.crypto_value.toLocaleString('en-US', { maximumFractionDigits: 0 })}
                        </div>
                        <div className="w-full bg-gray-800 h-1.5 rounded-full mt-3 overflow-hidden">
                            <div className="bg-orange-400 h-full rounded-full transition-all duration-1000" style={{ width: `${cryptoPercentage}%` }} />
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
