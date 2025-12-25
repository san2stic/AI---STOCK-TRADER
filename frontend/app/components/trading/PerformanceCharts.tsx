'use client';

import { useState, useEffect } from 'react';
import { LineChart, Line, AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, BarChart, Bar } from 'recharts';
import { BarChart3, TrendingUp, PieChart } from 'lucide-react';
import Card from '../ui/Card';

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

// Agent colors for charts
const AGENT_COLORS: Record<string, string> = {
    Titan: '#3b82f6',
    Nexus: '#8b5cf6',
    Viper: '#ef4444',
    Aegis: '#06b6d4',
    Surge: '#f59e0b',
    Ranger: '#10b981',
    Oracle: '#6366f1',
    Sentinel: '#6b7280',
    Cipher: '#ec4899',
    Warden: '#14b8a6',
};

export default function PerformanceCharts({ agents }: PerformanceChartsProps) {
    const [activeChart, setActiveChart] = useState<'pnl' | 'winrate' | 'trades'>('pnl');

    // Prepare chart data
    const pnlData = agents.map((agent) => ({
        name: agent.name,
        pnl: agent.pnl,
        pnl_percent: agent.pnl_percent,
        color: AGENT_COLORS[agent.name] || '#6b7280',
    }));

    const winRateData = agents.map((agent) => ({
        name: agent.name,
        winRate: agent.win_rate,
        color: AGENT_COLORS[agent.name] || '#6b7280',
    }));

    const tradesData = agents.map((agent) => ({
        name: agent.name,
        trades: agent.total_trades,
        color: AGENT_COLORS[agent.name] || '#6b7280',
    }));

    const CustomTooltip = ({ active, payload, label }: any) => {
        if (active && payload && payload.length) {
            return (
                <div className="bg-surface border border-surface-border rounded-lg p-3 shadow-lg">
                    <p className="text-white font-semibold mb-1">{label}</p>
                    {payload.map((entry: any, index: number) => (
                        <p key={index} className="text-sm" style={{ color: entry.color }}>
                            {entry.name}: {entry.value?.toFixed?.(2) || entry.value}
                            {entry.name === 'pnl' && '%'}
                        </p>
                    ))}
                </div>
            );
        }
        return null;
    };

    const charts = [
        { id: 'pnl', label: 'P&L %', icon: TrendingUp },
        { id: 'winrate', label: 'Win Rate', icon: PieChart },
        { id: 'trades', label: 'Total Trades', icon: BarChart3 },
    ];

    return (
        <Card variant="glass" padding="none" className="h-full">
            {/* Header */}
            <div className="p-6 border-b border-surface-border">
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-xl bg-primary/20 flex items-center justify-center">
                            <BarChart3 className="w-5 h-5 text-primary" />
                        </div>
                        <div>
                            <h3 className="font-bold text-white">Performance Analytics</h3>
                            <p className="text-xs text-gray-500">Agent comparison charts</p>
                        </div>
                    </div>

                    {/* Chart selector */}
                    <div className="flex bg-surface-elevated rounded-lg p-1">
                        {charts.map((chart) => {
                            const Icon = chart.icon;
                            return (
                                <button
                                    key={chart.id}
                                    onClick={() => setActiveChart(chart.id as any)}
                                    className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${activeChart === chart.id
                                            ? 'bg-primary text-white'
                                            : 'text-gray-400 hover:text-white'
                                        }`}
                                >
                                    <Icon size={14} />
                                    {chart.label}
                                </button>
                            );
                        })}
                    </div>
                </div>
            </div>

            {/* Chart */}
            <div className="p-6">
                <div className="h-80">
                    <ResponsiveContainer width="100%" height="100%">
                        {activeChart === 'pnl' ? (
                            <BarChart data={pnlData} layout="vertical">
                                <XAxis type="number" stroke="#6b7280" fontSize={12} />
                                <YAxis dataKey="name" type="category" stroke="#6b7280" fontSize={12} width={80} />
                                <Tooltip content={<CustomTooltip />} />
                                <Bar
                                    dataKey="pnl_percent"
                                    name="P&L %"
                                    radius={[0, 4, 4, 0]}
                                    fill="#06b6d4"
                                >
                                    {pnlData.map((entry, index) => (
                                        <rect
                                            key={`cell-${index}`}
                                            fill={entry.pnl_percent >= 0 ? '#10b981' : '#f43f5e'}
                                        />
                                    ))}
                                </Bar>
                            </BarChart>
                        ) : activeChart === 'winrate' ? (
                            <BarChart data={winRateData} layout="vertical">
                                <XAxis type="number" domain={[0, 100]} stroke="#6b7280" fontSize={12} />
                                <YAxis dataKey="name" type="category" stroke="#6b7280" fontSize={12} width={80} />
                                <Tooltip content={<CustomTooltip />} />
                                <Bar
                                    dataKey="winRate"
                                    name="Win Rate"
                                    radius={[0, 4, 4, 0]}
                                >
                                    {winRateData.map((entry, index) => (
                                        <rect
                                            key={`cell-${index}`}
                                            fill={entry.winRate >= 50 ? '#10b981' : '#f59e0b'}
                                        />
                                    ))}
                                </Bar>
                            </BarChart>
                        ) : (
                            <BarChart data={tradesData} layout="vertical">
                                <XAxis type="number" stroke="#6b7280" fontSize={12} />
                                <YAxis dataKey="name" type="category" stroke="#6b7280" fontSize={12} width={80} />
                                <Tooltip content={<CustomTooltip />} />
                                <Bar dataKey="trades" name="Trades" fill="#8b5cf6" radius={[0, 4, 4, 0]} />
                            </BarChart>
                        )}
                    </ResponsiveContainer>
                </div>
            </div>

            {/* Legend */}
            <div className="px-6 pb-6">
                <div className="flex flex-wrap gap-4 justify-center">
                    {agents.slice(0, 6).map((agent) => (
                        <div key={agent.name} className="flex items-center gap-2">
                            <div
                                className="w-3 h-3 rounded-full"
                                style={{ backgroundColor: AGENT_COLORS[agent.name] || '#6b7280' }}
                            />
                            <span className="text-xs text-gray-400">{agent.name}</span>
                        </div>
                    ))}
                </div>
            </div>
        </Card>
    );
}
