'use client';

import { useState, useEffect } from 'react';
import { Brain, BookOpen, AlertTriangle, TrendingUp, Target } from 'lucide-react';
import Card from '../ui/Card';
import Badge from '../ui/Badge';
import Progress from '../ui/Progress';

interface LearningData {
    agent_name: string;
    error_patterns: Array<{
        pattern_type: string;
        title: string;
        occurrence_count: number;
        avg_loss_percent: number;
        is_resolved: boolean;
    }>;
    strategy_performance: Array<{
        strategy_type: string;
        market_condition: string;
        win_rate: number;
        profit_factor: number;
        total_trades: number;
    }>;
    total_lessons: number;
    improvement_score: number;
}

export default function LearningDashboard() {
    const [agents, setAgents] = useState<string[]>([]);
    const [selectedAgent, setSelectedAgent] = useState<string | null>(null);
    const [learningData, setLearningData] = useState<LearningData | null>(null);
    const [loading, setLoading] = useState(true);

    // Fetch available agents
    useEffect(() => {
        const fetchAgents = async () => {
            try {
                const res = await fetch('/api/agents');
                if (res.ok) {
                    const data = await res.json();
                    const agentNames = data.agents?.map((a: any) => a.name) || [];
                    setAgents(agentNames);
                    if (agentNames.length > 0) {
                        setSelectedAgent(agentNames[0]);
                    }
                }
            } catch (error) {
                console.error('Failed to fetch agents:', error);
            }
        };
        fetchAgents();
    }, []);

    // Fetch learning data for selected agent
    useEffect(() => {
        if (!selectedAgent) return;

        const fetchLearning = async () => {
            setLoading(true);
            try {
                const res = await fetch(`/api/learning/summary/${selectedAgent}`);
                if (res.ok) {
                    const data = await res.json();
                    setLearningData(data);
                }
            } catch (error) {
                console.error('Failed to fetch learning data:', error);
            } finally {
                setLoading(false);
            }
        };
        fetchLearning();
    }, [selectedAgent]);

    return (
        <Card variant="glass" padding="none" className="h-full min-h-[60vh]">
            {/* Header */}
            <div className="p-6 border-b border-surface-border">
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-xl bg-primary/20 flex items-center justify-center">
                            <Brain className="w-5 h-5 text-primary" />
                        </div>
                        <div>
                            <h3 className="font-bold text-white">AI Learning Insights</h3>
                            <p className="text-xs text-gray-500">Agent improvement tracking</p>
                        </div>
                    </div>

                    {/* Agent Selector */}
                    <select
                        value={selectedAgent || ''}
                        onChange={(e) => setSelectedAgent(e.target.value)}
                        className="bg-surface-elevated border border-surface-border rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-primary"
                    >
                        {agents.map((agent) => (
                            <option key={agent} value={agent}>
                                {agent}
                            </option>
                        ))}
                    </select>
                </div>
            </div>

            {/* Content */}
            <div className="p-6">
                {loading ? (
                    <div className="space-y-4">
                        <div className="h-20 bg-surface-elevated animate-pulse rounded-xl" />
                        <div className="h-32 bg-surface-elevated animate-pulse rounded-xl" />
                    </div>
                ) : learningData ? (
                    <div className="space-y-6">
                        {/* Overview Stats */}
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                            <div className="bg-surface-elevated/50 rounded-xl p-4">
                                <div className="flex items-center gap-2 text-gray-400 text-xs mb-2">
                                    <BookOpen size={14} />
                                    Total Lessons
                                </div>
                                <p className="text-2xl font-bold font-mono text-white">
                                    {learningData.total_lessons || 0}
                                </p>
                            </div>
                            <div className="bg-surface-elevated/50 rounded-xl p-4">
                                <div className="flex items-center gap-2 text-gray-400 text-xs mb-2">
                                    <Target size={14} />
                                    Improvement Score
                                </div>
                                <p className="text-2xl font-bold font-mono text-primary">
                                    {(learningData.improvement_score || 0).toFixed(1)}%
                                </p>
                            </div>
                            <div className="bg-surface-elevated/50 rounded-xl p-4">
                                <div className="flex items-center gap-2 text-gray-400 text-xs mb-2">
                                    <AlertTriangle size={14} />
                                    Error Patterns
                                </div>
                                <p className="text-2xl font-bold font-mono text-warning">
                                    {learningData.error_patterns?.length || 0}
                                </p>
                            </div>
                            <div className="bg-surface-elevated/50 rounded-xl p-4">
                                <div className="flex items-center gap-2 text-gray-400 text-xs mb-2">
                                    <TrendingUp size={14} />
                                    Strategies
                                </div>
                                <p className="text-2xl font-bold font-mono text-success">
                                    {learningData.strategy_performance?.length || 0}
                                </p>
                            </div>
                        </div>

                        {/* Error Patterns */}
                        {learningData.error_patterns && learningData.error_patterns.length > 0 && (
                            <div className="bg-surface-elevated/30 rounded-xl p-4">
                                <h4 className="font-semibold text-white mb-4 flex items-center gap-2">
                                    <AlertTriangle className="w-4 h-4 text-warning" />
                                    Detected Error Patterns
                                </h4>
                                <div className="space-y-3">
                                    {learningData.error_patterns.slice(0, 5).map((pattern, i) => (
                                        <div
                                            key={i}
                                            className="flex items-center justify-between p-3 bg-surface rounded-lg"
                                        >
                                            <div>
                                                <p className="text-sm font-medium text-white">{pattern.title}</p>
                                                <p className="text-xs text-gray-500">
                                                    {pattern.pattern_type} • {pattern.occurrence_count} occurrences
                                                </p>
                                            </div>
                                            <div className="text-right">
                                                <Badge variant={pattern.is_resolved ? 'success' : 'danger'} size="sm">
                                                    {pattern.is_resolved ? 'Resolved' : 'Active'}
                                                </Badge>
                                                <p className="text-xs text-danger mt-1">
                                                    Avg Loss: {pattern.avg_loss_percent.toFixed(1)}%
                                                </p>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}

                        {/* Strategy Performance */}
                        {learningData.strategy_performance && learningData.strategy_performance.length > 0 && (
                            <div className="bg-surface-elevated/30 rounded-xl p-4">
                                <h4 className="font-semibold text-white mb-4 flex items-center gap-2">
                                    <TrendingUp className="w-4 h-4 text-success" />
                                    Strategy Performance
                                </h4>
                                <div className="space-y-3">
                                    {learningData.strategy_performance.slice(0, 5).map((strategy, i) => (
                                        <div key={i} className="p-3 bg-surface rounded-lg">
                                            <div className="flex items-center justify-between mb-2">
                                                <span className="text-sm font-medium text-white">
                                                    {strategy.strategy_type}
                                                </span>
                                                <Badge variant="info" size="sm">
                                                    {strategy.market_condition}
                                                </Badge>
                                            </div>
                                            <Progress
                                                value={strategy.win_rate}
                                                variant={strategy.win_rate >= 50 ? 'success' : 'danger'}
                                                size="sm"
                                                showLabel
                                                label={`Win Rate (${strategy.total_trades} trades)`}
                                            />
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}
                    </div>
                ) : (
                    <div className="flex flex-col items-center justify-center py-12 text-gray-500">
                        <Brain className="w-12 h-12 mb-4 opacity-30" />
                        <p className="text-lg font-medium">No Learning Data</p>
                        <p className="text-sm">Insights will appear after more trades</p>
                    </div>
                )}
            </div>
        </Card>
    );
}
