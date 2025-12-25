'use client';

import { useState, useEffect } from 'react';
import { Users, MessageSquare, Vote, Clock, CheckCircle, XCircle } from 'lucide-react';
import Card from '../ui/Card';
import Badge from '../ui/Badge';

interface CrewSession {
    id: string;
    symbol: string;
    asset_type: string;
    status: 'deliberating' | 'voting' | 'complete';
    rounds_completed: number;
    participants: string[];
    votes: Record<string, string>;
    final_decision: string | null;
    created_at: string;
}

export default function CrewDashboard() {
    const [sessions, setSessions] = useState<CrewSession[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchSessions = async () => {
            try {
                const res = await fetch('/api/crew/sessions?limit=10');
                if (res.ok) {
                    const data = await res.json();
                    setSessions(data.sessions || []);
                }
            } catch (error) {
                console.error('Failed to fetch crew sessions:', error);
            } finally {
                setLoading(false);
            }
        };
        fetchSessions();
        const interval = setInterval(fetchSessions, 30000);
        return () => clearInterval(interval);
    }, []);

    const getStatusBadge = (status: string) => {
        switch (status) {
            case 'deliberating':
                return { variant: 'warning' as const, label: 'Deliberating' };
            case 'voting':
                return { variant: 'info' as const, label: 'Voting' };
            case 'complete':
                return { variant: 'success' as const, label: 'Complete' };
            default:
                return { variant: 'neutral' as const, label: status };
        }
    };

    return (
        <Card variant="glass" padding="none" className="h-full min-h-[60vh]">
            {/* Header */}
            <div className="p-6 border-b border-surface-border">
                <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-secondary/20 flex items-center justify-center">
                        <Users className="w-5 h-5 text-secondary" />
                    </div>
                    <div>
                        <h3 className="font-bold text-white">Crew Deliberations</h3>
                        <p className="text-xs text-gray-500">Agent consensus sessions</p>
                    </div>
                </div>
            </div>

            {/* Sessions List */}
            <div className="p-6">
                {loading ? (
                    <div className="space-y-4">
                        {[1, 2, 3].map((i) => (
                            <div key={i} className="h-24 bg-surface-elevated animate-pulse rounded-xl" />
                        ))}
                    </div>
                ) : sessions.length > 0 ? (
                    <div className="space-y-4">
                        {sessions.map((session) => {
                            const badge = getStatusBadge(session.status);
                            const totalVotes = Object.keys(session.votes || {}).length;
                            const buyVotes = Object.values(session.votes || {}).filter((v) => v === 'BUY').length;
                            const sellVotes = Object.values(session.votes || {}).filter((v) => v === 'SELL').length;
                            const holdVotes = totalVotes - buyVotes - sellVotes;

                            return (
                                <div
                                    key={session.id}
                                    className="bg-surface-elevated/50 rounded-xl p-4 border border-surface-border hover:border-primary/30 transition-colors"
                                >
                                    <div className="flex items-center justify-between mb-3">
                                        <div className="flex items-center gap-3">
                                            <span className="font-mono font-bold text-white text-lg">
                                                {session.symbol}
                                            </span>
                                            <Badge variant={session.asset_type === 'crypto' ? 'purple' : 'info'} size="sm">
                                                {session.asset_type?.toUpperCase() || 'STOCK'}
                                            </Badge>
                                            <Badge variant={badge.variant} size="sm">
                                                {badge.label}
                                            </Badge>
                                        </div>
                                        <span className="text-xs text-gray-500">
                                            {new Date(session.created_at).toLocaleString()}
                                        </span>
                                    </div>

                                    {/* Participants */}
                                    <div className="flex items-center gap-2 mb-3">
                                        <Users size={14} className="text-gray-500" />
                                        <div className="flex gap-1 flex-wrap">
                                            {session.participants?.map((p) => (
                                                <span
                                                    key={p}
                                                    className="px-2 py-0.5 bg-surface rounded text-2xs text-gray-400"
                                                >
                                                    {p}
                                                </span>
                                            ))}
                                        </div>
                                    </div>

                                    {/* Votes */}
                                    {totalVotes > 0 && (
                                        <div className="flex items-center gap-4 mb-3">
                                            <div className="flex items-center gap-2">
                                                <Vote size={14} className="text-gray-500" />
                                                <span className="text-xs text-gray-500">Votes:</span>
                                            </div>
                                            <div className="flex gap-3">
                                                <span className="text-xs text-success flex items-center gap-1">
                                                    <CheckCircle size={12} />
                                                    BUY: {buyVotes}
                                                </span>
                                                <span className="text-xs text-danger flex items-center gap-1">
                                                    <XCircle size={12} />
                                                    SELL: {sellVotes}
                                                </span>
                                                <span className="text-xs text-gray-400">HOLD: {holdVotes}</span>
                                            </div>
                                        </div>
                                    )}

                                    {/* Final Decision */}
                                    {session.final_decision && (
                                        <div className="pt-3 border-t border-surface-border">
                                            <span className="text-xs text-gray-500">Final Decision: </span>
                                            <Badge
                                                variant={
                                                    session.final_decision === 'BUY'
                                                        ? 'success'
                                                        : session.final_decision === 'SELL'
                                                            ? 'danger'
                                                            : 'neutral'
                                                }
                                            >
                                                {session.final_decision}
                                            </Badge>
                                        </div>
                                    )}
                                </div>
                            );
                        })}
                    </div>
                ) : (
                    <div className="flex flex-col items-center justify-center py-12 text-gray-500">
                        <Users className="w-12 h-12 mb-4 opacity-30" />
                        <p className="text-lg font-medium">No Active Sessions</p>
                        <p className="text-sm">Crew deliberations will appear here</p>
                    </div>
                )}
            </div>
        </Card>
    );
}
