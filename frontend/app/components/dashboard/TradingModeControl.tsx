'use client';

import { useState, useEffect } from 'react';
import { Settings, Zap, TrendingUp, Bitcoin } from 'lucide-react';
import Card from '../ui/Card';
import Button from '../ui/Button';

type TradingMode = 'AUTO' | 'STOCK' | 'CRYPTO';

export default function TradingModeControl() {
    const [mode, setMode] = useState<TradingMode>('AUTO');
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        const fetchMode = async () => {
            try {
                const res = await fetch('/api/settings/trading-mode');
                if (res.ok) {
                    const data = await res.json();
                    setMode(data.mode || 'AUTO');
                }
            } catch (error) {
                console.error('Failed to fetch trading mode:', error);
            }
        };
        fetchMode();
    }, []);

    const handleModeChange = async (newMode: TradingMode) => {
        setLoading(true);
        try {
            const res = await fetch('/api/settings/trading-mode', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ mode: newMode }),
            });
            if (res.ok) {
                setMode(newMode);
            }
        } catch (error) {
            console.error('Failed to update trading mode:', error);
        } finally {
            setLoading(false);
        }
    };

    const modes = [
        {
            id: 'AUTO' as TradingMode,
            label: 'Auto',
            description: 'Smart switching',
            icon: Zap,
            color: 'primary',
        },
        {
            id: 'STOCK' as TradingMode,
            label: 'Stocks',
            description: 'Market hours',
            icon: TrendingUp,
            color: 'success',
        },
        {
            id: 'CRYPTO' as TradingMode,
            label: 'Crypto',
            description: '24/7 trading',
            icon: Bitcoin,
            color: 'warning',
        },
    ];

    return (
        <Card variant="glass">
            <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 rounded-xl bg-primary/20 flex items-center justify-center">
                    <Settings className="w-5 h-5 text-primary" />
                </div>
                <div>
                    <h3 className="font-bold text-white">Trading Mode</h3>
                    <p className="text-xs text-gray-500">Select asset type focus</p>
                </div>
            </div>

            <div className="grid grid-cols-3 gap-2">
                {modes.map((m) => {
                    const Icon = m.icon;
                    const isActive = mode === m.id;

                    return (
                        <button
                            key={m.id}
                            onClick={() => handleModeChange(m.id)}
                            disabled={loading}
                            className={`relative p-4 rounded-xl border transition-all duration-200 ${isActive
                                    ? `border-${m.color} bg-${m.color}/10 shadow-glow-${m.color}`
                                    : 'border-surface-border bg-surface-elevated/50 hover:border-gray-600'
                                } ${loading ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
                        >
                            <div className="flex flex-col items-center gap-2">
                                <Icon
                                    className={`w-6 h-6 ${isActive ? `text-${m.color}` : 'text-gray-400'
                                        }`}
                                    style={{
                                        color: isActive
                                            ? m.color === 'primary'
                                                ? '#06b6d4'
                                                : m.color === 'success'
                                                    ? '#10b981'
                                                    : '#f59e0b'
                                            : undefined,
                                    }}
                                />
                                <span
                                    className={`font-semibold text-sm ${isActive ? 'text-white' : 'text-gray-400'
                                        }`}
                                >
                                    {m.label}
                                </span>
                                <span className="text-2xs text-gray-500">{m.description}</span>
                            </div>

                            {isActive && (
                                <div className="absolute top-2 right-2 w-2 h-2 rounded-full bg-success animate-pulse" />
                            )}
                        </button>
                    );
                })}
            </div>
        </Card>
    );
}
