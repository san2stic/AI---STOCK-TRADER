'use client';

import { useState, useEffect } from 'react';
import { Bitcoin, TrendingUp, Sparkles, Zap, Lock } from 'lucide-react';

export default function TradingModeControl() {
    const [mode, setMode] = useState<string>('AUTO');
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        fetchMode();
    }, []);

    const fetchMode = async () => {
        try {
            const res = await fetch('/api/settings/trading-mode');
            if (res.ok) {
                const data = await res.json();
                setMode(data.mode);
            }
        } catch (error) {
            console.error('Failed to fetch trading mode:', error);
        }
    };

    const updateMode = async (newMode: string) => {
        setLoading(true);
        try {
            const res = await fetch('/api/settings/trading-mode', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ mode: newMode }),
            });

            if (res.ok) {
                const data = await res.json();
                setMode(data.mode);
            }
        } catch (error) {
            console.error('Failed to update trading mode:', error);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="glass-panel rounded-3xl p-6 border border-surface-border shadow-2xl mb-8 relative overflow-hidden">
            <div className="absolute top-0 right-0 w-64 h-64 bg-primary/5 blur-[100px] rounded-full pointer-events-none" />

            <div className="flex flex-col md:flex-row items-center justify-between gap-6 relative z-10">
                <div className="flex items-center gap-4">
                    <div className={`p-3 rounded-xl border border-surface-border ${mode === 'AUTO' ? 'bg-secondary/20 text-secondary shadow-[0_0_15px_rgba(112,0,255,0.3)]' :
                            mode === 'CRYPTO' ? 'bg-orange-500/20 text-orange-400' :
                                'bg-primary/20 text-primary shadow-[0_0_15px_rgba(0,240,255,0.3)]'
                        }`}>
                        {mode === 'AUTO' && <Sparkles className="w-8 h-8 animate-pulse" />}
                        {mode === 'CRYPTO' && <Bitcoin className="w-8 h-8" />}
                        {mode === 'STOCK' && <TrendingUp className="w-8 h-8" />}
                    </div>
                    <div>
                        <h2 className="text-2xl font-bold text-white flex items-center gap-2">
                            Mode de Trading
                            {loading && <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-primary"></div>}
                        </h2>
                        <p className="text-gray-400 text-sm">
                            {mode === 'AUTO' && "Intelligence Hybride Active"}
                            {mode === 'STOCK' && "Marchés Boursiers Uniquement"}
                            {mode === 'CRYPTO' && "Crypto-Actifs Uniquement"}
                        </p>
                    </div>
                </div>

                <div className="flex items-center bg-surface-active/50 p-1.5 rounded-2xl border border-surface-border">
                    <button
                        onClick={() => updateMode('STOCK')}
                        disabled={loading}
                        className={`relative px-6 py-3 rounded-xl font-bold text-sm transition-all duration-300 flex items-center gap-2 ${mode === 'STOCK'
                            ? 'bg-primary text-background shadow-neon-blue'
                            : 'text-gray-400 hover:text-white hover:bg-white/5'
                            }`}
                    >
                        <TrendingUp className="w-4 h-4" />
                        STOCKS
                    </button>

                    <button
                        onClick={() => updateMode('AUTO')}
                        disabled={loading}
                        className={`relative px-6 py-3 rounded-xl font-bold text-sm transition-all duration-300 flex items-center gap-2 ${mode === 'AUTO'
                            ? 'bg-secondary text-white shadow-neon-purple z-10'
                            : 'text-gray-400 hover:text-white hover:bg-white/5'
                            }`}
                    >
                        <Sparkles className="w-4 h-4" />
                        AUTO
                    </button>

                    <button
                        onClick={() => updateMode('CRYPTO')}
                        disabled={loading}
                        className={`relative px-6 py-3 rounded-xl font-bold text-sm transition-all duration-300 flex items-center gap-2 ${mode === 'CRYPTO'
                            ? 'bg-orange-500 text-white shadow-[0_0_15px_rgba(249,115,22,0.4)]'
                            : 'text-gray-400 hover:text-white hover:bg-white/5'
                            }`}
                    >
                        <Bitcoin className="w-4 h-4" />
                        CRYPTO
                    </button>
                </div>
            </div>
        </div>
    );
}
