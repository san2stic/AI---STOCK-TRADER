"use client";

import { useState, useEffect } from "react";

interface NextScanData {
    interval_minutes: number;
    interval_hours: number;
    next_scan_utc: string;
    seconds_until_next_scan: number;
    current_time_utc: string;
}

export default function NextScanCountdown() {
    const [scanData, setScanData] = useState<NextScanData | null>(null);
    const [countdown, setCountdown] = useState<number>(0);
    const [error, setError] = useState<string | null>(null);

    // Fetch next scan info
    const fetchNextScan = async () => {
        try {
            const response = await fetch("/api/next-scan");
            if (!response.ok) {
                throw new Error("Failed to fetch next scan info");
            }
            const data = await response.json();
            setScanData(data);
            setCountdown(data.seconds_until_next_scan);
            setError(null);
        } catch (err) {
            setError(err instanceof Error ? err.message : "Unknown error");
            console.error("Error fetching next scan:", err);
        }
    };

    // Initial fetch and refresh every 30 seconds
    useEffect(() => {
        fetchNextScan();
        const interval = setInterval(fetchNextScan, 30000);
        return () => clearInterval(interval);
    }, []);

    // Countdown timer (updates every second)
    useEffect(() => {
        if (countdown <= 0) return;

        const timer = setInterval(() => {
            setCountdown((prev) => {
                if (prev <= 1) {
                    fetchNextScan(); // Refresh when countdown reaches 0
                    return 0;
                }
                return prev - 1;
            });
        }, 1000);

        return () => clearInterval(timer);
    }, [countdown]);

    // Format countdown as HH:MM:SS
    const formatCountdown = (seconds: number): string => {
        if (seconds <= 0) return "Scan en cours...";

        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        const secs = seconds % 60;

        if (hours > 0) {
            return `${hours}h ${minutes.toString().padStart(2, "0")}m ${secs
                .toString()
                .padStart(2, "0")}s`;
        } else {
            return `${minutes}m ${secs.toString().padStart(2, "0")}s`;
        }
    };

    if (error) {
        return (
            <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-4">
                <p className="text-red-500 text-sm">❌ {error}</p>
            </div>
        );
    }

    if (!scanData) {
        return (
            <div className="bg-gray-800/50 border border-gray-700 rounded-lg p-4 animate-pulse">
                <div className="h-6 bg-gray-700 rounded w-48 mb-2"></div>
                <div className="h-4 bg-gray-700 rounded w-32"></div>
            </div>
        );
    }

    return (
        <div className="bg-gradient-to-br from-blue-900/30 to-purple-900/30 border border-blue-500/30 rounded-lg p-4 shadow-lg">
            <div className="flex items-center justify-between">
                <div>
                    <div className="flex items-center gap-2 mb-1">
                        <span className="text-2xl">⏱️</span>
                        <h3 className="text-lg font-semibold text-white">
                            Prochain Scan
                        </h3>
                    </div>
                    <p className="text-sm text-gray-400">
                        Analyse des positions tous les {scanData.interval_hours}h
                    </p>
                </div>

                <div className="text-right">
                    <div className="text-3xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-purple-400 mb-1">
                        {formatCountdown(countdown)}
                    </div>
                    <p className="text-xs text-gray-500">
                        {new Date(scanData.next_scan_utc).toLocaleTimeString("fr-FR", {
                            hour: "2-digit",
                            minute: "2-digit",
                            timeZone: "UTC",
                        })}{" "}
                        UTC
                    </p>
                </div>
            </div>

            {/* Progress bar */}
            <div className="mt-3 bg-gray-700/50 rounded-full h-2 overflow-hidden">
                <div
                    className="h-full bg-gradient-to-r from-blue-500 to-purple-500 transition-all duration-1000 ease-linear"
                    style={{
                        width: `${((scanData.interval_minutes * 60 - countdown) /
                                (scanData.interval_minutes * 60)) *
                            100
                            }%`,
                    }}
                ></div>
            </div>
        </div>
    );
}
