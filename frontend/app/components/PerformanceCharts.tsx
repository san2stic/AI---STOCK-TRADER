'use client';

import {
    LineChart, Line, BarChart, Bar, AreaChart, Area,
    XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell
} from 'recharts';
import { TrendingUp, TrendingDown, Activity, BarChart3, Wallet } from 'lucide-react';

interface Agent {
    name: string;
    total_value: number;
    pnl: number;
    pnl_percent: number;
    total_trades: number;
    win_rate: number;
}

interface PerformanceChartsProps {
    agents: Agent[];
}

export default function PerformanceCharts({ agents }: PerformanceChartsProps) {
    // Prepare data
    const pnlData = agents.map(agent => ({
        name: agent.name.split(' ')[0],
        pnl: agent.pnl_percent,
        value: agent.total_value,
    }));

    const winRateData = agents.map(agent => ({
        name: agent.name.split(' ')[0],
        winRate: agent.win_rate,
        fill: agent.win_rate >= 60 ? '#00E676' : agent.win_rate >= 40 ? '#FFEA00' : '#FF1744',
    }));

    const tradesData = agents.map(agent => ({
        name: agent.name.split(' ')[0],
        trades: agent.total_trades,
    }));

    // Mock historical data simulation
    const historicalData = Array.from({ length: 24 }, (_, i) => {
        const hour = i;
        const data: any = { hour: `${hour}h` };
        agents.forEach(agent => {
            // Deterministic pseudo-random for stable visualization
            const seed = agent.name.length + i;
            const variance = Math.sin(seed) * 2;
            data[agent.name.split(' ')[0]] = agent.total_value * (1 + variance * 0.005);
        });
        return data;
    });

    const CustomTooltip = ({ active, payload, label }: any) => {
        if (active && payload && payload.length) {
            return (
                <div className="bg-surface/95 backdrop-blur-xl border border-primary/20 rounded-xl p-4 shadow-[0_0_20px_rgba(0,0,0,0.5)]">
                    <p className="text-gray-400 text-xs font-mono mb-2 border-b border-surface-border pb-1">{label}</p>
                    {payload.map((entry: any, index: number) => (
                        <div key={index} className="flex items-center gap-2 text-sm mb-1">
                            <span
                                className="w-2 h-2 rounded-full"
                                style={{ backgroundColor: entry.color || entry.fill }}
                            />
                            <span className="text-gray-300">{entry.name}:</span>
                            <span className="font-mono text-white font-medium">
                                {typeof entry.value === 'number' ? entry.value.toFixed(2) : entry.value}
                            </span>
                        </div>
                    ))}
                </div>
            );
        }
        return null;
    };

    const totalPnL = agents.reduce((sum, agent) => sum + (agent.pnl || 0), 0);
    const avgWinRate = agents.reduce((sum, agent) => sum + agent.win_rate, 0) / (agents.length || 1);
    const totalTrades = agents.reduce((sum, agent) => sum + agent.total_trades, 0);
    const totalValue = agents.reduce((sum, agent) => sum + agent.total_value, 0);

    return (
        <div className="space-y-8 animate-fade-in-up">
            {/* Summary Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                <div className="glass-panel p-6 border-l-4 border-l-primary hover:-translate-y-1 transition-transform">
                    <div className="flex items-center justify-between mb-4">
                        <span className="text-gray-400 text-sm font-medium tracking-wide">VALEUR TOTALE</span>
                        <div className="p-2 bg-primary/10 rounded-lg">
                            <Wallet className="w-5 h-5 text-primary" />
                        </div>
                    </div>
                    <div className="text-3xl font-bold text-white font-mono tracking-tight">
                        ${totalValue.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}
                    </div>
                </div>

                <div className={`glass-panel p-6 border-l-4 hover:-translate-y-1 transition-transform ${totalPnL >= 0 ? 'border-l-status-success' : 'border-l-status-error'}`}>
                    <div className="flex items-center justify-between mb-4">
                        <span className="text-gray-400 text-sm font-medium tracking-wide">P&L GLOBAL</span>
                        <div className={`p-2 rounded-lg ${totalPnL >= 0 ? 'bg-status-success/10' : 'bg-status-error/10'}`}>
                            {totalPnL >= 0 ? <TrendingUp className="w-5 h-5 text-status-success" /> : <TrendingDown className="w-5 h-5 text-status-error" />}
                        </div>
                    </div>
                    <div className={`text-3xl font-bold font-mono tracking-tight ${totalPnL >= 0 ? 'text-status-success drop-shadow-[0_0_8px_rgba(0,230,118,0.5)]' : 'text-status-error'}`}>
                        {totalPnL >= 0 ? '+' : ''}${Math.abs(totalPnL).toFixed(2)}
                    </div>
                </div>

                <div className="glass-panel p-6 border-l-4 border-l-secondary hover:-translate-y-1 transition-transform">
                    <div className="flex items-center justify-between mb-4">
                        <span className="text-gray-400 text-sm font-medium tracking-wide">TAUX SUCCÈS</span>
                        <div className="p-2 bg-secondary/10 rounded-lg">
                            <Activity className="w-5 h-5 text-secondary" />
                        </div>
                    </div>
                    <div className="text-3xl font-bold text-white font-mono tracking-tight">
                        {avgWinRate.toFixed(1)}%
                    </div>
                </div>

                <div className="glass-panel p-6 border-l-4 border-l-accent-yellow hover:-translate-y-1 transition-transform">
                    <div className="flex items-center justify-between mb-4">
                        <span className="text-gray-400 text-sm font-medium tracking-wide">VOLUME TRADES</span>
                        <div className="p-2 bg-accent-yellow/10 rounded-lg">
                            <BarChart3 className="w-5 h-5 text-accent-yellow" />
                        </div>
                    </div>
                    <div className="text-3xl font-bold text-white font-mono tracking-tight">
                        {totalTrades}
                    </div>
                </div>
            </div>

            {/* Charts Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                {/* Portfolio Value Over Time */}
                <div className="glass-panel p-6">
                    <h3 className="text-lg font-bold text-white mb-6 flex items-center gap-2">
                        <span className="w-1 h-6 bg-primary rounded-full shadow-neon-blue" />
                        Évolution du Portfolio (24h)
                    </h3>
                    <div className="h-[350px] w-full">
                        <ResponsiveContainer width="100%" height="100%">
                            <LineChart data={historicalData} margin={{ top: 5, right: 30, left: 10, bottom: 5 }}>
                                <CartesianGrid strokeDasharray="3 3" stroke="#ffffff08" vertical={false} />
                                <XAxis
                                    dataKey="hour"
                                    stroke="#525252"
                                    tick={{ fill: '#737373', fontSize: 12 }}
                                    axisLine={false}
                                    tickLine={false}
                                />
                                <YAxis
                                    stroke="#525252"
                                    tick={{ fill: '#737373', fontSize: 12 }}
                                    axisLine={false}
                                    tickLine={false}
                                    tickFormatter={(value) => `$${value}`}
                                    width={60}
                                />
                                <Tooltip content={<CustomTooltip />} />
                                {agents.map((agent, idx) => (
                                    <Line
                                        key={agent.name}
                                        type="monotone"
                                        dataKey={agent.name.split(' ')[0]}
                                        stroke={`hsl(${200 + idx * 30}, 80%, 60%)`}
                                        strokeWidth={3}
                                        dot={false}
                                        activeDot={{ r: 6, strokeWidth: 0, fill: '#fff' }}
                                    />
                                ))}
                            </LineChart>
                        </ResponsiveContainer>
                    </div>
                </div>

                {/* P&L Comparison */}
                <div className="glass-panel p-6">
                    <h3 className="text-lg font-bold text-white mb-6 flex items-center gap-2">
                        <span className="w-1 h-6 bg-status-success rounded-full shadow-[0_0_10px_#00E676]" />
                        Performance Relative
                    </h3>
                    <div className="h-[350px] w-full">
                        <ResponsiveContainer width="100%" height="100%">
                            <BarChart data={pnlData} margin={{ top: 5, right: 30, left: 10, bottom: 5 }}>
                                <CartesianGrid strokeDasharray="3 3" stroke="#ffffff08" vertical={false} />
                                <XAxis
                                    dataKey="name"
                                    stroke="#525252"
                                    tick={{ fill: '#737373', fontSize: 12 }}
                                    axisLine={false}
                                    tickLine={false}
                                />
                                <YAxis
                                    stroke="#525252"
                                    tick={{ fill: '#737373', fontSize: 12 }}
                                    axisLine={false}
                                    tickLine={false}
                                    width={60}
                                />
                                <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(255,255,255,0.05)' }} />
                                <Bar dataKey="pnl" radius={[6, 6, 6, 6]} barSize={40}>
                                    {pnlData.map((entry, index) => (
                                        <Cell
                                            key={`cell-${index}`}
                                            fill={entry.pnl >= 0 ? '#00E676' : '#FF1744'}
                                            fillOpacity={0.8}
                                        />
                                    ))}
                                </Bar>
                            </BarChart>
                        </ResponsiveContainer>
                    </div>
                </div>

                {/* Win Rate Visualization */}
                <div className="glass-panel p-6">
                    <h3 className="text-lg font-bold text-white mb-6 flex items-center gap-2">
                        <span className="w-1 h-6 bg-secondary rounded-full shadow-neon-purple" />
                        Taux de Réussite
                    </h3>
                    <div className="h-[300px] w-full">
                        <ResponsiveContainer width="100%" height="100%">
                            <BarChart data={winRateData} layout="vertical" margin={{ top: 5, right: 30, left: 40, bottom: 5 }}>
                                <CartesianGrid strokeDasharray="3 3" stroke="#ffffff08" horizontal={false} />
                                <XAxis type="number" domain={[0, 100]} hide />
                                <YAxis
                                    dataKey="name"
                                    type="category"
                                    stroke="#525252"
                                    tick={{ fill: '#737373', fontSize: 12 }}
                                    axisLine={false}
                                    tickLine={false}
                                    width={80}
                                />
                                <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(255,255,255,0.05)' }} />
                                <Bar dataKey="winRate" radius={[0, 4, 4, 0]} barSize={24}>
                                    {winRateData.map((entry, index) => (
                                        <Cell
                                            key={`cell-${index}`}
                                            fill={entry.fill}
                                        />
                                    ))}
                                </Bar>
                            </BarChart>
                        </ResponsiveContainer>
                    </div>
                </div>

                {/* Trade Volume */}
                <div className="glass-panel p-6">
                    <h3 className="text-lg font-bold text-white mb-6 flex items-center gap-2">
                        <span className="w-1 h-6 bg-accent-yellow rounded-full" />
                        Volume d'Activité
                    </h3>
                    <div className="h-[300px] w-full">
                        <ResponsiveContainer width="100%" height="100%">
                            <AreaChart data={tradesData} margin={{ top: 5, right: 30, left: 10, bottom: 5 }}>
                                <CartesianGrid strokeDasharray="3 3" stroke="#ffffff08" vertical={false} />
                                <XAxis
                                    dataKey="name"
                                    stroke="#525252"
                                    tick={{ fill: '#737373', fontSize: 12 }}
                                    axisLine={false}
                                    tickLine={false}
                                />
                                <YAxis
                                    stroke="#525252"
                                    tick={{ fill: '#737373', fontSize: 12 }}
                                    axisLine={false}
                                    tickLine={false}
                                    width={40}
                                />
                                <Tooltip content={<CustomTooltip />} />
                                <defs>
                                    <linearGradient id="colorTrades" x1="0" y1="0" x2="0" y2="1">
                                        <stop offset="5%" stopColor="#FAFF00" stopOpacity={0.3} />
                                        <stop offset="95%" stopColor="#FAFF00" stopOpacity={0} />
                                    </linearGradient>
                                </defs>
                                <Area
                                    type="monotone"
                                    dataKey="trades"
                                    stroke="#FAFF00"
                                    fill="url(#colorTrades)"
                                    strokeWidth={3}
                                />
                            </AreaChart>
                        </ResponsiveContainer>
                    </div>
                </div>
            </div>
        </div>
    );
}
