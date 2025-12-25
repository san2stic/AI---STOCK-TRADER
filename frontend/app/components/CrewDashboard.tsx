'use client';

import { useEffect, useState } from 'react';
import { Users, MessageSquare, Vote, Clock, CheckCircle, XCircle, AlertCircle } from 'lucide-react';

interface CrewSession {
    session_id: string;
    status: string;
    final_decision: string;
    final_symbol: string;
    consensus_score: number;
    total_messages: number;
    mediator_used: boolean;
    started_at: string;
    completed_at: string;
    duration_seconds: number;
}

interface AgentMessage {
    message_id: string;
    agent_name: string;
    round_number: number;
    message_type: string;
    content: string;
    proposed_action: string;
    proposed_symbol: string;
    confidence_level: number;
    created_at: string;
}

interface CrewVote {
    vote_id: string;
    agent_name: string;
    vote_action: string;
    vote_symbol: string;
    vote_weight: number;
    confidence_level: number;
    reasoning: string;
}

interface SessionDetails {
    session: CrewSession;
    messages: AgentMessage[];
    votes: CrewVote[];
}

export default function CrewDashboard() {
    const [sessions, setSessions] = useState<CrewSession[]>([]);
    const [selectedSession, setSelectedSession] = useState<SessionDetails | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetchSessions();
    }, []);

    const fetchSessions = async () => {
        try {
            const res = await fetch('/api/crew/sessions');
            const data = await res.json();
            setSessions(data.sessions || []);
            setLoading(false);
        } catch (error) {
            console.error('Failed to fetch crew sessions:', error);
            setLoading(false);
        }
    };

    const fetchSessionDetails = async (sessionId: string) => {
        try {
            const res = await fetch(`/api/crew/sessions/${sessionId}`);
            const data = await res.json();
            setSelectedSession(data);
        } catch (error) {
            console.error('Failed to fetch session details:', error);
        }
    };

    const getStatusIcon = (status: string) => {
        switch (status?.toLowerCase()) {
            case 'completed':
                return <CheckCircle className="w-5 h-5 text-green-400" />;
            case 'in_progress':
                return <Clock className="w-5 h-5 text-yellow-400 animate-pulse" />;
            case 'failed':
                return <XCircle className="w-5 h-5 text-red-400" />;
            default:
                return <AlertCircle className="w-5 h-5 text-gray-400" />;
        }
    };

    const getConsensusColor = (score: number) => {
        if (score >= 75) return 'text-green-400';
        if (score >= 50) return 'text-yellow-400';
        return 'text-red-400';
    };

    const formatDuration = (seconds: number) => {
        const mins = Math.floor(seconds / 60);
        const secs = seconds % 60;
        return `${mins}m ${secs}s`;
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center py-12">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-cyan-500"></div>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            {/* Stats Overview */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="bg-gradient-to-br from-blue-500/20 to-cyan-500/20 backdrop-blur-sm rounded-xl p-6 border border-blue-500/30">
                    <div className="flex items-center gap-3 mb-2">
                        <Users className="w-6 h-6 text-blue-400" />
                        <span className="text-gray-300">Sessions Totales</span>
                    </div>
                    <div className="text-3xl font-bold text-white">{sessions.length}</div>
                </div>

                <div className="bg-gradient-to-br from-green-500/20 to-emerald-500/20 backdrop-blur-sm rounded-xl p-6 border border-green-500/30">
                    <div className="flex items-center gap-3 mb-2">
                        <CheckCircle className="w-6 h-6 text-green-400" />
                        <span className="text-gray-300">Consensus Atteint</span>
                    </div>
                    <div className="text-3xl font-bold text-white">
                        {sessions.filter(s => s.consensus_score >= 66).length}
                    </div>
                </div>

                <div className="bg-gradient-to-br from-purple-500/20 to-pink-500/20 backdrop-blur-sm rounded-xl p-6 border border-purple-500/30">
                    <div className="flex items-center gap-3 mb-2">
                        <MessageSquare className="w-6 h-6 text-purple-400" />
                        <span className="text-gray-300">Messages Totaux</span>
                    </div>
                    <div className="text-3xl font-bold text-white">
                        {sessions.reduce((sum, s) => sum + (s.total_messages || 0), 0)}
                    </div>
                </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Sessions List */}
                <div className="bg-white/5 backdrop-blur-lg rounded-2xl p-6 border border-white/10">
                    <h3 className="text-2xl font-bold text-white mb-4 flex items-center gap-2">
                        <Users className="w-6 h-6" />
                        Sessions Récentes
                    </h3>

                    <div className="space-y-3 max-h-[600px] overflow-y-auto custom-scrollbar pr-2">
                        {sessions.length === 0 ? (
                            <div className="text-center py-8 text-gray-400">
                                Aucune session de délibération
                            </div>
                        ) : (
                            sessions.map(session => (
                                <button
                                    key={session.session_id}
                                    onClick={() => fetchSessionDetails(session.session_id)}
                                    className={`w-full text-left bg-white/5 hover:bg-white/10 rounded-lg p-4 border transition-all ${selectedSession?.session.session_id === session.session_id
                                            ? 'border-cyan-500 bg-cyan-500/10'
                                            : 'border-white/10'
                                        }`}
                                >
                                    <div className="flex items-start justify-between mb-2">
                                        <div className="flex items-center gap-2">
                                            {getStatusIcon(session.status)}
                                            <span className="font-semibold text-white">
                                                {session.final_symbol || 'No symbol'}
                                            </span>
                                        </div>
                                        <span className="text-xs text-gray-400">
                                            {new Date(session.started_at).toLocaleString('fr-FR', {
                                                month: 'short',
                                                day: 'numeric',
                                                hour: '2-digit',
                                                minute: '2-digit'
                                            })}
                                        </span>
                                    </div>

                                    <div className="grid grid-cols-2 gap-2 text-sm">
                                        <div className="text-gray-400">
                                            Consensus:{' '}
                                            <span className={`font-semibold ${getConsensusColor(session.consensus_score)}`}>
                                                {session.consensus_score?.toFixed(0)}%
                                            </span>
                                        </div>
                                        <div className="text-gray-400">
                                            Messages: <span className="text-white">{session.total_messages}</span>
                                        </div>
                                        <div className="text-gray-400">
                                            Décision: <span className="text-white">{session.final_decision || 'N/A'}</span>
                                        </div>
                                        <div className="text-gray-400">
                                            Durée: <span className="text-white">{formatDuration(session.duration_seconds)}</span>
                                        </div>
                                    </div>

                                    {session.mediator_used && (
                                        <div className="mt-2 text-xs bg-yellow-500/10 text-yellow-400 px-2 py-1 rounded inline-block">
                                            Médiateur utilisé
                                        </div>
                                    )}
                                </button>
                            ))
                        )}
                    </div>
                </div>

                {/* Session Details */}
                <div className="bg-white/5 backdrop-blur-lg rounded-2xl p-6 border border-white/10">
                    <h3 className="text-2xl font-bold text-white mb-4 flex items-center gap-2">
                        <MessageSquare className="w-6 h-6" />
                        Détails de la Session
                    </h3>

                    {!selectedSession ? (
                        <div className="text-center py-12 text-gray-400">
                            Sélectionnez une session pour voir les détails
                        </div>
                    ) : (
                        <div className="space-y-6">
                            {/* Consensus Meter */}
                            <div className="bg-white/5 rounded-lg p-4">
                                <div className="flex items-center justify-between mb-2">
                                    <span className="text-sm text-gray-300">Niveau de Consensus</span>
                                    <span className={`text-xl font-bold ${getConsensusColor(selectedSession.session.consensus_score)}`}>
                                        {selectedSession.session.consensus_score?.toFixed(0)}%
                                    </span>
                                </div>
                                <div className="w-full bg-gray-700 rounded-full h-3 overflow-hidden">
                                    <div
                                        className={`h-full transition-all duration-500 ${selectedSession.session.consensus_score >= 75
                                                ? 'bg-green-500'
                                                : selectedSession.session.consensus_score >= 50
                                                    ? 'bg-yellow-500'
                                                    : 'bg-red-500'
                                            }`}
                                        style={{ width: `${selectedSession.session.consensus_score}%` }}
                                    />
                                </div>
                            </div>

                            {/* Messages Thread */}
                            <div className="space-y-3 max-h-[400px] overflow-y-auto custom-scrollbar pr-2">
                                <h4 className="text-lg font-semibold text-white flex items-center gap-2">
                                    <MessageSquare className="w-5 h-5" />
                                    Messages ({selectedSession.messages.length})
                                </h4>

                                {selectedSession.messages.map((msg, idx) => (
                                    <div
                                        key={msg.message_id}
                                        className="bg-white/5 rounded-lg p-3 border border-white/10 hover:border-cyan-500/30 transition-colors"
                                    >
                                        <div className="flex items-center justify-between mb-2">
                                            <span className="font-semibold text-cyan-400 text-sm">
                                                {msg.agent_name}
                                            </span>
                                            <div className="flex items-center gap-2">
                                                <span className="text-xs bg-white/10 px-2 py-1 rounded text-gray-300">
                                                    Round {msg.round_number}
                                                </span>
                                                <span className="text-xs text-gray-400">
                                                    Confiance: {msg.confidence_level}%
                                                </span>
                                            </div>
                                        </div>
                                        <p className="text-sm text-gray-300 mb-2">{msg.content}</p>
                                        {msg.proposed_action && (
                                            <div className="flex items-center gap-2 text-xs">
                                                <span className="bg-blue-500/20 text-blue-400 px-2 py-1 rounded">
                                                    {msg.proposed_action}
                                                </span>
                                                {msg.proposed_symbol && (
                                                    <span className="bg-purple-500/20 text-purple-400 px-2 py-1 rounded">
                                                        {msg.proposed_symbol}
                                                    </span>
                                                )}
                                            </div>
                                        )}
                                    </div>
                                ))}
                            </div>

                            {/* Votes */}
                            {selectedSession.votes.length > 0 && (
                                <div className="space-y-3">
                                    <h4 className="text-lg font-semibold text-white flex items-center gap-2">
                                        <Vote className="w-5 h-5" />
                                        Votes ({selectedSession.votes.length})
                                    </h4>

                                    {selectedSession.votes.map(vote => (
                                        <div
                                            key={vote.vote_id}
                                            className="bg-white/5 rounded-lg p-3 border border-white/10"
                                        >
                                            <div className="flex items-center justify-between mb-1">
                                                <span className="font-semibold text-white text-sm">
                                                    {vote.agent_name}
                                                </span>
                                                <span className="text-xs text-gray-400">
                                                    Poids: {vote.vote_weight}
                                                </span>
                                            </div>
                                            <div className="flex items-center gap-2 text-xs mb-2">
                                                <span className="bg-green-500/20 text-green-400 px-2 py-1 rounded">
                                                    {vote.vote_action}
                                                </span>
                                                {vote.vote_symbol && (
                                                    <span className="bg-purple-500/20 text-purple-400 px-2 py-1 rounded">
                                                        {vote.vote_symbol}
                                                    </span>
                                                )}
                                            </div>
                                            {vote.reasoning && (
                                                <p className="text-xs text-gray-400 italic">{vote.reasoning}</p>
                                            )}
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
