'use client';

interface ProgressProps {
    value: number;
    max?: number;
    variant?: 'primary' | 'success' | 'danger' | 'warning';
    size?: 'sm' | 'md' | 'lg';
    showLabel?: boolean;
    label?: string;
    className?: string;
    animated?: boolean;
}

const variantClasses = {
    primary: 'bg-gradient-to-r from-primary to-secondary',
    success: 'bg-gradient-to-r from-success to-primary',
    danger: 'bg-gradient-to-r from-danger to-warning',
    warning: 'bg-warning',
};

const sizeClasses = {
    sm: 'h-1',
    md: 'h-2',
    lg: 'h-3',
};

export default function Progress({
    value,
    max = 100,
    variant = 'primary',
    size = 'md',
    showLabel = false,
    label,
    className = '',
    animated = false,
}: ProgressProps) {
    const percentage = Math.min(Math.max((value / max) * 100, 0), 100);

    return (
        <div className={`w-full ${className}`}>
            {(showLabel || label) && (
                <div className="flex justify-between mb-1.5 text-xs">
                    <span className="text-gray-400">{label}</span>
                    {showLabel && (
                        <span className="text-white font-mono">{percentage.toFixed(0)}%</span>
                    )}
                </div>
            )}
            <div
                className={`w-full bg-surface-border rounded-full overflow-hidden ${sizeClasses[size]}`}
            >
                <div
                    className={`${sizeClasses[size]} ${variantClasses[variant]} rounded-full transition-all duration-500 ease-out ${animated ? 'animate-pulse' : ''
                        }`}
                    style={{ width: `${percentage}%` }}
                />
            </div>
        </div>
    );
}

// Circular progress variant
export function CircularProgress({
    value,
    max = 100,
    size = 64,
    strokeWidth = 4,
    variant = 'primary',
    showValue = true,
}: {
    value: number;
    max?: number;
    size?: number;
    strokeWidth?: number;
    variant?: 'primary' | 'success' | 'danger' | 'warning';
    showValue?: boolean;
}) {
    const percentage = Math.min(Math.max((value / max) * 100, 0), 100);
    const radius = (size - strokeWidth) / 2;
    const circumference = radius * 2 * Math.PI;
    const offset = circumference - (percentage / 100) * circumference;

    const colors = {
        primary: '#06b6d4',
        success: '#10b981',
        danger: '#f43f5e',
        warning: '#f59e0b',
    };

    return (
        <div className="relative inline-flex items-center justify-center">
            <svg width={size} height={size} className="-rotate-90">
                {/* Background circle */}
                <circle
                    cx={size / 2}
                    cy={size / 2}
                    r={radius}
                    fill="none"
                    stroke="rgba(75, 85, 99, 0.4)"
                    strokeWidth={strokeWidth}
                />
                {/* Progress circle */}
                <circle
                    cx={size / 2}
                    cy={size / 2}
                    r={radius}
                    fill="none"
                    stroke={colors[variant]}
                    strokeWidth={strokeWidth}
                    strokeLinecap="round"
                    strokeDasharray={circumference}
                    strokeDashoffset={offset}
                    className="transition-all duration-500 ease-out"
                    style={{
                        filter: `drop-shadow(0 0 6px ${colors[variant]}50)`,
                    }}
                />
            </svg>
            {showValue && (
                <span className="absolute text-xs font-bold font-mono">
                    {percentage.toFixed(0)}%
                </span>
            )}
        </div>
    );
}
