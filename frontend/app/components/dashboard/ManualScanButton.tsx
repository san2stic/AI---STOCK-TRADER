'use client';

import { useState } from 'react';
import { Play, Loader2, CheckCircle2, XCircle } from 'lucide-react';
import Button from '../ui/Button';

interface ScanResult {
    status: 'success' | 'error';
    message: string;
    timestamp?: string;
}

export default function ManualScanButton() {
    const [isScanning, setIsScanning] = useState(false);
    const [result, setResult] = useState<ScanResult | null>(null);

    const triggerScan = async () => {
        setIsScanning(true);
        setResult(null);

        try {
            const res = await fetch('/api/scan/trigger', {
                method: 'POST',
            });

            if (res.ok) {
                const data = await res.json();
                setResult({
                    status: 'success',
                    message: data.message || 'Scan completed successfully',
                    timestamp: data.timestamp,
                });
            } else {
                const error = await res.json();
                setResult({
                    status: 'error',
                    message: error.detail || 'Scan failed',
                });
            }
        } catch (error) {
            setResult({
                status: 'error',
                message: 'Network error - could not trigger scan',
            });
        } finally {
            setIsScanning(false);

            // Clear result after 5 seconds
            setTimeout(() => {
                setResult(null);
            }, 5000);
        }
    };

    return (
        <div className="flex flex-col gap-2">
            <Button
                onClick={triggerScan}
                disabled={isScanning}
                variant="primary"
                className="w-full group relative overflow-hidden"
            >
                <div className="relative z-10 flex items-center justify-center gap-2">
                    {isScanning ? (
                        <>
                            <Loader2 className="w-4 h-4 animate-spin" />
                            <span>Scanning...</span>
                        </>
                    ) : (
                        <>
                            <Play className="w-4 h-4 group-hover:scale-110 transition-transform" />
                            <span>Run Manual Scan</span>
                        </>
                    )}
                </div>

                {/* Animated gradient background on hover */}
                <div className="absolute inset-0 bg-gradient-to-r from-primary/0 via-primary/20 to-primary/0 group-hover:translate-x-full transition-transform duration-1000 ease-out" />
            </Button>

            {/* Result feedback */}
            {result && (
                <div
                    className={`flex items-center gap-2 text-sm p-2 rounded-lg animate-slide-in ${result.status === 'success'
                            ? 'bg-green-500/10 text-green-400 border border-green-500/20'
                            : 'bg-red-500/10 text-red-400 border border-red-500/20'
                        }`}
                >
                    {result.status === 'success' ? (
                        <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
                    ) : (
                        <XCircle className="w-4 h-4 flex-shrink-0" />
                    )}
                    <span className="flex-1">{result.message}</span>
                </div>
            )}
        </div>
    );
}
