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
                return "from-red-500/20 to-red-600/10 border-red-500/30";
            case "MEDIUM":
                return "from-yellow-500/20 to-yellow-600/10 border-yellow-500/30";
            case "LOW":
                return "from-green-500/20 to-green-600/10 border-green-500/30";
            default:
                return "from-gray-500/20 to-gray-600/10 border-gray-500/30";
        }
    };

    const getImpactBadgeColor = (impact: string) => {
        switch (impact) {
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

    const getCountdownText = (eventDate: string, eventTime?: string) => {
        const now = new Date();
        const event = new Date(`${eventDate}T${eventTime || "12:00:00"}`);
        const diffMs = event.getTime() - now.getTime();
        const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
        const diffDays = Math.floor(diffHours / 24);

        if (diffHours < 0) return "Past";
        if (diffHours < 24) return `In ${diffHours}h`;
        return `In ${diffDays}d`;
    };

    const formatDate = (dateStr: string) => {
        const date = new Date(dateStr);
        return date.toLocaleDateString("en-US", {
            weekday: "short",
            month: "short",
            day: "numeric",
        });
    };

    if (loading) {
        return (
            <div className="bg-gradient-to-br from-gray-900/50 to-gray-800/30 backdrop-blur-xl rounded-2xl border border-gray-700/50 p-6">
                <div className="flex items-center gap-3 mb-4">
                    <Calendar className="w-6 h-6 text-blue-400" />
                    <h2 className="text-xl font-bold text-white">Economic Calendar</h2>
                </div>
                <div className="flex items-center justify-center py-12">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-400"></div>
                </div>
            </div>
        );
    }

    return (
        <div className="bg-gradient-to-br from-gray-900/50 to-gray-800/30 backdrop-blur-xl rounded-2xl border border-gray-700/50 p-6">
            {/* Header */}
            <div className="flex items-center justify-between mb-6">
                <div className="flex items-center gap-3">
                    <Calendar className="w-6 h-6 text-blue-400" />
                    <h2 className="text-xl font-bold text-white">Economic Calendar</h2>
                </div>

                <button
                    onClick={() => fetchEvents(true)}
                    disabled={refreshing}
                    className="flex items-center gap-2 px-4 py-2 bg-blue-500/20 hover:bg-blue-500/30 text-blue-300 rounded-lg transition-all duration-200 border border-blue-500/30 disabled:opacity-50"
                >
                    <RefreshCw
                        className={`w-4 h-4 ${refreshing ? "animate-spin" : ""}`}
                    />
                    {refreshing ? "Refreshing..." : "Refresh"}
                </button>
            </div>

            {/* Impact Filter */}
            <div className="flex gap-2 mb-6">
                {["HIGH", "MEDIUM", "LOW"].map((impact) => (
                    <button
                        key={impact}
                        onClick={() => setSelectedImpact(impact)}
                        className={`px-4 py-2 rounded-lg font-medium transition-all duration-200 ${selectedImpact === impact
                                ? "bg-blue-500 text-white"
                                : "bg-gray-700/30 text-gray-400 hover:bg-gray-700/50"
                            }`}
                    >
                        {impact}
                    </button>
                ))}
            </div>

            {/* Events List */}
            <div className="space-y-3 max-h-[600px] overflow-y-auto custom-scrollbar">
                {events.length === 0 ? (
                    <div className="flex flex-col items-center justify-center py-12 text-gray-400">
                        <AlertCircle className="w-12 h-12 mb-3 opacity-50" />
                        <p>No upcoming events found</p>
                    </div>
                ) : (
                    events.map((event, index) => (
                        <div
                            key={index}
                            className={`bg-gradient-to-r ${getImpactColor(
                                event.impact
                            )} backdrop-blur-sm rounded-xl border p-4 hover:scale-[1.02] transition-all duration-200`}
                        >
                            <div className="flex items-start justify-between gap-4">
                                <div className="flex-1">
                                    {/* Event Name & Country */}
                                    <div className="flex items-center gap-2 mb-2">
                                        <h3 className="text-white font-semibold">{event.name}</h3>
                                        <span className="px-2 py-0.5 bg-gray-700/50 text-gray-300 text-xs rounded-md border border-gray-600/50">
                                            {event.country}
                                        </span>
                                    </div>

                                    {/* Date & Time */}
                                    <div className="flex items-center gap-3 text-sm text-gray-400 mb-2">
                                        <span className="flex items-center gap-1">
                                            <Calendar className="w-4 h-4" />
                                            {formatDate(event.date)}
                                        </span>
                                        {event.time && (
                                            <span className="flex items-center gap-1">
                                                <Clock className="w-4 h-4" />
                                                {event.time}
                                            </span>
                                        )}
                                    </div>

                                    {/* Description */}
                                    {event.description && (
                                        <p className="text-sm text-gray-400 mb-2">
                                            {event.description}
                                        </p>
                                    )}

                                    {/* Forecast & Previous */}
                                    {(event.forecast || event.previous) && (
                                        <div className="flex gap-4 text-xs text-gray-500">
                                            {event.forecast && (
                                                <span>
                                                    Forecast: <strong>{event.forecast}</strong>
                                                </span>
                                            )}
                                            {event.previous && (
                                                <span>
                                                    Previous: <strong>{event.previous}</strong>
                                                </span>
                                            )}
                                        </div>
                                    )}
                                </div>

                                {/* Impact Badge & Countdown */}
                                <div className="flex flex-col items-end gap-2">
                                    <span
                                        className={`px-3 py-1 rounded-lg text-xs font-bold border ${getImpactBadgeColor(
                                            event.impact
                                        )}`}
                                    >
                                        {event.impact}
                                    </span>
                                    <span className="text-xs text-gray-400 font-medium">
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
                <div className="mt-4 pt-4 border-t border-gray-700/50 text-xs text-gray-500 text-center">
                    Last updated: {lastUpdate.toLocaleTimeString()}
                </div>
            )}

            <style jsx>{`
        .custom-scrollbar::-webkit-scrollbar {
          width: 6px;
        }
        .custom-scrollbar::-webkit-scrollbar-track {
          background: rgba(55, 65, 81, 0.3);
          border-radius: 10px;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb {
          background: rgba(107, 114, 128, 0.5);
          border-radius: 10px;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover {
          background: rgba(107, 114, 128, 0.7);
        }
      `}</style>
        </div>
    );
}
