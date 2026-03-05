import { NextResponse } from "next/server";
import { getJsonFile, putJsonFile } from "../../../lib/s3Utils";
import crypto from "crypto";

export const dynamic = "force-dynamic";

const CONFIG_KEY = "api-keys/config.json";

/**
 * Read the API keys config from S3. Returns { keys: [] } if not found.
 */
async function getConfig() {
    const data = await getJsonFile(CONFIG_KEY);
    return data || { keys: [] };
}

/**
 * Save the API keys config to S3.
 */
async function saveConfig(config) {
    await putJsonFile(CONFIG_KEY, config);
}

/**
 * Mask an API key for display (show first 8 and last 4 chars).
 */
function maskKey(key) {
    if (!key || key.length < 16) return "••••••••";
    return key.slice(0, 8) + "••••••••" + key.slice(-4);
}

/**
 * Generate a new API key with prefix.
 */
function generateApiKey() {
    const raw = crypto.randomUUID().replace(/-/g, "") + crypto.randomUUID().replace(/-/g, "");
    return `mf_live_${raw.slice(0, 32)}`;
}

/**
 * GET /api/api-keys
 * List all API keys (with masked key values).
 */
export async function GET() {
    try {
        const config = await getConfig();
        const masked = config.keys.map((k) => ({
            ...k,
            key: maskKey(k.key),
        }));
        return NextResponse.json({ success: true, keys: masked });
    } catch (e) {
        console.error("[API Keys] GET error:", e);
        return NextResponse.json(
            { success: false, error: "Failed to load API keys" },
            { status: 500 }
        );
    }
}

/**
 * POST /api/api-keys
 * Create a new API key.
 * Body: { name, access: { type, allowed_amcs?, allowed_schemes? }, rate_limit? }
 */
export async function POST(request) {
    try {
        const body = await request.json();
        const { name, access, rate_limit } = body;

        if (!name || !name.trim()) {
            return NextResponse.json(
                { success: false, error: "Key name is required" },
                { status: 400 }
            );
        }

        const accessType = access?.type || "all";
        if (!["all", "restricted"].includes(accessType)) {
            return NextResponse.json(
                { success: false, error: "access.type must be 'all' or 'restricted'" },
                { status: 400 }
            );
        }

        const newKey = {
            id: `ak_${crypto.randomUUID().replace(/-/g, "").slice(0, 12)}`,
            key: generateApiKey(),
            name: name.trim(),
            created_at: new Date().toISOString(),
            is_active: true,
            access: {
                type: accessType,
                allowed_amcs: accessType === "restricted" ? (access?.allowed_amcs || []) : [],
                allowed_schemes: accessType === "restricted" ? (access?.allowed_schemes || []) : [],
            },
            rate_limit: rate_limit || 100,
            last_used_at: null,
        };

        const config = await getConfig();
        config.keys.push(newKey);
        await saveConfig(config);

        // Return the full key ONLY on creation
        return NextResponse.json({
            success: true,
            key: newKey,
        });
    } catch (e) {
        console.error("[API Keys] POST error:", e);
        return NextResponse.json(
            { success: false, error: "Failed to create API key" },
            { status: 500 }
        );
    }
}

/**
 * PATCH /api/api-keys
 * Update an existing API key.
 * Body: { id, name?, is_active?, access?, rate_limit? }
 */
export async function PATCH(request) {
    try {
        const body = await request.json();
        const { id, ...updates } = body;

        if (!id) {
            return NextResponse.json(
                { success: false, error: "Key id is required" },
                { status: 400 }
            );
        }

        const config = await getConfig();
        const idx = config.keys.findIndex((k) => k.id === id);

        if (idx === -1) {
            return NextResponse.json(
                { success: false, error: "API key not found" },
                { status: 404 }
            );
        }

        // Apply allowed updates
        if (updates.name !== undefined) config.keys[idx].name = updates.name.trim();
        if (updates.is_active !== undefined) config.keys[idx].is_active = !!updates.is_active;
        if (updates.rate_limit !== undefined) config.keys[idx].rate_limit = updates.rate_limit;
        if (updates.access !== undefined) {
            const accessType = updates.access.type || config.keys[idx].access?.type || "all";
            config.keys[idx].access = {
                type: accessType,
                allowed_amcs: accessType === "restricted" ? (updates.access.allowed_amcs || []) : [],
                allowed_schemes: accessType === "restricted" ? (updates.access.allowed_schemes || []) : [],
            };
        }

        await saveConfig(config);

        return NextResponse.json({
            success: true,
            key: { ...config.keys[idx], key: maskKey(config.keys[idx].key) },
        });
    } catch (e) {
        console.error("[API Keys] PATCH error:", e);
        return NextResponse.json(
            { success: false, error: "Failed to update API key" },
            { status: 500 }
        );
    }
}

/**
 * DELETE /api/api-keys
 * Delete an API key.
 * Body: { id }
 */
export async function DELETE(request) {
    try {
        const body = await request.json();
        const { id } = body;

        if (!id) {
            return NextResponse.json(
                { success: false, error: "Key id is required" },
                { status: 400 }
            );
        }

        const config = await getConfig();
        const idx = config.keys.findIndex((k) => k.id === id);

        if (idx === -1) {
            return NextResponse.json(
                { success: false, error: "API key not found" },
                { status: 404 }
            );
        }

        config.keys.splice(idx, 1);
        await saveConfig(config);

        return NextResponse.json({ success: true });
    } catch (e) {
        console.error("[API Keys] DELETE error:", e);
        return NextResponse.json(
            { success: false, error: "Failed to delete API key" },
            { status: 500 }
        );
    }
}
