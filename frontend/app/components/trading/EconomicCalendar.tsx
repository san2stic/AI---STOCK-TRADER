'use client';

import { useState, useEffect } from 'react';
import { Calendar, AlertTriangle, Clock, TrendingUp, TrendingDown } from 'lucide-react';
import Card from '../ui/Card';
import Badge from '../ui/Badge';

interface EconomicEvent {
    title: string;
    date: string;
    time: string;
    impact: 'HIGH' | 'MEDIUM' | 'LOW';
    country: string;
    forecast?: string;
    previous?: string;
}

interface EconomicCalendarProps {
    daysAhead?: number;
    minImpact?: 'HIGH' | 'MEDIUM' | 'LOW';
}

export default function EconomicCalendar({ daysAhead = 7, minImpact = 'MEDIUM' }: EconomicCalendarProps) {
    const [events, setEvents] = useState<EconomicEvent[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchEvents = async () => {
            try {
                const res = await fetch(`/api/economic/events?days=${daysAhead}`);
                if (res.ok) {
                    const data = await res.json();
                    setEvents(data.events || []);
                }
            } catch (error) {
                console.error('Failed to fetch economic events:', error);
            } finally {
                setLoading(false);
            }
        };
        fetchEvents();
    }, [daysAhead]);

    const getImpactColor = (impact: string) => {
        switch (impact) {
            case 'HIGH':
                return 'danger';
            case 'MEDIUM':
                return 'warning';
            case 'LOW':
                return 'info';
            default:
                return 'neutral';
        }
    };

    const formatDate = (dateStr: string) => {
        const date = new Date(dateStr);
        const today = new Date();
        const tomorrow = new Date(today);
        tomorrow.setDate(tomorrow.getDate() + 1);

        if (date.toDateString() === today.toDateString()) {
            return 'Today';
        } else if (date.toDateString() === tomorrow.toDateString()) {
            return 'Tomorrow';
        }
        return date.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });
    };

    // Filter by minimum impact
    const filteredEvents = events.filter((event) => {
        const impactOrder = { HIGH: 3, MEDIUM: 2, LOW: 1 };
        return impactOrder[event.impact] >= impactOrder[minImpact];
    });

    return (
        <Card variant="glass" padding="none" className="h-full">
            <div className="p-4 border-b border-surface-border">
                <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-lg bg-warning/20 flex items-center justify-center">
                        <Calendar className="w-4 h-4 text-warning" />
                    </div>
                    <div>
                        <h3 className="font-bold text-white text-sm">Economic Calendar</h3>
                        <p className="text-2xs text-gray-500">Next {daysAhead} days</p>
                    </div>
                </div>
            </div>

            <div className="max-h-64 overflow-y-auto">
                {loading ? (
                    <div className="p-4 space-y-2">
                        {[1, 2, 3].map((i) => (
                            <div key={i} className="h-12 bg-surface-elevated animate-pulse rounded-lg" />
                        ))}
                    </div>
                ) : filteredEvents.length > 0 ? (
                    <div className="divide-y divide-surface-border">
                        {filteredEvents.slice(0, 8).map((event, i) => (
                            <div key={i} className="p-3 hover:bg-surface-elevated/50 transition-colors">
                                <div className="flex items-start justify-between gap-2">
                                    <div className="flex-1 min-w-0">
                                        <p className="text-sm font-medium text-white truncate">{event.title}</p>
                                        <div className="flex items-center gap-2 mt-1 text-2xs text-gray-500">
                                            <Clock size={10} />
                                            <span>{formatDate(event.date)}</span>
                                            {event.time && <span>• {event.time}</span>}
                                            <span>• {event.country}</span>
                                        </div>
                                    </div>
                                    <Badge variant={getImpactColor(event.impact) as any} size="sm">
                                        {event.impact}
                                    </Badge>
                                </div>
                            </div>
                        ))}
                    </div>
                ) : (
                    <div className="p-8 text-center text-gray-500 text-sm">
                        <Calendar className="w-8 h-8 mx-auto mb-2 opacity-50" />
                        No upcoming events
                    </div>
                )}
            </div>
        </Card>
    );
}
