'use client';

import { ReactNode, ButtonHTMLAttributes } from 'react';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
    children: ReactNode;
    variant?: 'primary' | 'secondary' | 'danger' | 'ghost' | 'success';
    size?: 'sm' | 'md' | 'lg';
    loading?: boolean;
    icon?: ReactNode;
    iconPosition?: 'left' | 'right';
}

const variantClasses = {
    primary:
        'bg-gradient-to-r from-primary to-secondary text-white shadow-md hover:shadow-glow-primary hover:-translate-y-0.5',
    secondary:
        'bg-surface-elevated text-white border border-surface-border hover:bg-surface-border hover:border-primary/30',
    danger:
        'bg-danger text-white hover:bg-danger-hover hover:shadow-glow-danger',
    ghost:
        'bg-transparent text-gray-400 hover:bg-surface-elevated hover:text-white',
    success:
        'bg-success text-white hover:bg-success-hover hover:shadow-glow-success',
};

const sizeClasses = {
    sm: 'px-3 py-1.5 text-xs',
    md: 'px-4 py-2 text-sm',
    lg: 'px-6 py-3 text-base',
};

export default function Button({
    children,
    variant = 'primary',
    size = 'md',
    loading = false,
    icon,
    iconPosition = 'left',
    className = '',
    disabled,
    ...props
}: ButtonProps) {
    const baseClasses =
        'inline-flex items-center justify-center gap-2 font-semibold rounded-lg transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-primary/50 focus:ring-offset-2 focus:ring-offset-background disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none';

    return (
        <button
            className={`${baseClasses} ${variantClasses[variant]} ${sizeClasses[size]} ${className}`}
            disabled={disabled || loading}
            {...props}
        >
            {loading ? (
                <>
                    <svg
                        className="animate-spin h-4 w-4"
                        xmlns="http://www.w3.org/2000/svg"
                        fill="none"
                        viewBox="0 0 24 24"
                    >
                        <circle
                            className="opacity-25"
                            cx="12"
                            cy="12"
                            r="10"
                            stroke="currentColor"
                            strokeWidth="4"
                        />
                        <path
                            className="opacity-75"
                            fill="currentColor"
                            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                        />
                    </svg>
                    Loading...
                </>
            ) : (
                <>
                    {icon && iconPosition === 'left' && icon}
                    {children}
                    {icon && iconPosition === 'right' && icon}
                </>
            )}
        </button>
    );
}

// Icon button variant
export function IconButton({
    children,
    variant = 'ghost',
    size = 'md',
    className = '',
    ...props
}: Omit<ButtonProps, 'icon' | 'iconPosition'>) {
    const sizeClasses = {
        sm: 'p-1.5',
        md: 'p-2',
        lg: 'p-3',
    };

    return (
        <Button
            variant={variant}
            className={`${sizeClasses[size]} ${className}`}
            {...props}
        >
            {children}
        </Button>
    );
}
