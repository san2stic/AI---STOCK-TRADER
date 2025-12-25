'use client';

import { Bot, TrendingUp, TrendingDown, Target, Zap } from 'lucide-react';
import Card from '../ui/Card';
import Badge from '../ui/Badge';
import { CircularProgress } from '../ui/Progress';

interface Agent {
    name: string;
    total_value: number;
    pnl: number;
    pnl_percent: number;
    total_trades: number;
    win_rate: number;
    cash: number;
    positions_count: number;
    model?: string;
    model_category?: string;
}

interface AgentCardProps {
    agent: Agent;
    onClick?: () => void;
}

// Agent color mapping for visual distinction
const agentColors: Record<string, string> = {
    Titan: 'from-blue-500 to-blue-700',
    Nexus: 'from-purple-500 to-purple-700',
    Viper: 'from-red-500 to-red-700',
    Aegis: 'from-cyan-500 to-cyan-700',
    Surge: 'from-yellow-500 to-orange-600',
    Ranger: 'from-green-500 to-green-700',
    Oracle: 'from-indigo-500 to-indigo-700',
    Sentinel: 'from-gray-500 to-gray-700',
    Cipher: 'from-pink-500 to-pink-700',
    Warden: 'from-teal-500 to-teal-700',
};

// Agent emoji/icon mapping
const agentEmojis: Record<string, string> = {
    Titan: '🏔️',
    Nexus: '🔗',
    Viper: '🐍',
    Aegis: '🛡️',
    Surge: '⚡',
    Ranger: '🎯',
    Oracle: '🔮',
    Sentinel: '👁️',
    Cipher: '🔐',
    Warden: '⚔️',
};

export default function AgentCard({ agent, onClick }: AgentCardProps) {
    const isPositive = agent.pnl >= 0;
    const gradientClass = agentColors[agent.name] || 'from-primary to-secondary';
    const emoji = agentEmojis[agent.name] || '🤖';

    // Determine performance tier
    const getPerformanceTier = (winRate: number) => {
        if (winRate >= 70) return { label: 'Elite', variant: 'success' as const };
        if (winRate >= 50) return { label: 'Good', variant: 'info' as const };
        if (winRate >= 30) return { label: 'Learning', variant: 'warning' as const };
        return { label: 'Struggling', variant: 'danger' as const };
    };

    const tier = getPerformanceTier(agent.win_rate);

    return (
        <Card
            variant="glass"
            hover
            onClick={onClick}
            className="group relative overflow-hidden"
            padding="none"
        >
            {/* Gradient top bar */}
            <div className={`h-1 bg-gradient-to-r ${gradientClass}`} />

            <div className="p-5">
                {/* Header */}
                <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-3">
                        <div
                            className={`w-10 h-10 rounded-xl bg-gradient-to-br ${gradientClass} flex items-center justify-center text-lg shadow-lg group-hover:scale-110 transition-transform`}
                        >
                            {emoji}
                        </div>
                        <div>
                            <h3 className="font-bold text-white group-hover:text-primary transition-colors">
                                {agent.name}
                            </h3>
                            <p className="text-xs text-gray-500 font-mono">
                                {agent.model?.split('/').pop() || 'gemini-3-pro'}
                            </p>
                        </div>
                    </div>
                    <Badge variant={tier.variant} size="sm">
                        {tier.label}
                    </Badge>
                </div>

                {/* Stats Grid */}
                <div className="grid grid-cols-2 gap-3 mb-4">
                    {/* P&L */}
                    <div className="bg-surface-elevated/50 rounded-lg p-3">
                        <div className="flex items-center gap-1 text-xs text-gray-500 mb-1">
                            {isPositive ? (
                                <TrendingUp size={12} className="text-success" />
                            ) : (
                                <TrendingDown size={12} className="text-danger" />
                            )}
                            P&L
                        </div>
                        <p
                            className={`font-bold font-mono ${isPositive ? 'text-success' : 'text-danger'
                                }`}
                        >
                            {isPositive ? '+' : ''}${agent.pnl.toFixed(2)}
                        </p>
                        <p className={`text-xs ${isPositive ? 'text-success/70' : 'text-danger/70'}`}>
                            {isPositive ? '+' : ''}{agent.pnl_percent.toFixed(2)}%
                        </p>
                    </div>

                    {/* Win Rate */}
                    <div className="bg-surface-elevated/50 rounded-lg p-3 flex items-center justify-between">
                        <div>
                            <div className="flex items-center gap-1 text-xs text-gray-500 mb-1">
                                <Target size={12} />
                                Win Rate
                            </div>
                            <p className="font-bold font-mono text-white">
                                {agent.win_rate.toFixed(1)}%
                            </p>
                        </div>
                        <CircularProgress
                            value={agent.win_rate}
                            size={40}
                            strokeWidth={3}
                            variant={agent.win_rate >= 50 ? 'success' : 'danger'}
                            showValue={false}
                        />
                    </div>
                </div>

                {/* Footer Stats */}
                <div className="flex items-center justify-between text-xs text-gray-400 pt-3 border-t border-surface-border">
                    <span className="flex items-center gap-1">
                        <Zap size={12} />
                        {agent.total_trades} trades
                    </span>
                    <span>{agent.positions_count} positions</span>
                    <span className="font-mono">${agent.cash.toFixed(0)} cash</span>
                </div>
            </div>

            {/* Hover glow effect */}
            <div
                className={`absolute inset-0 opacity-0 group-hover:opacity-10 transition-opacity bg-gradient-to-br ${gradientClass} pointer-events-none`}
            />
        </Card>
    );
}
