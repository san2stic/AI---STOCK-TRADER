'use client';

import { ReactNode } from 'react';

interface BadgeProps {
    children: ReactNode;
    variant?: 'success' | 'warning' | 'danger' | 'info' | 'purple' | 'neutral';
    size?: 'sm' | 'md';
    dot?: boolean;
    pulse?: boolean;
    className?: string;
}

const variantClasses = {
    success: 'bg-success/20 text-success border-success/30',
    warning: 'bg-warning/20 text-warning border-warning/30',
    danger: 'bg-danger/20 text-danger border-danger/30',
    info: 'bg-primary/20 text-primary border-primary/30',
    purple: 'bg-secondary/20 text-secondary border-secondary/30',
    neutral: 'bg-surface-elevated text-gray-400 border-surface-border',
};

const dotColors = {
    success: 'bg-success',
    warning: 'bg-warning',
    danger: 'bg-danger',
    info: 'bg-primary',
    purple: 'bg-secondary',
    neutral: 'bg-gray-500',
};

const sizeClasses = {
    sm: 'px-2 py-0.5 text-2xs',
    md: 'px-2.5 py-1 text-xs',
};

export default function Badge({
    children,
    variant = 'info',
    size = 'md',
    dot = false,
    pulse = false,
    className = '',
}: BadgeProps) {
    return (
        <span
            className={`inline-flex items-center gap-1.5 font-semibold rounded-full border uppercase tracking-wide ${variantClasses[variant]} ${sizeClasses[size]} ${className}`}
        >
            {dot && (
                <span className="relative flex h-2 w-2">
                    {pulse && (
                        <span
                            className={`animate-ping absolute inline-flex h-full w-full rounded-full ${dotColors[variant]} opacity-75`}
                        />
                    )}
                    <span
                        className={`relative inline-flex rounded-full h-2 w-2 ${dotColors[variant]}`}
                    />
                </span>
            )}
            {children}
        </span>
    );
}

// Status badge with predefined states
export function StatusBadge({
    status,
}: {
    status: 'online' | 'offline' | 'connecting' | 'paused';
}) {
    const config = {
        online: { variant: 'success' as const, label: 'Online', dot: true, pulse: true },
        offline: { variant: 'danger' as const, label: 'Offline', dot: true, pulse: false },
        connecting: { variant: 'warning' as const, label: 'Connecting', dot: true, pulse: true },
        paused: { variant: 'neutral' as const, label: 'Paused', dot: true, pulse: false },
    };

    const { variant, label, dot, pulse } = config[status];

    return (
        <Badge variant={variant} dot={dot} pulse={pulse}>
            {label}
        </Badge>
    );
}

// PnL badge that changes color based on value
export function PnLBadge({ value, percent }: { value: number; percent?: number }) {
    const isPositive = value >= 0;
    const variant = isPositive ? 'success' : 'danger';
    const sign = isPositive ? '+' : '';

    return (
        <Badge variant={variant} size="sm">
            {sign}${Math.abs(value).toFixed(2)}
            {percent !== undefined && ` (${sign}${percent.toFixed(2)}%)`}
        </Badge>
    );
}
