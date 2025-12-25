'use client';

import { useEffect, useRef } from 'react';
import { Activity, Bot, TrendingUp, TrendingDown, AlertTriangle, CheckCircle, Info } from 'lucide-react';
import Badge from '../ui/Badge';

interface Message {
    type: string;
    timestamp: string;
    agent?: string;
    data: any;
}

interface LiveMessageFeedProps {
    messages: Message[];
    maxMessages?: number;
}

export default function LiveMessageFeed({ messages, maxMessages = 100 }: LiveMessageFeedProps) {
    const containerRef = useRef<HTMLDivElement>(null);

    // Auto-scroll to top on new messages
    useEffect(() => {
        if (containerRef.current) {
            containerRef.current.scrollTop = 0;
        }
    }, [messages.length]);

    const getMessageIcon = (type: string) => {
        switch (type) {
            case 'trade':
                return <TrendingUp className="w-4 h-4 text-success" />;
            case 'decision':
            case 'agent_decision':
                return <Bot className="w-4 h-4 text-primary" />;
            case 'error':
                return <AlertTriangle className="w-4 h-4 text-danger" />;
            case 'success':
                return <CheckCircle className="w-4 h-4 text-success" />;
            default:
                return <Info className="w-4 h-4 text-gray-400" />;
        }
    };

    const getMessageBadge = (type: string) => {
        switch (type) {
            case 'trade':
                return { variant: 'success' as const, label: 'TRADE' };
            case 'decision':
            case 'agent_decision':
                return { variant: 'info' as const, label: 'DECISION' };
            case 'error':
                return { variant: 'danger' as const, label: 'ERROR' };
            case 'market_data':
                return { variant: 'purple' as const, label: 'MARKET' };
            case 'crew_deliberation':
                return { variant: 'warning' as const, label: 'CREW' };
            default:
                return { variant: 'neutral' as const, label: type.toUpperCase() };
        }
    };

    const formatTimestamp = (timestamp: string) => {
        const date = new Date(timestamp);
        return date.toLocaleTimeString('en-US', {
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
        });
    };

    const renderMessageContent = (message: Message) => {
        const { type, data, agent } = message;

        switch (type) {
            case 'trade':
                return (
                    <div>
                        <span className="font-semibold text-white">{agent || 'System'}</span>
                        <span className="text-gray-400"> executed </span>
                        <span className={data.action === 'BUY' ? 'text-success' : 'text-danger'}>
                            {data.action}
                        </span>
                        <span className="text-gray-400"> of </span>
                        <span className="text-white font-mono">{data.quantity} {data.symbol}</span>
                        <span className="text-gray-400"> @ </span>
                        <span className="text-white font-mono">${data.price?.toFixed(2)}</span>
                    </div>
                );

            case 'decision':
            case 'agent_decision':
                return (
                    <div>
                        <span className="font-semibold text-white">{agent || 'Agent'}</span>
                        <span className="text-gray-400"> decided to </span>
                        <span className="text-primary">{data.action || data.decision || 'analyze'}</span>
                        {data.symbol && (
                            <>
                                <span className="text-gray-400"> for </span>
                                <span className="text-white font-mono">{data.symbol}</span>
                            </>
                        )}
                    </div>
                );

            case 'error':
                return (
                    <div>
                        <span className="text-danger">{data.message || data.error || 'An error occurred'}</span>
                    </div>
                );

            default:
                return (
                    <div className="text-gray-400">
                        {typeof data === 'string' ? data : JSON.stringify(data).slice(0, 100)}
                    </div>
                );
        }
    };

    return (
        <div ref={containerRef} className="h-full overflow-y-auto">
            {messages.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-full text-gray-500">
                    <Activity className="w-12 h-12 mb-4 opacity-30 animate-pulse" />
                    <p className="text-lg font-medium">Waiting for activity...</p>
                    <p className="text-sm">Real-time events will appear here</p>
                </div>
            ) : (
                <div className="divide-y divide-surface-border">
                    {messages.slice(0, maxMessages).map((message, index) => {
                        const badge = getMessageBadge(message.type);
                        return (
                            <div
                                key={`${message.timestamp}-${index}`}
                                className={`p-4 hover:bg-surface-elevated/30 transition-colors ${index === 0 ? 'animate-slide-in' : ''
                                    }`}
                            >
                                <div className="flex items-start gap-3">
                                    <div className="mt-0.5">{getMessageIcon(message.type)}</div>
                                    <div className="flex-1 min-w-0">
                                        <div className="flex items-center gap-2 mb-1">
                                            <Badge variant={badge.variant} size="sm">
                                                {badge.label}
                                            </Badge>
                                            <span className="text-2xs text-gray-500 font-mono">
                                                {formatTimestamp(message.timestamp)}
                                            </span>
                                        </div>
                                        <div className="text-sm">{renderMessageContent(message)}</div>
                                    </div>
                                </div>
                            </div>
                        );
                    })}
                </div>
            )}
        </div>
    );
}
