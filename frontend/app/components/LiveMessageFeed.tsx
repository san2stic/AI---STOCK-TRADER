'use client';

import { useEffect, useRef, useState } from 'react';
import { Search, Filter, X, ChevronDown, ChevronUp } from 'lucide-react';

interface Message {
    type: string;
    timestamp: string;
    agent?: string;
    data: any;
    level?: 'info' | 'success' | 'warning' | 'error';
}

interface LiveMessageFeedProps {
    messages: Message[];
    maxMessages?: number;
}

const MESSAGE_CATEGORIES = {
    trade: { color: 'text-green-400', bg: 'bg-green-500/10', border: 'border-green-500/20' },
    decision: { color: 'text-blue-400', bg: 'bg-blue-500/10', border: 'border-blue-500/20' },
    market_data: { color: 'text-purple-400', bg: 'bg-purple-500/10', border: 'border-purple-500/20' },
    crew: { color: 'text-yellow-400', bg: 'bg-yellow-500/10', border: 'border-yellow-500/20' },
    system: { color: 'text-gray-400', bg: 'bg-gray-500/10', border: 'border-gray-500/20' },
    error: { color: 'text-red-400', bg: 'bg-red-500/10', border: 'border-red-500/20' },
};

export default function LiveMessageFeed({ messages, maxMessages = 100 }: LiveMessageFeedProps) {
    const [filter, setFilter] = useState<string>('all');
    const [searchQuery, setSearchQuery] = useState('');
    const [autoScroll, setAutoScroll] = useState(true);
    const [expandedMessages, setExpandedMessages] = useState<Set<number>>(new Set());
    const messagesEndRef = useRef<HTMLDivElement>(null);
    const containerRef = useRef<HTMLDivElement>(null);

    const scrollToBottom = () => {
        if (autoScroll && messagesEndRef.current) {
            messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
        }
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages, autoScroll]);

    const handleScroll = () => {
        if (!containerRef.current) return;
        const { scrollTop, scrollHeight, clientHeight } = containerRef.current;
        const isAtBottom = scrollHeight - scrollTop - clientHeight < 50;
        setAutoScroll(isAtBottom);
    };

    const getMessageCategory = (type: string): keyof typeof MESSAGE_CATEGORIES => {
        const lowerType = type.toLowerCase();
        if (lowerType.includes('trade') || lowerType.includes('order')) return 'trade';
        if (lowerType.includes('decision')) return 'decision';
        if (lowerType.includes('market') || lowerType.includes('price')) return 'market_data';
        if (lowerType.includes('crew') || lowerType.includes('vote')) return 'crew';
        if (lowerType.includes('error') || lowerType.includes('fail')) return 'error';
        return 'system';
    };

    const filteredMessages = messages
        .filter(msg => {
            if (filter !== 'all' && getMessageCategory(msg.type) !== filter) return false;
            if (searchQuery && !JSON.stringify(msg).toLowerCase().includes(searchQuery.toLowerCase())) return false;
            return true;
        })
        .slice(-maxMessages);

    const toggleExpand = (index: number) => {
        const newExpanded = new Set(expandedMessages);
        if (newExpanded.has(index)) {
            newExpanded.delete(index);
        } else {
            newExpanded.add(index);
        }
        setExpandedMessages(newExpanded);
    };

    const formatTimestamp = (timestamp: string) => {
        try {
            return new Date(timestamp).toLocaleTimeString('fr-FR', {
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit'
            });
        } catch {
            return new Date().toLocaleTimeString('fr-FR');
        }
    };

    return (
        <div className="flex flex-col h-full">
            {/* Header with controls */}
            <div className="flex flex-wrap gap-4 mb-4 items-center">
                <div className="flex-1 min-w-[200px] relative">
                    <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
                    <input
                        type="text"
                        placeholder="Rechercher..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        className="w-full pl-10 pr-4 py-2 bg-white/5 border border-white/10 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:border-cyan-500/50 transition-colors"
                    />
                    {searchQuery && (
                        <button
                            onClick={() => setSearchQuery('')}
                            className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-white transition-colors"
                        >
                            <X className="w-4 h-4" />
                        </button>
                    )}
                </div>

                <div className="flex gap-2 flex-wrap">
                    <button
                        onClick={() => setFilter('all')}
                        className={`px-3 py-1 rounded-lg text-sm font-medium transition-all ${filter === 'all'
                                ? 'bg-cyan-500 text-white'
                                : 'bg-white/5 text-gray-300 hover:bg-white/10'
                            }`}
                    >
                        Tous
                    </button>
                    {Object.keys(MESSAGE_CATEGORIES).map(category => (
                        <button
                            key={category}
                            onClick={() => setFilter(category)}
                            className={`px-3 py-1 rounded-lg text-sm font-medium transition-all ${filter === category
                                    ? `${MESSAGE_CATEGORIES[category as keyof typeof MESSAGE_CATEGORIES].bg} ${MESSAGE_CATEGORIES[category as keyof typeof MESSAGE_CATEGORIES].color} border ${MESSAGE_CATEGORIES[category as keyof typeof MESSAGE_CATEGORIES].border}`
                                    : 'bg-white/5 text-gray-300 hover:bg-white/10'
                                }`}
                        >
                            {category.replace('_', ' ')}
                        </button>
                    ))}
                </div>

                <div className="flex items-center gap-2">
                    <span className="text-sm text-gray-400">Auto-scroll</span>
                    <button
                        onClick={() => setAutoScroll(!autoScroll)}
                        className={`relative w-12 h-6 rounded-full transition-colors ${autoScroll ? 'bg-cyan-500' : 'bg-gray-600'
                            }`}
                    >
                        <div className={`absolute top-1 left-1 w-4 h-4 bg-white rounded-full transition-transform ${autoScroll ? 'translate-x-6' : ''
                            }`} />
                    </button>
                </div>
            </div>

            {/* Messages container */}
            <div
                ref={containerRef}
                onScroll={handleScroll}
                className="flex-1 overflow-y-auto space-y-3 pr-2 custom-scrollbar"
                style={{ maxHeight: '600px' }}
            >
                {filteredMessages.length === 0 ? (
                    <div className="text-center py-12 text-gray-400">
                        <Filter className="w-12 h-12 mx-auto mb-3 opacity-50" />
                        <p>Aucun message trouvé</p>
                    </div>
                ) : (
                    filteredMessages.map((msg, idx) => {
                        const category = getMessageCategory(msg.type);
                        const style = MESSAGE_CATEGORIES[category];
                        const isExpanded = expandedMessages.has(idx);

                        return (
                            <div
                                key={idx}
                                className={`${style.bg} ${style.border} border rounded-lg p-4 transition-all hover:scale-[1.01] animate-slideIn`}
                            >
                                <div className="flex items-start justify-between mb-2">
                                    <div className="flex items-center gap-3">
                                        <span className={`${style.color} font-semibold text-sm uppercase tracking-wide`}>
                                            {msg.type}
                                        </span>
                                        {msg.agent && (
                                            <span className="text-xs bg-white/10 px-2 py-1 rounded text-gray-300">
                                                {msg.agent}
                                            </span>
                                        )}
                                    </div>
                                    <div className="flex items-center gap-2">
                                        <span className="text-xs text-gray-400">
                                            {formatTimestamp(msg.timestamp)}
                                        </span>
                                        <button
                                            onClick={() => toggleExpand(idx)}
                                            className="text-gray-400 hover:text-white transition-colors"
                                        >
                                            {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                                        </button>
                                    </div>
                                </div>

                                {isExpanded ? (
                                    <pre className="text-xs text-gray-300 overflow-x-auto bg-black/20 p-3 rounded mt-2 custom-scrollbar">
                                        {JSON.stringify(msg.data, null, 2)}
                                    </pre>
                                ) : (
                                    <div className="text-sm text-gray-300 line-clamp-2">
                                        {typeof msg.data === 'string'
                                            ? msg.data
                                            : JSON.stringify(msg.data).slice(0, 150) + '...'}
                                    </div>
                                )}
                            </div>
                        );
                    })
                )}
                <div ref={messagesEndRef} />
            </div>

            {/* Stats footer */}
            <div className="mt-4 pt-4 border-t border-white/10 flex justify-between items-center text-sm text-gray-400">
                <span>{filteredMessages.length} message{filteredMessages.length !== 1 ? 's' : ''}</span>
                <span>Total: {messages.length}</span>
            </div>
        </div>
    );
}
