'use client';

import { useState, useEffect } from 'react';
import { X, Bot, TrendingUp, TrendingDown, Clock, Target, Zap, Brain, AlertTriangle } from 'lucide-react';
import Card from '../ui/Card';
import Badge from '../ui/Badge';
import Button from '../ui/Button';
import Progress from '../ui/Progress';

interface AgentDetails {
    agent: string;
    portfolio: {
        cash: number;
        total_value: number;
        pnl: number;
        pnl_percent: number;
        positions: Record<string, any>;
    };
    stats: {
        total_trades: number;
        winning_trades: number;
        losing_trades: number;
        sharpe_ratio: number;
        max_drawdown: number;
    };
    recent_trades: Array<{
        symbol: string;
        action: string;
        quantity: number;
        price: number;
        executed_at: string;
        reasoning: string;
    }>;
    recent_decisions: Array<{
        action: string;
        reasoning: string;
        created_at: string;
    }>;
    reflections: Array<{
        well: string;
        wrong: string;
        improvements: string;
        created_at: string;
    }>;
}

interface AgentDetailModalProps {
    agentName: string;
    onClose: () => void;
}

export default function AgentDetailModal({ agentName, onClose }: AgentDetailModalProps) {
    const [data, setData] = useState<AgentDetails | null>(null);
    const [loading, setLoading] = useState(true);
    const [activeTab, setActiveTab] = useState<'overview' | 'trades' | 'decisions' | 'reflections'>('overview');

    useEffect(() => {
        const fetchDetails = async () => {
            try {
                const res = await fetch(`/api/agents/${agentName}`);
                if (res.ok) {
                    setData(await res.json());
                }
            } catch (error) {
                console.error('Failed to fetch agent details:', error);
            } finally {
                setLoading(false);
            }
        };
        fetchDetails();
    }, [agentName]);

    // Handle escape key
    useEffect(() => {
        const handleEscape = (e: KeyboardEvent) => {
            if (e.key === 'Escape') onClose();
        };
        document.addEventListener('keydown', handleEscape);
        document.body.style.overflow = 'hidden';
        return () => {
            document.removeEventListener('keydown', handleEscape);
            document.body.style.overflow = 'unset';
        };
    }, [onClose]);

    const tabs = [
        { id: 'overview', label: 'Overview', icon: Bot },
        { id: 'trades', label: 'Trades', icon: TrendingUp },
        { id: 'decisions', label: 'Decisions', icon: Brain },
        { id: 'reflections', label: 'Reflections', icon: AlertTriangle },
    ];

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            {/* Backdrop */}
            <div className="absolute inset-0 bg-black/80 backdrop-blur-sm" onClick={onClose} />

            {/* Modal */}
            <div className="relative w-full max-w-4xl max-h-[90vh] bg-surface/95 backdrop-blur-xl border border-surface-border rounded-2xl shadow-2xl overflow-hidden animate-slide-up">
                {/* Header */}
                <div className="flex items-center justify-between p-6 border-b border-surface-border">
                    <div className="flex items-center gap-4">
                        <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-primary to-secondary flex items-center justify-center">
                            <Bot className="w-6 h-6 text-white" />
                        </div>
                        <div>
                            <h2 className="text-xl font-bold text-white">{agentName}</h2>
                            <p className="text-sm text-gray-500">Agent Performance Details</p>
                        </div>
                    </div>
                    <button
                        onClick={onClose}
                        className="p-2 rounded-lg text-gray-400 hover:text-white hover:bg-surface-elevated transition-colors"
                    >
                        <X size={20} />
                    </button>
                </div>

                {/* Tabs */}
                <div className="flex border-b border-surface-border">
                    {tabs.map((tab) => {
                        const Icon = tab.icon;
                        return (
                            <button
                                key={tab.id}
                                onClick={() => setActiveTab(tab.id as any)}
                                className={`flex items-center gap-2 px-6 py-3 text-sm font-medium transition-colors ${activeTab === tab.id
                                        ? 'text-primary border-b-2 border-primary'
                                        : 'text-gray-400 hover:text-white'
                                    }`}
                            >
                                <Icon size={16} />
                                {tab.label}
                            </button>
                        );
                    })}
                </div>

                {/* Content */}
                <div className="p-6 overflow-y-auto max-h-[calc(90vh-200px)]">
                    {loading ? (
                        <div className="flex items-center justify-center py-12">
                            <div className="loading-spinner" />
                        </div>
                    ) : !data ? (
                        <div className="text-center py-12 text-gray-500">
                            Failed to load agent details
                        </div>
                    ) : (
                        <>
                            {activeTab === 'overview' && (
                                <div className="space-y-6 animate-fade-in">
                                    {/* Stats Grid */}
                                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                                        <StatCard
                                            icon={<TrendingUp size={20} />}
                                            label="Total P&L"
                                            value={`$${data.portfolio.pnl.toFixed(2)}`}
                                            subValue={`${data.portfolio.pnl_percent.toFixed(2)}%`}
                                            isPositive={data.portfolio.pnl >= 0}
                                        />
                                        <StatCard
                                            icon={<Target size={20} />}
                                            label="Win Rate"
                                            value={`${((data.stats.winning_trades / (data.stats.total_trades || 1)) * 100).toFixed(1)}%`}
                                            subValue={`${data.stats.winning_trades}W / ${data.stats.losing_trades}L`}
                                        />
                                        <StatCard
                                            icon={<Zap size={20} />}
                                            label="Total Trades"
                                            value={data.stats.total_trades.toString()}
                                        />
                                        <StatCard
                                            icon={<AlertTriangle size={20} />}
                                            label="Max Drawdown"
                                            value={`${(data.stats.max_drawdown || 0).toFixed(2)}%`}
                                            isNegative={true}
                                        />
                                    </div>

                                    {/* Positions */}
                                    <Card variant="default" padding="md">
                                        <h3 className="font-bold text-white mb-4">Active Positions</h3>
                                        {Object.keys(data.portfolio.positions || {}).length > 0 ? (
                                            <div className="space-y-2">
                                                {Object.entries(data.portfolio.positions).map(([symbol, position]: [string, any]) => (
                                                    <div
                                                        key={symbol}
                                                        className="flex items-center justify-between p-3 bg-surface-elevated rounded-lg"
                                                    >
                                                        <span className="font-mono font-bold">{symbol}</span>
                                                        <span className="text-gray-400">{position.quantity} shares</span>
                                                        <span className="font-mono">${position.current_value?.toFixed(2) || 'N/A'}</span>
                                                    </div>
                                                ))}
                                            </div>
                                        ) : (
                                            <p className="text-gray-500 text-center py-4">No active positions</p>
                                        )}
                                    </Card>
                                </div>
                            )}

                            {activeTab === 'trades' && (
                                <div className="space-y-4 animate-fade-in">
                                    {data.recent_trades.length > 0 ? (
                                        data.recent_trades.map((trade, i) => (
                                            <Card key={i} variant="default" padding="md">
                                                <div className="flex items-center justify-between mb-2">
                                                    <div className="flex items-center gap-3">
                                                        <Badge variant={trade.action === 'BUY' ? 'success' : 'danger'}>
                                                            {trade.action}
                                                        </Badge>
                                                        <span className="font-mono font-bold">{trade.symbol}</span>
                                                    </div>
                                                    <span className="text-sm text-gray-500">
                                                        {trade.executed_at ? new Date(trade.executed_at).toLocaleString() : 'Pending'}
                                                    </span>
                                                </div>
                                                <div className="flex items-center gap-4 text-sm text-gray-400 mb-2">
                                                    <span>{trade.quantity} shares @ ${trade.price.toFixed(2)}</span>
                                                </div>
                                                {trade.reasoning && (
                                                    <p className="text-sm text-gray-500 border-t border-surface-border pt-2 mt-2">
                                                        {trade.reasoning}
                                                    </p>
                                                )}
                                            </Card>
                                        ))
                                    ) : (
                                        <p className="text-center text-gray-500 py-8">No recent trades</p>
                                    )}
                                </div>
                            )}

                            {activeTab === 'decisions' && (
                                <div className="space-y-4 animate-fade-in">
                                    {data.recent_decisions.length > 0 ? (
                                        data.recent_decisions.map((decision, i) => (
                                            <Card key={i} variant="default" padding="md">
                                                <div className="flex items-center justify-between mb-2">
                                                    <Badge variant="info">{decision.action.toUpperCase()}</Badge>
                                                    <span className="text-sm text-gray-500">
                                                        {new Date(decision.created_at).toLocaleString()}
                                                    </span>
                                                </div>
                                                <p className="text-sm text-gray-400 whitespace-pre-wrap">
                                                    {decision.reasoning || 'No reasoning provided'}
                                                </p>
                                            </Card>
                                        ))
                                    ) : (
                                        <p className="text-center text-gray-500 py-8">No recent decisions</p>
                                    )}
                                </div>
                            )}

                            {activeTab === 'reflections' && (
                                <div className="space-y-4 animate-fade-in">
                                    {data.reflections.length > 0 ? (
                                        data.reflections.map((reflection, i) => (
                                            <Card key={i} variant="default" padding="md">
                                                <div className="text-sm text-gray-500 mb-3">
                                                    {new Date(reflection.created_at).toLocaleString()}
                                                </div>
                                                {reflection.well && (
                                                    <div className="mb-3">
                                                        <h4 className="text-success font-semibold mb-1">✓ What Went Well</h4>
                                                        <p className="text-sm text-gray-400">{reflection.well}</p>
                                                    </div>
                                                )}
                                                {reflection.wrong && (
                                                    <div className="mb-3">
                                                        <h4 className="text-danger font-semibold mb-1">✗ What Went Wrong</h4>
                                                        <p className="text-sm text-gray-400">{reflection.wrong}</p>
                                                    </div>
                                                )}
                                                {reflection.improvements && (
                                                    <div>
                                                        <h4 className="text-warning font-semibold mb-1">→ Improvements</h4>
                                                        <p className="text-sm text-gray-400">{reflection.improvements}</p>
                                                    </div>
                                                )}
                                            </Card>
                                        ))
                                    ) : (
                                        <p className="text-center text-gray-500 py-8">No reflections yet</p>
                                    )}
                                </div>
                            )}
                        </>
                    )}
                </div>
            </div>
        </div>
    );
}

function StatCard({
    icon,
    label,
    value,
    subValue,
    isPositive,
    isNegative,
}: {
    icon: React.ReactNode;
    label: string;
    value: string;
    subValue?: string;
    isPositive?: boolean;
    isNegative?: boolean;
}) {
    const valueColor = isPositive ? 'text-success' : isNegative ? 'text-danger' : 'text-white';

    return (
        <div className="bg-surface-elevated/50 rounded-xl p-4">
            <div className="flex items-center gap-2 text-gray-400 text-xs mb-2">
                {icon}
                {label}
            </div>
            <p className={`text-xl font-bold font-mono ${valueColor}`}>{value}</p>
            {subValue && <p className="text-xs text-gray-500 mt-1">{subValue}</p>}
        </div>
    );
}
