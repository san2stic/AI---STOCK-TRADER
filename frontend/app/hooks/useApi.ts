'use client';

import { useState, useCallback, useRef, useEffect } from 'react';

interface UseApiOptions<T> {
    /** Initial data value */
    initialData?: T;
    /** Auto-fetch on mount */
    autoFetch?: boolean;
    /** Cache duration in milliseconds (default: 30 seconds) */
    cacheDuration?: number;
    /** Number of retries on failure */
    retries?: number;
    /** Retry delay in milliseconds */
    retryDelay?: number;
}

interface UseApiReturn<T> {
    data: T | null;
    error: Error | null;
    loading: boolean;
    refetch: () => Promise<void>;
    reset: () => void;
}

interface CacheEntry<T> {
    data: T;
    timestamp: number;
}

// Global cache for API responses
const apiCache = new Map<string, CacheEntry<unknown>>();

/**
 * Custom hook for API calls with automatic retries, caching, and error handling.
 * 
 * @param url - API endpoint URL
 * @param options - Configuration options
 * @returns Object with data, error, loading state, and refetch function
 */
export function useApi<T>(
    url: string,
    options: UseApiOptions<T> = {}
): UseApiReturn<T> {
    const {
        initialData = null,
        autoFetch = true,
        cacheDuration = 30000, // 30 seconds default
        retries = 3,
        retryDelay = 1000,
    } = options;

    const [data, setData] = useState<T | null>(initialData);
    const [error, setError] = useState<Error | null>(null);
    const [loading, setLoading] = useState<boolean>(autoFetch);

    const abortControllerRef = useRef<AbortController | null>(null);
    const mountedRef = useRef<boolean>(true);

    const getCachedData = useCallback((): T | null => {
        const cached = apiCache.get(url);
        if (cached && Date.now() - cached.timestamp < cacheDuration) {
            return cached.data as T;
        }
        return null;
    }, [url, cacheDuration]);

    const setCachedData = useCallback((data: T): void => {
        apiCache.set(url, {
            data,
            timestamp: Date.now(),
        });
    }, [url]);

    const fetchWithRetry = useCallback(async (
        attemptNumber: number = 1
    ): Promise<T> => {
        try {
            // Create new abort controller for this request
            abortControllerRef.current = new AbortController();

            const response = await fetch(url, {
                signal: abortControllerRef.current.signal,
                headers: {
                    'Content-Type': 'application/json',
                },
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const result = await response.json();
            return result as T;
        } catch (err) {
            const error = err as Error;

            // Don't retry on abort
            if (error.name === 'AbortError') {
                throw error;
            }

            // Retry if we have attempts left
            if (attemptNumber < retries) {
                await new Promise(resolve =>
                    setTimeout(resolve, retryDelay * attemptNumber)
                );
                return fetchWithRetry(attemptNumber + 1);
            }

            throw error;
        }
    }, [url, retries, retryDelay]);

    const refetch = useCallback(async (): Promise<void> => {
        // Cancel any in-flight request
        if (abortControllerRef.current) {
            abortControllerRef.current.abort();
        }

        setLoading(true);
        setError(null);

        try {
            // Check cache first
            const cachedData = getCachedData();
            if (cachedData !== null) {
                setData(cachedData);
                setLoading(false);
                return;
            }

            const result = await fetchWithRetry();

            if (mountedRef.current) {
                setData(result);
                setCachedData(result);
                setLoading(false);
            }
        } catch (err) {
            if (mountedRef.current && (err as Error).name !== 'AbortError') {
                setError(err as Error);
                setLoading(false);
            }
        }
    }, [getCachedData, setCachedData, fetchWithRetry]);

    const reset = useCallback((): void => {
        setData(initialData);
        setError(null);
        setLoading(false);
        apiCache.delete(url);
    }, [initialData, url]);

    // Auto-fetch on mount if enabled
    useEffect(() => {
        mountedRef.current = true;

        if (autoFetch) {
            refetch();
        }

        return () => {
            mountedRef.current = false;
            if (abortControllerRef.current) {
                abortControllerRef.current.abort();
            }
        };
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [autoFetch, url]);

    return { data, error, loading, refetch, reset };
}

/**
 * Manually clear the entire API cache
 */
export function clearApiCache(): void {
    apiCache.clear();
}

/**
 * Clear a specific URL from the cache
 */
export function clearCacheFor(url: string): void {
    apiCache.delete(url);
}

export default useApi;
