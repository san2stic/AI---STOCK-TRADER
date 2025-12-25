import { useState } from 'react';
import { Brain, AlertTriangle, TrendingUp, Search, RefreshCw, CheckCircle, XCircle } from 'lucide-react';
import useApi from '../hooks/useApi';

interface ErrorPattern {
    pattern_type: string;
    description: string;
    occurrence_count: number;
    avg_loss_percent: number;
    severity_score: number;
    is_resolved: boolean;
    examples: string[];
}

interface StrategyPerformance {
    strategy_name: string;
    win_rate: number;
    avg_return: number;
    total_trades: number;
    market_condition: string;
    recommendation: string;
}

interface CollectiveInsights {
    common_error_types: {
        pattern_type: string;
        occurrences: number;
        avg_loss: number;
    }[];
    best_strategies_overall: StrategyPerformance[];
}

interface AgentErrorSummary {
    active_error_patterns: number;
    total_error_patterns: number;
    critical_patterns: number;
}

interface LearningSummary {
    agent_name: string;
    error_summary: AgentErrorSummary;
    best_strategy?: StrategyPerformance;
    learning_status: string;
    trades_completed: number;
}

export default function LearningDashboard() {
    const [selectedAgent, setSelectedAgent] = useState<string | null>(null);

    // Fetch Collective Insights
    const { data: collectiveData, loading: collectiveLoading } = useApi<CollectiveInsights>('/api/learning/collective?days=30', {
        autoFetch: true
    });

    // Fetch Agents List (reuse from API or props? better to fetch to be self-contained or pass as props. 
    // I'll assume I can get the list of agents from somewhere, but let's just fetch summaries for all known agents)
    // Actually, I can use the existing /api/agents to get the list, then fetch summaries.
    // Or just iterate standard agent names.
    const agentsList = ["GPT-4 Holder", "Claude Équilibré", "Grok Sniper", "Gemini Gestionnaire", "DeepSeek Nerveux", "Mistral Marine"];

    return (
        <div className="space-y-8 animate-fade-in-up">
            {/* Header Section */}
            <div className="flex items-center justify-between">
                <div>
                    <h2 className="text-3xl font-bold text-white flex items-center gap-3">
                        <Brain className="text-accent-pink w-8 h-8" />
                        Centre d'Apprentissage IA
                    </h2>
                    <p className="text-gray-400 mt-2">
                        suivi des erreurs cognitives et adaptation des stratégies
                    </p>
                </div>
                <div className="text-sm text-gray-500">
                    Auto-analyzed every 24h
                </div>
            </div>

            {/* Collective Insights Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                {/* Common Errors */}
                <div className="glass-card p-6 border border-danger/20">
                    <h3 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
                        <AlertTriangle className="text-danger w-5 h-5" />
                        Erreurs Fréquentes (Système)
                    </h3>
                    {collectiveLoading ? (
                        <div className="animate-pulse space-y-3">
                            {[1, 2, 3].map(i => <div key={i} className="h-12 bg-white/5 rounded" />)}
                        </div>
                    ) : (
                        <div className="space-y-4">
                            {collectiveData?.common_error_types.map((error, idx) => (
                                <div key={idx} className="bg-white/5 rounded-lg p-3 flex items-center justify-between border border-white/5 hover:border-danger/30 transition-colors">
                                    <div>
                                        <div className="font-medium text-danger-glow">{error.pattern_type}</div>
                                        <div className="text-xs text-gray-400">{error.occurrences} occurrences</div>
                                    </div>
                                    <div className="text-right">
                                        <div className="text-sm font-bold text-danger">-{error.avg_loss.toFixed(2)}%</div>
                                        <div className="text-xs text-gray-500">perte moy.</div>
                                    </div>
                                </div>
                            ))}
                            {(!collectiveData?.common_error_types?.length) && (
                                <div className="text-center text-gray-500 py-4">Aucune erreur majeure détectée</div>
                            )}
                        </div>
                    )}
                </div>

                {/* Best Strategies */}
                <div className="glass-card p-6 border border-success/20">
                    <h3 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
                        <TrendingUp className="text-success w-5 h-5" />
                        Meilleures Stratégies (Global)
                    </h3>
                    {collectiveLoading ? (
                        <div className="animate-pulse space-y-3">
                            {[1, 2, 3].map(i => <div key={i} className="h-12 bg-white/5 rounded" />)}
                        </div>
                    ) : (
                        <div className="space-y-4">
                            {collectiveData?.best_strategies_overall.map((strat, idx) => (
                                <div key={idx} className="bg-white/5 rounded-lg p-3 flex items-center justify-between border border-white/5 hover:border-success/30 transition-colors">
                                    <div>
                                        <div className="font-medium text-success-glow">{strat.strategy_name}</div>
                                        <div className="text-xs text-gray-400">{strat.market_condition}</div>
                                    </div>
                                    <div className="text-right">
                                        <div className="text-sm font-bold text-success">+{strat.win_rate.toFixed(1)}%</div>
                                        <div className="text-xs text-gray-500">win rate</div>
                                    </div>
                                </div>
                            ))}
                            {(!collectiveData?.best_strategies_overall?.length) && (
                                <div className="text-center text-gray-500 py-4">Pas assez de données de stratégie</div>
                            )}
                        </div>
                    )}
                </div>
            </div>

            {/* Agent Learning Status Cards */}
            <div>
                <h3 className="text-2xl font-bold text-white mb-6">État d'Apprentissage par Agent</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {agentsList.map(agent => (
                        <AgentLearningCard key={agent} agentName={agent} />
                    ))}
                </div>
            </div>
        </div>
    );
}

function AgentLearningCard({ agentName }: { agentName: string }) {
    const { data, loading } = useApi<LearningSummary>(`/api/learning/summary/${agentName}?days=30`, {
        autoFetch: true
    });

    if (loading) {
        return <div className="glass-card p-6 h-48 animate-pulse bg-white/5" />;
    }

    if (!data) return null;

    const hasErrors = data.error_summary.active_error_patterns > 0;

    return (
        <div className="glass-card p-6 relative overflow-hidden group hover:scale-[1.02] transition-transform duration-300">
            <div className={`absolute top-0 right-0 w-24 h-24 blur-[60px] opacity-20 ${hasErrors ? 'bg-danger' : 'bg-success'}`} />

            <div className="relative z-10">
                <div className="flex justify-between items-start mb-4">
                    <h4 className="font-bold text-lg text-white">{agentName}</h4>
                    {hasErrors ? (
                        <span className="bg-danger/20 text-danger text-xs px-2 py-1 rounded-full flex items-center gap-1">
                            <AlertTriangle size={12} /> Needs Focus
                        </span>
                    ) : (
                        <span className="bg-success/20 text-success text-xs px-2 py-1 rounded-full flex items-center gap-1">
                            <CheckCircle size={12} /> Optimized
                        </span>
                    )}
                </div>

                <div className="space-y-4">
                    <div className="flex justify-between text-sm">
                        <span className="text-gray-400">Erreurs Actives</span>
                        <span className={`font-mono font-bold ${hasErrors ? 'text-danger' : 'text-gray-300'}`}>
                            {data.error_summary.active_error_patterns}
                        </span>
                    </div>

                    <div className="flex justify-between text-sm">
                        <span className="text-gray-400">Top Stratégie</span>
                        <span className="font-mono text-accent truncate max-w-[120px]" title={data.best_strategy?.strategy_name}>
                            {data.best_strategy?.strategy_name || 'N/A'}
                        </span>
                    </div>

                    <div className="flex justify-between text-sm">
                        <span className="text-gray-400"> Trades Analysés</span>
                        <span className="font-mono text-white">{data.trades_completed}</span>
                    </div>
                </div>

                {/* Progress Bar for Error Resolution */}
                {/*  <div className="mt-4">
                    <div className="h-1 w-full bg-white/10 rounded-full overflow-hidden">
                        <div 
                            className="h-full bg-success transition-all duration-1000"
                            style={{ 
                                width: `${(1 - (data.error_summary.active_error_patterns / (data.error_summary.total_error_patterns || 1))) * 100}%` 
                            }} 
                        />
                    </div>
                </div> */}
            </div>
        </div>
    );
}
