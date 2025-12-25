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
    provider: string;
}

export default function ModelDisplay() {
    const [modelInfo, setModelInfo] = useState<ModelInfo | null>(null);
    const [isLoading, setIsLoading] = useState(true);
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

    return (
        <div className="bg-gradient-to-br from-slate-900 to-slate-800 rounded-2xl p-6 border border-slate-700 shadow-2xl">
            {/* Header */}
            <div className="flex items-center justify-between mb-6">
                <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-cyan-600 rounded-xl flex items-center justify-center">
                        <span className="text-2xl">☁️</span>
                    </div>
                    <div>
                        <h2 className="text-xl font-bold text-white">AI Infrastructure</h2>
                        <p className="text-sm text-blue-400 font-medium">
                            {modelInfo.provider || "Google Cloud Vertex AI"}
                        </p>
                    </div>
                </div>

                <div className="px-3 py-1 bg-blue-500/20 text-blue-400 rounded-full text-xs font-mono border border-blue-500/30">
                    Claude 3.5 Sonnet
                </div>
            </div>

            {/* Agent Models */}
            <div className="space-y-3">
                <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-wider mb-3">
                    Active Agents
                </h3>
                <div className="grid gap-3 grid-cols-1 md:grid-cols-2">
                    {Object.entries(modelInfo.agents).map(([key, agent]) => (
                        <div
                            key={key}
                            className="bg-slate-800/30 rounded-xl p-4 border border-slate-700/50 hover:border-blue-500/30 transition-all duration-200"
                        >
                            <div className="flex items-start justify-between gap-4">
                                <div className="flex-1 min-w-0">
                                    <div className="flex items-center gap-2 mb-2">
                                        <h4 className="font-semibold text-white truncate">
                                            {agent.name}
                                        </h4>
                                    </div>

                                    <div className="space-y-1">
                                        <div className="flex items-center gap-2">
                                            <span className="text-xs text-slate-500 w-16">Core:</span>
                                            <code className="text-xs font-mono text-cyan-400 bg-slate-900/50 px-2 py-0.5 rounded">
                                                Claude 3.5 Sonnet
                                            </code>
                                        </div>
                                        <div className="flex items-center gap-2">
                                            <span className="text-xs text-slate-500 w-16">Strategy:</span>
                                            <span className="text-xs text-slate-300 truncate">{agent.strategy}</span>
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
                    <svg className="w-4 h-4 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <span>
                        Enterprise-grade infrastructure via Google Cloud Vertex AI
                    </span>
                </div>
            </div>
        </div>
    );
}
