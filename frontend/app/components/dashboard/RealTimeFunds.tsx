'use client';

import { useState, useEffect } from 'react';
import { DollarSign, TrendingUp, TrendingDown, Wallet, PieChart, RefreshCw } from 'lucide-react';
import Card from '../ui/Card';
import Badge from '../ui/Badge';

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
    data_source: string;
}

export default function RealTimeFunds() {
    const [data, setData] = useState<FundsData | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const fetchFunds = async () => {
        try {
            const res = await fetch('/api/funds/realtime');
            if (!res.ok) throw new Error('Failed to fetch funds');
            const json = await res.json();
            setData(json);
            setError(null);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Unknown error');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchFunds();
        const interval = setInterval(fetchFunds, 30000); // Refresh every 30s
        return () => clearInterval(interval);
    }, []);

    if (loading) {
        return (
            <Card className="animate-pulse">
                <div className="h-32 bg-surface-elevated rounded-lg" />
            </Card>
        );
    }

    if (error || !data) {
        return (
            <Card>
                <div className="text-center text-danger py-8">
                    <p>Failed to load funds data</p>
                    <button onClick={fetchFunds} className="mt-2 text-primary hover:underline">
                        Retry
                    </button>
                </div>
            </Card>
        );
    }

    const { totals } = data;
    const isPositive = totals.pnl >= 0;

    return (
        <Card variant="glow" padding="lg">
            <div className="flex items-center justify-between mb-6">
                <div className="flex items-center gap-3">
                    <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-primary to-secondary flex items-center justify-center">
                        <Wallet className="w-6 h-6 text-white" />
                    </div>
                    <div>
                        <h2 className="text-lg font-bold text-white">Portfolio Overview</h2>
                        <p className="text-xs text-gray-500">Real-time balance</p>
                    </div>
                </div>
                <Badge variant={data.data_source === 'live_api' ? 'success' : 'warning'} size="sm">
                    {data.data_source === 'live_api' ? 'LIVE' : 'CACHED'}
                </Badge>
            </div>

            {/* Main Stats */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
                {/* Total Value */}
                <div className="bg-surface-elevated/50 rounded-xl p-4">
                    <div className="flex items-center gap-2 text-gray-400 text-xs mb-2">
                        <DollarSign size={14} />
                        Total Value
                    </div>
                    <p className="text-2xl font-bold font-mono text-white">
                        ${totals.total_value.toLocaleString('en-US', { minimumFractionDigits: 2 })}
                    </p>
                </div>

                {/* P&L */}
                <div className="bg-surface-elevated/50 rounded-xl p-4">
                    <div className="flex items-center gap-2 text-gray-400 text-xs mb-2">
                        {isPositive ? <TrendingUp size={14} /> : <TrendingDown size={14} />}
                        Total P&L
                    </div>
                    <p className={`text-2xl font-bold font-mono ${isPositive ? 'text-success' : 'text-danger'}`}>
                        {isPositive ? '+' : ''}${totals.pnl.toLocaleString('en-US', { minimumFractionDigits: 2 })}
                    </p>
                    <p className={`text-sm ${isPositive ? 'text-success' : 'text-danger'}`}>
                        {isPositive ? '+' : ''}{totals.pnl_percent.toFixed(2)}%
                    </p>
                </div>

                {/* Cash */}
                <div className="bg-surface-elevated/50 rounded-xl p-4">
                    <div className="flex items-center gap-2 text-gray-400 text-xs mb-2">
                        <Wallet size={14} />
                        Cash Available
                    </div>
                    <p className="text-2xl font-bold font-mono text-white">
                        ${totals.cash.toLocaleString('en-US', { minimumFractionDigits: 2 })}
                    </p>
                </div>

                {/* Positions */}
                <div className="bg-surface-elevated/50 rounded-xl p-4">
                    <div className="flex items-center gap-2 text-gray-400 text-xs mb-2">
                        <PieChart size={14} />
                        Active Positions
                    </div>
                    <p className="text-2xl font-bold font-mono text-white">
                        {totals.positions_count}
                    </p>
                </div>
            </div>

            {/* Asset Allocation Bar */}
            <div className="space-y-2">
                <div className="flex items-center justify-between text-xs">
                    <span className="text-gray-400">Asset Allocation</span>
                    <div className="flex items-center gap-4">
                        <span className="flex items-center gap-1">
                            <span className="w-2 h-2 rounded-full bg-primary" />
                            Stocks ${totals.stock_value.toLocaleString()}
                        </span>
                        <span className="flex items-center gap-1">
                            <span className="w-2 h-2 rounded-full bg-secondary" />
                            Crypto ${totals.crypto_value.toLocaleString()}
                        </span>
                    </div>
                </div>
                <div className="h-2 bg-surface-border rounded-full overflow-hidden flex">
                    <div
                        className="bg-primary h-full transition-all duration-500"
                        style={{ width: `${(totals.stock_value / totals.total_value) * 100}%` }}
                    />
                    <div
                        className="bg-secondary h-full transition-all duration-500"
                        style={{ width: `${(totals.crypto_value / totals.total_value) * 100}%` }}
                    />
                </div>
            </div>

            {/* Refresh indicator */}
            <div className="flex items-center justify-end mt-4 text-xs text-gray-500">
                <RefreshCw size={12} className="mr-1" />
                Last updated: {new Date(data.timestamp).toLocaleTimeString()}
            </div>
        </Card>
    );
}
