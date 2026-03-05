/**
 * API Key Authentication Utility
 * Validates API keys from query parameters against S3-stored config.
 * Used by public /api/v1/* endpoints.
 */

import { getJsonFile, putJsonFile } from "./s3Utils";
import { NextResponse } from "next/server";

const CONFIG_KEY = "api-keys/config.json";

// In-memory cache for API key config (5-minute TTL)
let _configCache = null;
let _configCacheTime = 0;
const CONFIG_CACHE_TTL = 5 * 60 * 1000; // 5 minutes

/**
 * Fetch API keys config from S3 with caching.
 */
async function getApiKeysConfig() {
    if (_configCache && Date.now() - _configCacheTime < CONFIG_CACHE_TTL) {
        return _configCache;
    }
    const data = await getJsonFile(CONFIG_KEY);
    _configCache = data || { keys: [] };
    _configCacheTime = Date.now();
    return _configCache;
}

/**
 * Validate an API key from the request.
 *
 * @param {Request} request - The incoming Next.js request
 * @returns {{ valid: boolean, keyData?: object, error?: { code: string, message: string, status: number } }}
 */
export async function validateApiKey(request) {
    const { searchParams } = new URL(request.url);
    const apiKey = searchParams.get("api_key");

    if (!apiKey) {
        return {
            valid: false,
            error: {
                code: "MISSING_API_KEY",
                message: "An api_key query parameter is required. Example: ?api_key=mf_live_xxx",
                status: 401,
            },
        };
    }

    try {
        const config = await getApiKeysConfig();
        const keyData = config.keys.find((k) => k.key === apiKey);

        if (!keyData) {
            return {
                valid: false,
                error: {
                    code: "INVALID_API_KEY",
                    message: "The provided API key is invalid.",
                    status: 401,
                },
            };
        }

        if (!keyData.is_active) {
            return {
                valid: false,
                error: {
                    code: "INVALID_API_KEY",
                    message: "This API key has been revoked.",
                    status: 403,
                },
            };
        }

        // Update last_used_at asynchronously (fire-and-forget)
        updateLastUsed(keyData.id).catch(() => { });

        return { valid: true, keyData };
    } catch (e) {
        console.error("[API Auth] Validation error:", e);
        return {
            valid: false,
            error: {
                code: "INTERNAL_ERROR",
                message: "Failed to validate API key.",
                status: 500,
            },
        };
    }
}

/**
 * Check if a fund is accessible by the given API key.
 *
 * @param {object} keyData - The validated API key object
 * @param {object} fund - The fund object (must have slug and amc_slug)
 * @returns {boolean}
 */
export function isFundAccessible(keyData, fund) {
    const access = keyData.access;

    // "all" access type grants access to everything
    if (!access || access.type === "all") {
        return true;
    }

    // Check scheme-level access first (most specific)
    if (access.allowed_schemes && access.allowed_schemes.length > 0) {
        if (access.allowed_schemes.includes(fund.slug)) {
            return true;
        }
    }

    // Check AMC-level access
    if (access.allowed_amcs && access.allowed_amcs.length > 0) {
        if (access.allowed_amcs.includes(fund.amc_slug)) {
            return true;
        }
    }

    // If restricted and neither scheme nor AMC matched, deny
    return false;
}

/**
 * Build an error response for API key validation failures.
 */
export function apiErrorResponse(error) {
    return NextResponse.json(
        {
            success: false,
            error: {
                code: error.code,
                message: error.message,
            },
        },
        { status: error.status }
    );
}

/**
 * Update last_used_at for a key (async, non-blocking).
 */
async function updateLastUsed(keyId) {
    try {
        const config = await getJsonFile(CONFIG_KEY);
        if (!config) return;
        const key = config.keys.find((k) => k.id === keyId);
        if (key) {
            key.last_used_at = new Date().toISOString();
            await putJsonFile(CONFIG_KEY, config);
            // Invalidate cache so next read gets the update
            _configCache = null;
        }
    } catch { }
}
