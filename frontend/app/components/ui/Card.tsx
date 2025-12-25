'use client';

import { ReactNode } from 'react';

interface CardProps {
    children: ReactNode;
    variant?: 'default' | 'glass' | 'glow';
    className?: string;
    padding?: 'none' | 'sm' | 'md' | 'lg';
    hover?: boolean;
    onClick?: () => void;
}

const paddingClasses = {
    none: '',
    sm: 'p-4',
    md: 'p-6',
    lg: 'p-8',
};

const variantClasses = {
    default: 'bg-surface border border-surface-border',
    glass: 'bg-surface/80 backdrop-blur-xl border border-surface-border',
    glow: 'bg-surface/80 backdrop-blur-xl border border-primary/30 shadow-glow-primary',
};

export default function Card({
    children,
    variant = 'glass',
    className = '',
    padding = 'md',
    hover = false,
    onClick,
}: CardProps) {
    const baseClasses = 'rounded-xl transition-all duration-300';
    const hoverClasses = hover
        ? 'hover:border-primary/50 hover:shadow-card-hover hover:-translate-y-1 cursor-pointer'
        : '';

    return (
        <div
            className={`${baseClasses} ${variantClasses[variant]} ${paddingClasses[padding]} ${hoverClasses} ${className}`}
            onClick={onClick}
            role={onClick ? 'button' : undefined}
            tabIndex={onClick ? 0 : undefined}
        >
            {children}
        </div>
    );
}

// Subcomponents for structured cards
Card.Header = function CardHeader({
    children,
    className = '',
}: {
    children: ReactNode;
    className?: string;
}) {
    return (
        <div className={`flex items-center justify-between mb-4 ${className}`}>
            {children}
        </div>
    );
};

Card.Title = function CardTitle({
    children,
    className = '',
    icon,
}: {
    children: ReactNode;
    className?: string;
    icon?: ReactNode;
}) {
    return (
        <h3 className={`text-lg font-semibold flex items-center gap-2 ${className}`}>
            {icon && <span className="text-primary">{icon}</span>}
            {children}
        </h3>
    );
};

Card.Body = function CardBody({
    children,
    className = '',
}: {
    children: ReactNode;
    className?: string;
}) {
    return <div className={className}>{children}</div>;
};

Card.Footer = function CardFooter({
    children,
    className = '',
}: {
    children: ReactNode;
    className?: string;
}) {
    return (
        <div className={`mt-4 pt-4 border-t border-surface-border ${className}`}>
            {children}
        </div>
    );
};
