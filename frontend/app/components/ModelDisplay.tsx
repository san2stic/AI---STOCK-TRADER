"use client";

import { useEffect, useState } from "react";

interface ModelInfo {
    agents: Record<string, {
        name: string;
        model: string;
        category: string;
        personality: string;
        strategy: string;
    }>;
    categories: Record<string, string>;
    dynamic_enabled: boolean;
}

export default function ModelDisplay() {
    const [modelInfo, setModelInfo] = useState<ModelInfo | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [isRefreshing, setIsRefreshing] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const fetchModels = async () => {
        try {
            const apiUrl = process.env.NEXT_PUBLIC_API_URL || "";
            const response = await fetch(`${apiUrl}/api/models/current`);
            if (!response.ok) throw new Error("Failed to fetch models");
            const data = await response.json();
            setModelInfo(data);
            setError(null);
        } catch (err) {
            setError(err instanceof Error ? err.message : "Failed to load models");
        } finally {
            setIsLoading(false);
        }
    };

    const handleRefresh = async () => {
        setIsRefreshing(true);
        try {
            const apiUrl = process.env.NEXT_PUBLIC_API_URL || "";
            await fetch(`${apiUrl}/api/models/refresh`, { method: "POST" });
            await fetchModels();
        } catch (err) {
            setError("Failed to refresh models");
        } finally {
            setIsRefreshing(false);
        }
    };

    useEffect(() => {
        fetchModels();
    }, []);

    if (isLoading) {
        return (
            <div className="bg-gradient-to-br from-slate-900 to-slate-800 rounded-2xl p-6 border border-slate-700">
                <div className="animate-pulse">
                    <div className="h-6 bg-slate-700 rounded w-1/3 mb-4"></div>
                    <div className="space-y-3">
                        <div className="h-4 bg-slate-700 rounded"></div>
                        <div className="h-4 bg-slate-700 rounded w-5/6"></div>
                    </div>
                </div>
            </div>
        );
    }

    if (error || !modelInfo) {
        return (
            <div className="bg-gradient-to-br from-red-900/20 to-slate-900 rounded-2xl p-6 border border-red-500/30">
                <div className="flex items-center gap-3 text-red-400">
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <span>{error || "Failed to load model information"}</span>
                </div>
            </div>
        );
    }

    const getCategoryColor = (category: string) => {
        switch (category) {
            case "finance": return "from-green-500 to-emerald-600";
            case "data_analysis": return "from-blue-500 to-cyan-600";
            case "general": return "from-purple-500 to-pink-600";
            case "parsing": return "from-orange-500 to-amber-600";
            default: return "from-gray-500 to-slate-600";
        }
    };

    const getCategoryIcon = (category: string) => {
        switch (category) {
            case "finance": return "💹";
            case "data_analysis": return "📊";
            case "general": return "🤖";
            case "parsing": return "📝";
            default: return "⚙️";
        }
    };

    return (
        <div className="bg-gradient-to-br from-slate-900 to-slate-800 rounded-2xl p-6 border border-slate-700 shadow-2xl">
            {/* Header */}
            <div className="flex items-center justify-between mb-6">
                <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-gradient-to-br from-violet-500 to-purple-600 rounded-xl flex items-center justify-center">
                        <span className="text-2xl">🧠</span>
                    </div>
                    <div>
                        <h2 className="text-xl font-bold text-white">AI Models</h2>
                        <p className="text-sm text-slate-400">
                            {modelInfo.dynamic_enabled ? "Dynamic Selection Active" : "Static Configuration"}
                        </p>
                    </div>
                </div>

                <button
                    onClick={handleRefresh}
                    disabled={isRefreshing}
                    className="px-4 py-2 bg-gradient-to-r from-violet-600 to-purple-600 hover:from-violet-700 hover:to-purple-700 text-white rounded-lg font-medium transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                >
                    <svg
                        className={`w-4 h-4 ${isRefreshing ? 'animate-spin' : ''}`}
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                    >
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                    </svg>
                    {isRefreshing ? "Refreshing..." : "Refresh"}
                </button>
            </div>

            {/* Category Summary */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
                {Object.entries(modelInfo.categories).map(([category, model]) => (
                    <div
                        key={category}
                        className="bg-slate-800/50 rounded-xl p-3 border border-slate-700"
                    >
                        <div className="flex items-center gap-2 mb-1">
                            <span className="text-lg">{getCategoryIcon(category)}</span>
                            <span className="text-xs font-medium text-slate-400 uppercase">
                                {category.replace('_', ' ')}
                            </span>
                        </div>
                        <p className="text-xs text-white font-mono truncate" title={model}>
                            {model.split('/').pop()}
                        </p>
                    </div>
                ))}
            </div>

            {/* Agent Models */}
            <div className="space-y-3">
                <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-wider mb-3">
                    Agent Models
                </h3>
                <div className="grid gap-3">
                    {Object.entries(modelInfo.agents).map(([key, agent]) => (
                        <div
                            key={key}
                            className="bg-slate-800/30 rounded-xl p-4 border border-slate-700/50 hover:border-slate-600 transition-all duration-200"
                        >
                            <div className="flex items-start justify-between gap-4">
                                <div className="flex-1 min-w-0">
                                    <div className="flex items-center gap-2 mb-2">
                                        <h4 className="font-semibold text-white truncate">
                                            {agent.name}
                                        </h4>
                                        <span className={`px-2 py-0.5 rounded-full text-xs font-medium bg-gradient-to-r ${getCategoryColor(agent.category)} text-white`}>
                                            {getCategoryIcon(agent.category)} {agent.category.replace('_', ' ')}
                                        </span>
                                    </div>

                                    <div className="space-y-1">
                                        <div className="flex items-center gap-2">
                                            <span className="text-xs text-slate-500 w-20">Model:</span>
                                            <code className="text-xs font-mono text-green-400 bg-slate-900/50 px-2 py-0.5 rounded">
                                                {agent.model}
                                            </code>
                                        </div>
                                        <div className="flex items-center gap-2">
                                            <span className="text-xs text-slate-500 w-20">Strategy:</span>
                                            <span className="text-xs text-slate-300">{agent.strategy}</span>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            </div>

            {/* Footer Info */}
            <div className="mt-6 pt-4 border-t border-slate-700">
                <div className="flex items-center gap-2 text-xs text-slate-500">
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <span>
                        Models are {modelInfo.dynamic_enabled ? 'automatically selected' : 'statically configured'} and cached for performance
                    </span>
                </div>
            </div>
        </div>
    );
}
