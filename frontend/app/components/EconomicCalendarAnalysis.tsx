"use client";

import { useState, useEffect } from "react";
import { Brain, TrendingUp, TrendingDown, Activity, AlertTriangle, RefreshCw, Zap } from "lucide-react";

interface EconomicAnalysis {
    summary: string;
    market_outlook: "BULLISH" | "BEARISH" | "NEUTRAL" | "VOLATILE";
    volatility_level: "HIGH" | "MEDIUM" | "LOW";
    recommended_strategy: "NORMAL" | "CAUTIOUS" | "PAUSE" | "AGGRESSIVE";
    key_events: string[];
    trading_recommendations: string[];
    potential_impacts?: {
        stocks?: string;
        crypto?: string;
        forex?: string;
    };
    risk_factors?: string[];
    events_count: number;
    analyzed_at?: string;
}

interface EconomicCalendarAnalysisProps {
    daysAhead?: number;
}

export default function EconomicCalendarAnalysis({
    daysAhead = 7,
}: EconomicCalendarAnalysisProps) {
    const [analysis, setAnalysis] = useState<EconomicAnalysis | null>(null);
    const [loading, setLoading] = useState(true);
    const [refreshing, setRefreshing] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const fetchAnalysis = async (forceRefresh = false) => {
        try {
            if (forceRefresh) {
                setRefreshing(true);
                await fetch(`/api/economic-events/analysis/refresh?days_ahead=${daysAhead}`, {
                    method: "POST",
                });
            }

            const response = await fetch(
                `/api/economic-events/analysis?days_ahead=${daysAhead}&force_refresh=${forceRefresh}`
            );

            if (!response.ok) throw new Error("Failed to fetch analysis");

            const data = await response.json();
            setAnalysis(data);
            setError(null);
        } catch (err) {
            console.error("Error fetching economic analysis:", err);
            setError("Failed to load analysis");
        } finally {
            setLoading(false);
            setRefreshing(false);
        }
    };

    useEffect(() => {
        fetchAnalysis();

        // Auto-refresh every 6 hours
        const interval = setInterval(() => fetchAnalysis(), 21600000);
        return () => clearInterval(interval);
    }, [daysAhead]);

    const getOutlookColor = (outlook: string) => {
        switch (outlook) {
            case "BULLISH":
                return "from-green-500/20 to-green-600/10 border-green-500/30 text-green-300";
            case "BEARISH":
                return "from-red-500/20 to-red-600/10 border-red-500/30 text-red-300";
            case "VOLATILE":
                return "from-orange-500/20 to-orange-600/10 border-orange-500/30 text-orange-300";
            default:
                return "from-blue-500/20 to-blue-600/10 border-blue-500/30 text-blue-300";
        }
    };

    const getVolatilityColor = (level: string) => {
        switch (level) {
            case "HIGH":
                return "bg-red-500/20 text-red-300 border-red-500/50";
            case "MEDIUM":
                return "bg-yellow-500/20 text-yellow-300 border-yellow-500/50";
            case "LOW":
                return "bg-green-500/20 text-green-300 border-green-500/50";
            default:
                return "bg-gray-500/20 text-gray-300 border-gray-500/50";
        }
    };

    const getStrategyIcon = (strategy: string) => {
        switch (strategy) {
            case "AGGRESSIVE":
                return <Zap className="w-5 h-5" />;
            case "CAUTIOUS":
                return <AlertTriangle className="w-5 h-5" />;
            case "PAUSE":
                return <Activity className="w-5 h-5" />;
            default:
                return <TrendingUp className="w-5 h5" />;
        }
    };

    const getOutlookIcon = (outlook: string) => {
        switch (outlook) {
            case "BULLISH":
                return <TrendingUp className="w-6 h-6" />;
            case "BEARISH":
                return <TrendingDown className="w-6 h-6" />;
            default:
                return <Activity className="w-6 h-6" />;
        }
    };

    if (loading) {
        return (
            <div className="bg-gradient-to-br from-gray-900/50 to-gray-800/30 backdrop-blur-xl rounded-2xl border border-gray-700/50 p-6">
                <div className="flex items-center gap-3 mb-4">
                    <Brain className="w-6 h-6 text-purple-400 animate-pulse" />
                    <h2 className="text-xl font-bold text-white">AI Economic Analysis</h2>
                </div>
                <div className="flex items-center justify-center py-12">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-400"></div>
                </div>
            </div>
        );
    }

    if (error || !analysis) {
        return (
            <div className="bg-gradient-to-br from-gray-900/50 to-gray-800/30 backdrop-blur-xl rounded-2xl border border-gray-700/50 p-6">
                <div className="flex items-center gap-3 mb-4">
                    <Brain className="w-6 h-6 text-purple-400" />
                    <h2 className="text-xl font-bold text-white">AI Economic Analysis</h2>
                </div>
                <div className="text-center py-8 text-red-400">
                    <AlertTriangle className="w-12 h-12 mx-auto mb-3 opacity-50" />
                    <p>{error || "No analysis available"}</p>
                </div>
            </div>
        );
    }

    return (
        <div className="bg-gradient-to-br from-gray-900/50 to-gray-800/30 backdrop-blur-xl rounded-2xl border border-gray-700/50 p-6">
            {/* Header */}
            <div className="flex items-center justify-between mb-6">
                <div className="flex items-center gap-3">
                    <Brain className="w-6 h-6 text-purple-400" />
                    <h2 className="text-xl font-bold text-white">AI Economic Analysis</h2>
                    <span className="px-2 py-1 bg-purple-500/20 text-purple-300 text-xs rounded-lg border border-purple-500/30">
                        Powered by Claude 3.5
                    </span>
                </div>

                <button
                    onClick={() => fetchAnalysis(true)}
                    disabled={refreshing}
                    className="flex items-center gap-2 px-4 py-2 bg-purple-500/20 hover:bg-purple-500/30 text-purple-300 rounded-lg transition-all duration-200 border border-purple-500/30 disabled:opacity-50"
                >
                    <RefreshCw
                        className={`w-4 h-4 ${refreshing ? "animate-spin" : ""}`}
                    />
                    {refreshing ? "Analyzing..." : "Refresh"}
                </button>
            </div>

            {/* Market Outlook & Volatility */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                <div className={`bg-gradient-to-r ${getOutlookColor(analysis.market_outlook)} backdrop-blur-sm rounded-xl border p-4 hover:scale-[1.02] transition-all duration-200`}>
                    <div className="flex items-center justify-between">
                        <div>
                            <p className="text-xs text-gray-400 mb-1">Market Outlook</p>
                            <p className="text-xl font-bold">{analysis.market_outlook}</p>
                        </div>
                        {getOutlookIcon(analysis.market_outlook)}
                    </div>
                </div>

                <div className={`bg-gradient-to-r ${getVolatilityColor(analysis.volatility_level)} backdrop-blur-sm rounded-xl border p-4 hover:scale-[1.02] transition-all duration-200`}>
                    <div className="flex items-center justify-between">
                        <div>
                            <p className="text-xs text-gray-400 mb-1">Volatility Level</p>
                            <p className="text-xl font-bold">{analysis.volatility_level}</p>
                        </div>
                        <Activity className="w-6 h-6" />
                    </div>
                </div>

                <div className="bg-gradient-to-r from-indigo-500/20 to-indigo-600/10 border-indigo-500/30 backdrop-blur-sm rounded-xl border p-4 hover:scale-[1.02] transition-all duration-200 text-indigo-300">
                    <div className="flex items-center justify-between">
                        <div>
                            <p className="text-xs text-gray-400 mb-1">Strategy</p>
                            <p className="text-xl font-bold">{analysis.recommended_strategy}</p>
                        </div>
                        {getStrategyIcon(analysis.recommended_strategy)}
                    </div>
                </div>
            </div>

            {/* AI Summary */}
            <div className="bg-gray-800/30 rounded-xl p-4 mb-6 border border-gray-700/50">
                <h3 className="text-sm font-semibold text-gray-300 mb-2 flex items-center gap-2">
                    <Brain className="w-4 h-4 text-purple-400" />
                    AI Summary
                </h3>
                <p className="text-gray-300 leading-relaxed">{analysis.summary}</p>
            </div>

            {/* Trading Recommendations */}
            {analysis.trading_recommendations && analysis.trading_recommendations.length > 0 && (
                <div className="mb-6">
                    <h3 className="text-sm font-semibold text-gray-300 mb-3">Trading Recommendations</h3>
                    <div className="space-y-2">
                        {analysis.trading_recommendations.map((rec, index) => (
                            <div
                                key={index}
                                className="flex items-start gap-3 bg-blue-500/10 border border-blue-500/20 rounded-lg p-3 hover:bg-blue-500/20 transition-all duration-200"
                            >
                                <div className="w-6 h-6 rounded-full bg-blue-500/20 flex items-center justify-center text-blue-300 text-xs font-bold flex-shrink-0 mt-0.5">
                                    {index + 1}
                                </div>
                                <p className="text-sm text-gray-300 flex-1">{rec}</p>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Market Impacts */}
            {analysis.potential_impacts && (
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                    {analysis.potential_impacts.stocks && (
                        <div className="bg-gray-800/30 rounded-lg p-3 border border-gray-700/50">
                            <p className="text-xs text-gray-400 mb-1 font-semibold">Stocks Impact</p>
                            <p className="text-sm text-gray-300">{analysis.potential_impacts.stocks}</p>
                        </div>
                    )}
                    {analysis.potential_impacts.crypto && (
                        <div className="bg-gray-800/30 rounded-lg p-3 border border-gray-700/50">
                            <p className="text-xs text-gray-400 mb-1 font-semibold">Crypto Impact</p>
                            <p className="text-sm text-gray-300">{analysis.potential_impacts.crypto}</p>
                        </div>
                    )}
                    {analysis.potential_impacts.forex && (
                        <div className="bg-gray-800/30 rounded-lg p-3 border border-gray-700/50">
                            <p className="text-xs text-gray-400 mb-1 font-semibold">Forex Impact</p>
                            <p className="text-sm text-gray-300">{analysis.potential_impacts.forex}</p>
                        </div>
                    )}
                </div>
            )}

            {/* Key Events & Risk Factors */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {analysis.key_events && analysis.key_events.length > 0 && (
                    <div>
                        <h3 className="text-sm font-semibold text-gray-300 mb-3">Key Upcoming Events</h3>
                        <div className="space-y-2">
                            {analysis.key_events.slice(0, 3).map((event, index) => (
                                <div
                                    key={index}
                                    className="text-sm text-gray-400 flex items-start gap-2"
                                >
                                    <span className="text-purple-400">•</span>
                                    <span>{event}</span>
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {analysis.risk_factors && analysis.risk_factors.length > 0 && (
                    <div>
                        <h3 className="text-sm font-semibold text-gray-300 mb-3 flex items-center gap-2">
                            <AlertTriangle className="w-4 h-4 text-orange-400" />
                            Risk Factors
                        </h3>
                        <div className="space-y-2">
                            {analysis.risk_factors.slice(0, 3).map((risk, index) => (
                                <div
                                    key={index}
                                    className="text-sm text-gray-400 flex items-start gap-2"
                                >
                                    <span className="text-orange-400">⚠</span>
                                    <span>{risk}</span>
                                </div>
                            ))}
                        </div>
                    </div>
                )}
            </div>

            {/* Footer */}
            {analysis.analyzed_at && (
                <div className="mt-6 pt-4 border-t border-gray-700/50 text-xs text-gray-500 text-center flex items-center justify-center gap-2">
                    <span>Analyzed {analysis.events_count} events •</span>
                    <span>Updated: {new Date(analysis.analyzed_at).toLocaleTimeString()}</span>
                </div>
            )}
        </div>
    );
}
