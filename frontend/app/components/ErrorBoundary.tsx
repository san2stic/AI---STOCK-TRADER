'use client';

import React, { Component, ErrorInfo, ReactNode } from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';

interface Props {
    children: ReactNode;
    fallback?: ReactNode;
}

interface State {
    hasError: boolean;
    error: Error | null;
    errorInfo: ErrorInfo | null;
}

/**
 * Error Boundary component to catch React errors gracefully.
 * Prevents the entire app from crashing when a component throws an error.
 */
class ErrorBoundary extends Component<Props, State> {
    constructor(props: Props) {
        super(props);
        this.state = {
            hasError: false,
            error: null,
            errorInfo: null
        };
    }

    static getDerivedStateFromError(error: Error): Partial<State> {
        return { hasError: true, error };
    }

    componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
        console.error('ErrorBoundary caught an error:', error, errorInfo);
        this.setState({ errorInfo });
    }

    handleRetry = (): void => {
        this.setState({
            hasError: false,
            error: null,
            errorInfo: null
        });
    };

    render(): ReactNode {
        if (this.state.hasError) {
            if (this.props.fallback) {
                return this.props.fallback;
            }

            return (
                <div className="min-h-[200px] flex items-center justify-center p-6">
                    <div className="bg-red-500/10 border border-red-500/30 rounded-2xl p-8 max-w-lg w-full text-center backdrop-blur-sm">
                        <div className="flex justify-center mb-4">
                            <div className="p-3 bg-red-500/20 rounded-full">
                                <AlertTriangle className="w-8 h-8 text-red-400" />
                            </div>
                        </div>

                        <h2 className="text-xl font-bold text-white mb-2">
                            Something went wrong
                        </h2>

                        <p className="text-gray-400 mb-4">
                            An unexpected error occurred. Please try again or refresh the page.
                        </p>

                        {process.env.NODE_ENV === 'development' && this.state.error && (
                            <div className="bg-black/30 rounded-lg p-4 mb-4 text-left overflow-auto max-h-40">
                                <code className="text-red-300 text-sm">
                                    {this.state.error.toString()}
                                </code>
                            </div>
                        )}

                        <button
                            onClick={this.handleRetry}
                            className="inline-flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-cyan-500 to-blue-500 hover:from-cyan-600 hover:to-blue-600 text-white rounded-xl font-semibold transition-all duration-200 shadow-lg shadow-cyan-500/20"
                        >
                            <RefreshCw className="w-4 h-4" />
                            Try Again
                        </button>
                    </div>
                </div>
            );
        }

        return this.props.children;
    }
}

export default ErrorBoundary;
