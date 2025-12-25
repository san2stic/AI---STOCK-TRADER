"use client";

import { useState, useEffect } from "react";
import { Calendar, TrendingUp, AlertCircle, RefreshCw, Clock } from "lucide-react";

interface EconomicEvent {
    date: string;
    time?: string;
    name: string;
    impact: "HIGH" | "MEDIUM" | "LOW";
    country: string;
    description?: string;
    forecast?: string;
    previous?: string;
}

interface EconomicCalendarProps {
    daysAhead?: number;
    minImpact?: "HIGH" | "MEDIUM" | "LOW";
}

export default function EconomicCalendar({
    daysAhead = 7,
    minImpact = "MEDIUM",
}: EconomicCalendarProps) {
    const [events, setEvents] = useState<EconomicEvent[]>([]);
    const [loading, setLoading] = useState(true);
    const [refreshing, setRefreshing] = useState(false);
    const [lastUpdate, setLastUpdate] = useState<Date | null>(null);
    const [selectedImpact, setSelectedImpact] = useState<string>(minImpact);

    const fetchEvents = async (forceRefresh = false) => {
        try {
            if (forceRefresh) {
                setRefreshing(true);
                // Trigger manual refresh
                await fetch(`/api/economic-events/refresh?days_ahead=${daysAhead}`, {
                    method: "POST",
                });
            }

            const response = await fetch(
                `/api/economic-events?days_ahead=${daysAhead}&min_impact=${selectedImpact}`
            );

            if (!response.ok) throw new Error("Failed to fetch events");

            const data = await response.json();
            setEvents(data.events || []);
            setLastUpdate(new Date());
        } catch (error) {
            console.error("Error fetching economic events:", error);
        } finally {
            setLoading(false);
            setRefreshing(false);
        }
    };

    useEffect(() => {
        fetchEvents();

        // Auto-refresh every hour
        const interval = setInterval(() => fetchEvents(), 3600000);
        return () => clearInterval(interval);
    }, [selectedImpact, daysAhead]);

    const getImpactColor = (impact: string) => {
        switch (impact) {
            case "HIGH":
                return "from-status-error/20 to-status-error/5 border-status-error/30";
            case "MEDIUM":
                return "from-status-warning/20 to-status-warning/5 border-status-warning/30";
            case "LOW":
                return "from-status-success/20 to-status-success/5 border-status-success/30";
            default:
                return "from-surface/20 to-surface/5 border-surface-border";
        }
    };

    const getImpactBadgeColor = (impact: string) => {
        switch (impact) {
            case "HIGH":
                return "bg-status-error/20 text-status-error border-status-error/50";
            case "MEDIUM":
                return "bg-status-warning/20 text-status-warning border-status-warning/50";
            case "LOW":
                return "bg-status-success/20 text-status-success border-status-success/50";
            default:
                return "bg-surface-active text-gray-400 border-surface-border";
        }
    };

    const getCountdownText = (eventDate: string, eventTime?: string) => {
        const now = new Date();
        const event = new Date(`${eventDate}T${eventTime || "12:00:00"}`);
        const diffMs = event.getTime() - now.getTime();
        const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
        const diffDays = Math.floor(diffHours / 24);

        if (diffHours < 0) return "Terminé";
        if (diffHours < 24) return `Dans ${diffHours}h`;
        return `Dans ${diffDays}j`;
    };

    const formatDate = (dateStr: string) => {
        const date = new Date(dateStr);
        return date.toLocaleDateString("fr-FR", {
            weekday: "short",
            month: "short",
            day: "numeric",
        });
    };

    if (loading) {
        return (
            <div className="glass-panel text-center p-8">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto mb-4"></div>
                <div className="text-gray-400">Scan des événements économiques...</div>
            </div>
        );
    }

    return (
        <div className="glass-panel p-6 rounded-3xl border border-surface-border">
            {/* Header */}
            <div className="flex items-center justify-between mb-6">
                <div className="flex items-center gap-3">
                    <Calendar className="w-6 h-6 text-primary" />
                    <h2 className="text-xl font-bold text-white">Calendrier Éco</h2>
                </div>

                <button
                    onClick={() => fetchEvents(true)}
                    disabled={refreshing}
                    className="flex items-center gap-2 px-3 py-1.5 bg-surface-active hover:bg-surface-hover text-gray-300 rounded-lg transition-all duration-200 border border-surface-border disabled:opacity-50 text-sm"
                >
                    <RefreshCw
                        className={`w-3.5 h-3.5 ${refreshing ? "animate-spin" : ""}`}
                    />
                    {refreshing ? "..." : "Refresh"}
                </button>
            </div>

            {/* Impact Filter */}
            <div className="flex gap-2 mb-6">
                {["HIGH", "MEDIUM", "LOW"].map((impact) => (
                    <button
                        key={impact}
                        onClick={() => setSelectedImpact(impact)}
                        className={`px-3 py-1.5 rounded-lg font-bold text-xs transition-all duration-200 ${selectedImpact === impact
                            ? "bg-primary text-background"
                            : "bg-surface-active text-gray-500 hover:text-gray-300"
                            }`}
                    >
                        {impact}
                    </button>
                ))}
            </div>

            {/* Events List */}
            <div className="space-y-3 max-h-[600px] overflow-y-auto custom-scrollbar pr-2">
                {events.length === 0 ? (
                    <div className="flex flex-col items-center justify-center py-12 text-gray-400/50">
                        <AlertCircle className="w-12 h-12 mb-3 opacity-50" />
                        <p>Aucun événement majeur détecté</p>
                    </div>
                ) : (
                    events.map((event, index) => (
                        <div
                            key={index}
                            className={`bg-gradient-to-r ${getImpactColor(
                                event.impact
                            )} backdrop-blur-sm rounded-xl border p-4 hover:scale-[1.01] transition-all duration-200 group`}
                        >
                            <div className="flex items-start justify-between gap-4">
                                <div className="flex-1">
                                    {/* Event Name & Country */}
                                    <div className="flex items-center gap-2 mb-2">
                                        <h3 className="text-white font-bold text-sm group-hover:text-primary transition-colors">{event.name}</h3>
                                        <span className="px-1.5 py-0.5 bg-background/50 text-gray-300 text-[10px] uppercase font-mono rounded border border-white/5">
                                            {event.country}
                                        </span>
                                    </div>

                                    {/* Date & Time */}
                                    <div className="flex items-center gap-3 text-xs text-gray-400 mb-2">
                                        <span className="flex items-center gap-1">
                                            <Calendar className="w-3 h-3" />
                                            {formatDate(event.date)}
                                        </span>
                                        {event.time && (
                                            <span className="flex items-center gap-1">
                                                <Clock className="w-3 h-3" />
                                                {event.time}
                                            </span>
                                        )}
                                    </div>

                                    {/* Forecast & Previous */}
                                    {(event.forecast || event.previous) && (
                                        <div className="flex gap-4 text-xs text-gray-500 border-t border-white/5 pt-2 mt-2">
                                            {event.forecast && (
                                                <span>
                                                    Prévu: <strong className="text-gray-300">{event.forecast}</strong>
                                                </span>
                                            )}
                                            {event.previous && (
                                                <span>
                                                    Préc: <strong className="text-gray-300">{event.previous}</strong>
                                                </span>
                                            )}
                                        </div>
                                    )}
                                </div>

                                {/* Impact Badge & Countdown */}
                                <div className="flex flex-col items-end gap-2">
                                    <span
                                        className={`px-2 py-0.5 rounded text-[10px] font-bold border ${getImpactBadgeColor(
                                            event.impact
                                        )}`}
                                    >
                                        {event.impact}
                                    </span>
                                    <span className="text-[10px] text-gray-500 uppercase font-bold tracking-wider">
                                        {getCountdownText(event.date, event.time)}
                                    </span>
                                </div>
                            </div>
                        </div>
                    ))
                )}
            </div>

            {/* Last Update */}
            {lastUpdate && (
                <div className="mt-4 pt-4 border-t border-surface-border text-[10px] text-gray-600 text-center uppercase tracking-widest">
                    MAJ: {lastUpdate.toLocaleTimeString()}
                </div>
            )}
        </div>
    );
}
