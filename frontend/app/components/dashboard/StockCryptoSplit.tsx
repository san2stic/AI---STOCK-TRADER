'use client';

import { useState, useEffect } from 'react';
import { PieChart, TrendingUp, Bitcoin, BarChart3 } from 'lucide-react';
import Card from '../ui/Card';

interface BreakdownData {
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
        stock: { value: number; trades_count: number };
        crypto: { value: number; trades_count: number };
        total_pnl: number;
        pnl_percent: number;
    }>;
}

export default function StockCryptoSplit() {
    const [data, setData] = useState<BreakdownData | null>(null);

    useEffect(() => {
        const fetchData = async () => {
            try {
                const res = await fetch('/api/performance/breakdown');
                if (res.ok) {
                    setData(await res.json());
                }
            } catch (error) {
                console.error('Failed to fetch breakdown:', error);
            }
        };
        fetchData();
        const interval = setInterval(fetchData, 60000);
        return () => clearInterval(interval);
    }, []);

    if (!data) {
        return (
            <Card className="animate-pulse">
                <div className="h-32 bg-surface-elevated rounded-lg" />
            </Card>
        );
    }

    const { breakdown } = data;
    const totalValue = breakdown.stocks.total_value + breakdown.crypto.total_value;
    const stockPercent = totalValue > 0 ? (breakdown.stocks.total_value / totalValue) * 100 : 50;
    const cryptoPercent = totalValue > 0 ? (breakdown.crypto.total_value / totalValue) * 100 : 50;

    return (
        <Card variant="glass">
            <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 rounded-xl bg-secondary/20 flex items-center justify-center">
                    <PieChart className="w-5 h-5 text-secondary" />
                </div>
                <div>
                    <h3 className="font-bold text-white">Asset Split</h3>
                    <p className="text-xs text-gray-500">Portfolio distribution</p>
                </div>
            </div>

            {/* Split Visualization */}
            <div className="mb-4">
                <div className="h-3 bg-surface-border rounded-full overflow-hidden flex">
                    <div
                        className="bg-gradient-to-r from-primary to-cyan-400 h-full transition-all duration-500"
                        style={{ width: `${stockPercent}%` }}
                    />
                    <div
                        className="bg-gradient-to-r from-secondary to-purple-400 h-full transition-all duration-500"
                        style={{ width: `${cryptoPercent}%` }}
                    />
                </div>
            </div>

            {/* Stats */}
            <div className="grid grid-cols-2 gap-4">
                {/* Stocks */}
                <div className="bg-surface-elevated/50 rounded-xl p-4">
                    <div className="flex items-center gap-2 mb-3">
                        <TrendingUp className="w-4 h-4 text-primary" />
                        <span className="font-semibold text-white">Stocks</span>
                        <span className="text-xs text-gray-500 ml-auto">{stockPercent.toFixed(1)}%</span>
                    </div>
                    <p className="text-lg font-bold font-mono text-primary mb-2">
                        ${breakdown.stocks.total_value.toLocaleString('en-US', { minimumFractionDigits: 2 })}
                    </p>
                    <div className="flex items-center gap-3 text-xs text-gray-400">
                        <span className="flex items-center gap-1">
                            <BarChart3 size={12} />
                            {breakdown.stocks.total_trades} trades
                        </span>
                        {breakdown.stocks.pending_trades > 0 && (
                            <span className="text-warning">
                                {breakdown.stocks.pending_trades} pending
                            </span>
                        )}
                    </div>
                </div>

                {/* Crypto */}
                <div className="bg-surface-elevated/50 rounded-xl p-4">
                    <div className="flex items-center gap-2 mb-3">
                        <Bitcoin className="w-4 h-4 text-secondary" />
                        <span className="font-semibold text-white">Crypto</span>
                        <span className="text-xs text-gray-500 ml-auto">{cryptoPercent.toFixed(1)}%</span>
                    </div>
                    <p className="text-lg font-bold font-mono text-secondary mb-2">
                        ${breakdown.crypto.total_value.toLocaleString('en-US', { minimumFractionDigits: 2 })}
                    </p>
                    <div className="flex items-center gap-3 text-xs text-gray-400">
                        <span className="flex items-center gap-1">
                            <BarChart3 size={12} />
                            {breakdown.crypto.total_trades} trades
                        </span>
                        {breakdown.crypto.pending_trades > 0 && (
                            <span className="text-warning">
                                {breakdown.crypto.pending_trades} pending
                            </span>
                        )}
                    </div>
                </div>
            </div>
        </Card>
    );
}
