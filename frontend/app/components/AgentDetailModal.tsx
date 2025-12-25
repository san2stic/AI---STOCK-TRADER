import { useState, useEffect } from 'react';
import { X, TrendingUp, TrendingDown, Brain, Activity, History, Shield, Play } from 'lucide-react';
import useApi from '../hooks/useApi';

interface AgentDetailModalProps {
    agentName: string | null;
    onClose: () => void;
}

// Interfaces matching API response
interface Trade {
    symbol: string;
    action: string;
    quantity: number;
    price: number;
    executed_at: string;
    reasoning: string;
}

interface Decision {
    action: string;
    reasoning: string;
    created_at: string;
}

interface Reflection {
    well: string;
    wrong: string;
    improvements: string;
    created_at: string;
}

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
    recent_trades: Trade[];
    recent_decisions: Decision[];
    reflections: Reflection[];
}

export default function AgentDetailModal({ agentName, onClose }: AgentDetailModalProps) {
    const [activeTab, setActiveTab] = useState<'overview' | 'trades' | 'decisions' | 'reflections'>('overview');
    const [isReflecting, setIsReflecting] = useState(false);

    const { data: details, loading, refetch } = useApi<AgentDetails>(
        agentName ? `/api/agents/${agentName}` : '',
        {
            autoFetch: !!agentName
        }
    );

    useEffect(() => {
        if (agentName) {
            setActiveTab('overview');
        }
    }, [agentName]);

    if (!agentName) return null;

    const handleReflect = async () => {
        setIsReflecting(true);
        try {
            await fetch(`/api/agents/${agentName}/reflect`, { method: 'POST' });
            refetch(); // Refresh data to show new reflection
        } catch (error) {
            console.error("Reflection failed", error);
        } finally {
            setIsReflecting(false);
        }
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            {/* Backdrop */}
            <div
                className="absolute inset-0 bg-black/80 backdrop-blur-sm animate-fade-in"
                onClick={onClose}
            />

            {/* Modal Content */}
            <div className="relative bg-[#0A0A0B] border border-white/10 rounded-2xl w-full max-w-5xl max-h-[90vh] overflow-hidden flex flex-col shadow-2xl animate-scale-up">
                {/* Header */}
                <div className="p-6 border-b border-white/10 flex items-center justify-between bg-white/5">
                    <div className="flex items-center gap-4">
                        <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-primary to-secondary flex items-center justify-center text-white font-bold text-xl">
                            {agentName.substring(0, 2)}
                        </div>
                        <div>
                            <h2 className="text-2xl font-bold text-white">{agentName}</h2>
                            <p className="text-gray-400 text-sm">Agent Autonome & Apprentissage Continu</p>
                        </div>
                    </div>

                    <button
                        onClick={onClose}
                        className="p-2 hover:bg-white/10 rounded-full transition-colors text-gray-400 hover:text-white"
                    >
                        <X size={24} />
                    </button>
                </div>

                {/* Navbar */}
                <div className="flex border-b border-white/10 px-6">
                    {[
                        { id: 'overview', label: 'Vue Globale', icon: Activity },
                        { id: 'trades', label: 'Historique Trades', icon: History },
                        { id: 'decisions', label: 'Log Décisions', icon: Shield },
                        { id: 'reflections', label: 'Réflexions & Apprentissage', icon: Brain },
                    ].map(tab => {
                        const Icon = tab.icon;
                        const isActive = activeTab === tab.id;
                        return (
                            <button
                                key={tab.id}
                                onClick={() => setActiveTab(tab.id as any)}
                                className={`
                                    flex items-center gap-2 px-6 py-4 border-b-2 transition-colors font-medium
                                    ${isActive
                                        ? 'border-primary text-primary'
                                        : 'border-transparent text-gray-400 hover:text-white hover:bg-white/5'}
                                `}
                            >
                                <Icon size={18} />
                                {tab.label}
                            </button>
                        );
                    })}
                </div>

                {/* Body */}
                <div className="flex-1 overflow-y-auto p-6 min-h-[400px]">
                    {loading ? (
                        <div className="flex items-center justify-center h-full">
                            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
                        </div>
                    ) : details ? (
                        <>
                            {activeTab === 'overview' && (
                                <div className="space-y-8">
                                    <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                                        <StatCard label="Valeur Totale" value={`$${details.portfolio.total_value.toFixed(2)}`} />
                                        <StatCard label="Cash Disponible" value={`$${details.portfolio.cash.toFixed(2)}`} />
                                        <StatCard
                                            label="P&L Total"
                                            value={`$${details.portfolio.pnl.toFixed(2)}`}
                                            detail={`${details.portfolio.pnl_percent.toFixed(2)}%`}
                                            isPositive={details.portfolio.pnl >= 0}
                                        />
                                        <StatCard label="Win Rate" value={`${((details.stats.winning_trades / (details.stats.total_trades || 1)) * 100).toFixed(1)}%`} />
                                    </div>

                                    <div className="glass-card p-6">
                                        <h3 className="text-xl font-bold text-white mb-4">Positions Actuelles</h3>
                                        {Object.keys(details.portfolio.positions).length === 0 ? (
                                            <p className="text-gray-500 italic">Aucune position ouverte.</p>
                                        ) : (
                                            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                                                {Object.entries(details.portfolio.positions).map(([symbol, pos]: [string, any]) => (
                                                    <div key={symbol} className="bg-white/5 rounded-lg p-4 border border-white/10">
                                                        <div className="flex justify-between items-start mb-2">
                                                            <span className="font-bold text-lg text-white">{symbol}</span>
                                                            <span className={`text-sm ${pos.unrealized_pnl >= 0 ? 'text-success' : 'text-danger'}`}>
                                                                {pos.unrealized_pnl >= 0 ? '+' : ''}{pos.unrealized_pnl?.toFixed(2)}$
                                                            </span>
                                                        </div>
                                                        <div className="text-sm text-gray-400">
                                                            {pos.quantity} units @ ${pos.average_price?.toFixed(2)}
                                                        </div>
                                                    </div>
                                                ))}
                                            </div>
                                        )}
                                    </div>
                                </div>
                            )}

                            {activeTab === 'trades' && (
                                <div className="space-y-4">
                                    {details.recent_trades.map((trade, idx) => (
                                        <div key={idx} className="bg-white/5 rounded-lg p-4 border border-white/5 flex flex-col md:flex-row justify-between gap-4">
                                            <div>
                                                <div className="flex items-center gap-3 mb-2">
                                                    <span className={`px-2 py-1 rounded text-xs font-bold uppercase ${trade.action === 'buy' ? 'bg-success/20 text-success' : 'bg-danger/20 text-danger'
                                                        }`}>
                                                        {trade.action}
                                                    </span>
                                                    <span className="font-bold text-white">{trade.symbol}</span>
                                                    <span className="text-gray-400 text-sm">
                                                        {trade.quantity} @ ${trade.price.toFixed(2)}
                                                    </span>
                                                </div>
                                                <p className="text-sm text-gray-400 italic">"{trade.reasoning}"</p>
                                            </div>
                                            <div className="text-right text-xs text-gray-500 whitespace-nowrap">
                                                {new Date(trade.executed_at).toLocaleString()}
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}

                            {activeTab === 'decisions' && (
                                <div className="space-y-4">
                                    {details.recent_decisions.map((decision, idx) => (
                                        <div key={idx} className="bg-white/5 rounded-lg p-4 border border-white/5">
                                            <div className="flex justify-between items-center mb-2">
                                                <span className="text-primary font-mono text-sm">{decision.action}</span>
                                                <span className="text-xs text-gray-500">{new Date(decision.created_at).toLocaleString()}</span>
                                            </div>
                                            <div className="text-gray-300 text-sm whitespace-pre-wrap font-light">
                                                {decision.reasoning}
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}

                            {activeTab === 'reflections' && (
                                <div className="space-y-6">
                                    <div className="flex justify-between items-center bg-accent/10 p-4 rounded-xl border border-accent/20">
                                        <div>
                                            <h4 className="text-white font-bold">Apprentissage Manuel</h4>
                                            <p className="text-sm text-gray-400">Force l'agent à analyser ses trades récents maintenant.</p>
                                        </div>
                                        <button
                                            onClick={handleReflect}
                                            disabled={isReflecting}
                                            className="bg-accent hover:bg-accent-glow text-white px-4 py-2 rounded-lg font-medium transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                                        >
                                            {isReflecting ? <div className="animate-spin rounded-full h-4 w-4 border-2 border-white/30 border-t-white" /> : <Play size={16} fill="currentColor" />}
                                            {isReflecting ? 'Analyse...' : 'Lancer Réflexion'}
                                        </button>
                                    </div>

                                    {details.reflections.map((ref, idx) => (
                                        <div key={idx} className="glass-card p-6 border-l-4 border-l-primary">
                                            <div className="flex items-center gap-2 mb-4 text-xs text-gray-500 uppercase tracking-widest">
                                                <Brain size={14} />
                                                Session du {new Date(ref.created_at).toLocaleString()}
                                            </div>

                                            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                                <div>
                                                    <h5 className="text-success font-bold mb-2 flex items-center gap-2">
                                                        <TrendingUp size={16} /> Ce qui a bien marché
                                                    </h5>
                                                    <p className="text-gray-300 text-sm leading-relaxed">{ref.well}</p>
                                                </div>
                                                <div>
                                                    <h5 className="text-danger font-bold mb-2 flex items-center gap-2">
                                                        <TrendingDown size={16} /> Ce qui a échoué
                                                    </h5>
                                                    <p className="text-gray-300 text-sm leading-relaxed">{ref.wrong}</p>
                                                </div>
                                            </div>

                                            <div className="mt-4 pt-4 border-t border-white/5">
                                                <h5 className="text-accent font-bold mb-2">Plan d'Amélioration</h5>
                                                <p className="text-gray-300 text-sm bg-white/5 p-3 rounded-lg italic border border-white/5">
                                                    "{ref.improvements}"
                                                </p>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </>
                    ) : (
                        <div className="text-center text-gray-500">Failed to load agent details.</div>
                    )}
                </div>
            </div>
        </div>
    );
}

function StatCard({ label, value, detail, isPositive }: { label: string, value: string, detail?: string, isPositive?: boolean }) {
    return (
        <div className="bg-white/5 rounded-xl p-4 border border-white/10">
            <div className="text-gray-400 text-xs uppercase tracking-wider mb-1">{label}</div>
            <div className="text-2xl font-bold text-white flex items-end gap-2">
                {value}
                {detail && (
                    <span className={`text-sm mb-1 ${isPositive ? 'text-success' : 'text-danger'}`}>
                        {detail}
                    </span>
                )}
            </div>
        </div>
    );
}
