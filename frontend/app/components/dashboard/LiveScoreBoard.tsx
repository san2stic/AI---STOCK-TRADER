'use client';

import { Trophy, Medal, TrendingUp, TrendingDown, Percent } from 'lucide-react';
import Card from '../ui/Card';

interface Agent {
    name: string;
    total_value: number;
    pnl: number;
    pnl_percent: number;
    total_trades: number;
    win_rate: number;
}

interface LiveScoreBoardProps {
    agents: Agent[];
}

export default function LiveScoreBoard({ agents }: LiveScoreBoardProps) {
    // Sort agents by PnL percent (performance)
    const sortedAgents = [...agents].sort((a, b) => b.pnl_percent - a.pnl_percent);

    const getRankIcon = (index: number) => {
        switch (index) {
            case 0:
                return <Trophy className="w-5 h-5 text-yellow-500" />;
            case 1:
                return <Medal className="w-5 h-5 text-gray-400" />;
            case 2:
                return <Medal className="w-5 h-5 text-amber-700" />;
            default:
                return (
                    <span className="w-5 h-5 flex items-center justify-center text-xs text-gray-500 font-bold">
                        {index + 1}
                    </span>
                );
        }
    };

    const getRowClass = (index: number) => {
        if (index === 0) return 'bg-yellow-500/10 border-yellow-500/30';
        if (index === 1) return 'bg-gray-500/10 border-gray-500/30';
        if (index === 2) return 'bg-amber-700/10 border-amber-700/30';
        return 'bg-surface-elevated/30 border-surface-border';
    };

    return (
        <Card variant="glass" padding="none" className="overflow-hidden">
            {/* Header */}
            <div className="p-6 border-b border-surface-border">
                <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-warning/20 flex items-center justify-center">
                        <Trophy className="w-5 h-5 text-warning" />
                    </div>
                    <div>
                        <h3 className="font-bold text-white">Performance Leaderboard</h3>
                        <p className="text-xs text-gray-500">Agent rankings by P&L</p>
                    </div>
                </div>
            </div>

            {/* Table */}
            <div className="overflow-x-auto">
                <table className="w-full">
                    <thead>
                        <tr className="text-xs text-gray-500 uppercase tracking-wider">
                            <th className="text-left p-4 font-semibold">Rank</th>
                            <th className="text-left p-4 font-semibold">Agent</th>
                            <th className="text-right p-4 font-semibold">P&L</th>
                            <th className="text-right p-4 font-semibold">P&L %</th>
                            <th className="text-right p-4 font-semibold">Win Rate</th>
                            <th className="text-right p-4 font-semibold">Trades</th>
                        </tr>
                    </thead>
                    <tbody>
                        {sortedAgents.map((agent, index) => {
                            const isPositive = agent.pnl >= 0;
                            return (
                                <tr
                                    key={agent.name}
                                    className={`border-b ${getRowClass(index)} hover:bg-primary/5 transition-colors`}
                                >
                                    <td className="p-4">
                                        <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-surface-elevated">
                                            {getRankIcon(index)}
                                        </div>
                                    </td>
                                    <td className="p-4">
                                        <div className="flex items-center gap-3">
                                            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary to-secondary flex items-center justify-center text-xs font-bold">
                                                {agent.name.charAt(0)}
                                            </div>
                                            <span className="font-semibold text-white">{agent.name}</span>
                                        </div>
                                    </td>
                                    <td className="p-4 text-right">
                                        <div className="flex items-center justify-end gap-1">
                                            {isPositive ? (
                                                <TrendingUp className="w-4 h-4 text-success" />
                                            ) : (
                                                <TrendingDown className="w-4 h-4 text-danger" />
                                            )}
                                            <span
                                                className={`font-mono font-bold ${isPositive ? 'text-success' : 'text-danger'
                                                    }`}
                                            >
                                                {isPositive ? '+' : ''}${agent.pnl.toFixed(2)}
                                            </span>
                                        </div>
                                    </td>
                                    <td className="p-4 text-right">
                                        <span
                                            className={`font-mono font-bold ${isPositive ? 'text-success' : 'text-danger'
                                                }`}
                                        >
                                            {isPositive ? '+' : ''}{agent.pnl_percent.toFixed(2)}%
                                        </span>
                                    </td>
                                    <td className="p-4 text-right">
                                        <div className="flex items-center justify-end gap-2">
                                            <div className="w-16 h-1.5 bg-surface-border rounded-full overflow-hidden">
                                                <div
                                                    className={`h-full rounded-full ${agent.win_rate >= 50 ? 'bg-success' : 'bg-danger'
                                                        }`}
                                                    style={{ width: `${agent.win_rate}%` }}
                                                />
                                            </div>
                                            <span className="font-mono text-sm text-gray-400">
                                                {agent.win_rate.toFixed(0)}%
                                            </span>
                                        </div>
                                    </td>
                                    <td className="p-4 text-right">
                                        <span className="font-mono text-gray-400">{agent.total_trades}</span>
                                    </td>
                                </tr>
                            );
                        })}
                    </tbody>
                </table>
            </div>

            {agents.length === 0 && (
                <div className="p-8 text-center text-gray-500">
                    <p>No agent data available</p>
                </div>
            )}
        </Card>
    );
}
