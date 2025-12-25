'use client';

import { useState, useEffect } from 'react';
import { Clock, Zap, RefreshCw } from 'lucide-react';
import Card from '../ui/Card';

interface NextScanData {
    interval_minutes: number;
    interval_hours: number;
    next_scan_utc: string;
    seconds_until_next_scan: number;
    current_time_utc: string;
}

export default function NextScanCountdown() {
    const [data, setData] = useState<NextScanData | null>(null);
    const [countdown, setCountdown] = useState<number>(0);

    useEffect(() => {
        const fetchNextScan = async () => {
            try {
                const res = await fetch('/api/next-scan');
                if (res.ok) {
                    const json = await res.json();
                    setData(json);
                    setCountdown(json.seconds_until_next_scan);
                }
            } catch (error) {
                console.error('Failed to fetch next scan info:', error);
            }
        };

        fetchNextScan();
        const fetchInterval = setInterval(fetchNextScan, 60000); // Refresh every minute

        return () => clearInterval(fetchInterval);
    }, []);

    // Countdown timer
    useEffect(() => {
        if (countdown <= 0) return;

        const timer = setInterval(() => {
            setCountdown((prev) => Math.max(0, prev - 1));
        }, 1000);

        return () => clearInterval(timer);
    }, [countdown]);

    // Format time
    const formatTime = (totalSeconds: number) => {
        const hours = Math.floor(totalSeconds / 3600);
        const minutes = Math.floor((totalSeconds % 3600) / 60);
        const seconds = totalSeconds % 60;

        if (hours > 0) {
            return `${hours}h ${minutes.toString().padStart(2, '0')}m ${seconds
                .toString()
                .padStart(2, '0')}s`;
        }
        return `${minutes}m ${seconds.toString().padStart(2, '0')}s`;
    };

    // Calculate progress
    const totalInterval = data ? data.interval_minutes * 60 : 3600;
    const progress = data ? ((totalInterval - countdown) / totalInterval) * 100 : 0;

    return (
        <Card variant="glass" className="h-full">
            <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 rounded-xl bg-secondary/20 flex items-center justify-center">
                    <Clock className="w-5 h-5 text-secondary" />
                </div>
                <div>
                    <h3 className="font-bold text-white">Next Analysis</h3>
                    <p className="text-xs text-gray-500">
                        Every {data?.interval_hours || 4}h cycle
                    </p>
                </div>
            </div>

            {/* Countdown Display */}
            <div className="text-center py-6">
                <div className="relative inline-flex items-center justify-center">
                    {/* Circular progress background */}
                    <svg className="w-32 h-32 -rotate-90">
                        <circle
                            cx="64"
                            cy="64"
                            r="56"
                            fill="none"
                            stroke="rgba(75, 85, 99, 0.3)"
                            strokeWidth="8"
                        />
                        <circle
                            cx="64"
                            cy="64"
                            r="56"
                            fill="none"
                            stroke="url(#gradient)"
                            strokeWidth="8"
                            strokeLinecap="round"
                            strokeDasharray={`${progress * 3.52} 352`}
                            className="transition-all duration-1000"
                        />
                        <defs>
                            <linearGradient id="gradient" x1="0%" y1="0%" x2="100%" y2="0%">
                                <stop offset="0%" stopColor="#06b6d4" />
                                <stop offset="100%" stopColor="#8b5cf6" />
                            </linearGradient>
                        </defs>
                    </svg>

                    {/* Time display */}
                    <div className="absolute inset-0 flex flex-col items-center justify-center">
                        <Zap className="w-5 h-5 text-primary mb-1 animate-pulse" />
                        <p className="text-xl font-bold font-mono text-white">
                            {formatTime(countdown)}
                        </p>
                    </div>
                </div>
            </div>

            {/* Status */}
            <div className="flex items-center justify-center gap-2 text-sm text-gray-400">
                <RefreshCw size={14} className={countdown <= 60 ? 'animate-spin text-primary' : ''} />
                {countdown <= 60 ? (
                    <span className="text-primary font-medium">Scan starting soon...</span>
                ) : (
                    <span>Agents analyzing market</span>
                )}
            </div>
        </Card>
    );
}
