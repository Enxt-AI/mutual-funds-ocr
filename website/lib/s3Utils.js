/**
 * S3 Utility Library
 * Shared between website and admin for reading/writing fund JSON data.
 */

import {
    S3Client,
    ListObjectsV2Command,
    GetObjectCommand,
    PutObjectCommand,
    DeleteObjectCommand,
    HeadObjectCommand,
} from "@aws-sdk/client-s3";
import fs from "fs";
import path from "path";

const BUCKET = process.env.S3_BUCKET_NAME;
const REGION = process.env.AWS_REGION || "ap-south-1";

let _client = null;

function getClient() {
    if (!_client) {
        _client = new S3Client({
            region: REGION,
            credentials: {
                accessKeyId: process.env.AWS_ACCESS_KEY_ID,
                secretAccessKey: process.env.AWS_SECRET_ACCESS_KEY,
            },
        });
    }
    return _client;
}

function useLocalFallback() {
    return (
        process.env.NO_S3 === "1" ||
        process.env.NO_S3 === "true" ||
        !process.env.AWS_ACCESS_KEY_ID ||
        process.env.AWS_ACCESS_KEY_ID === "your_access_key"
    );
}

function getLocalDataDirs() {
    const dirs = [];
    if (process.env.EXTRACTED_DATA_PATH) {
        dirs.push(process.env.EXTRACTED_DATA_PATH);
    }
    const rootDir = path.resolve(process.cwd(), "..");
    const extractedDataDir = path.join(rootDir, "extracted_data");
    if (fs.existsSync(extractedDataDir)) {
        dirs.push(extractedDataDir);
    }
    const dataDir = path.join(rootDir, "website", "data");
    if (fs.existsSync(dataDir)) {
        dirs.push(dataDir);
    }
    return [...new Set(dirs)].filter(d => fs.existsSync(d));
}

function getLocalFilePath(key) {
    const dirs = getLocalDataDirs();
    let relativePath = key;
    if (key.startsWith("funds/")) {
        relativePath = key.replace("funds/", "");
    } else if (key.startsWith("status/")) {
        relativePath = path.join(".status", key.replace("status/", ""));
    }
    for (const dir of dirs) {
        const filePath = path.join(dir, relativePath);
        if (fs.existsSync(filePath)) {
            return filePath;
        }
    }
    return path.join(dirs[0] || path.resolve(process.cwd(), "..", "extracted_data"), relativePath);
}

/**
 * List all .json file keys under a given S3 prefix.
 * @param {string} prefix - e.g. "funds/" or "status/"
 * @returns {Promise<Array<{key: string, size: number, lastModified: Date}>>}
 */
export async function listJsonFiles(prefix) {
    if (useLocalFallback()) {
        const dirs = getLocalDataDirs();
        const itemsMap = new Map();
        for (const dir of dirs) {
            let searchDir = dir;
            if (prefix.startsWith("status")) {
                searchDir = path.join(dir, ".status");
            }
            if (!fs.existsSync(searchDir)) {
                continue;
            }
            const files = fs.readdirSync(searchDir);
            for (const file of files) {
                if (file.endsWith(".json")) {
                    const filePath = path.join(searchDir, file);
                    const stats = fs.statSync(filePath);
                    const fileKey = prefix + file;
                    if (!itemsMap.has(fileKey)) {
                        itemsMap.set(fileKey, {
                            key: fileKey,
                            size: stats.size,
                            lastModified: stats.mtime,
                        });
                    }
                }
            }
        }
        return Array.from(itemsMap.values());
    }

    const client = getClient();
    const items = [];
    let continuationToken;

    do {
        const cmd = new ListObjectsV2Command({
            Bucket: BUCKET,
            Prefix: prefix,
            ContinuationToken: continuationToken,
        });
        const res = await client.send(cmd);

        for (const obj of res.Contents || []) {
            if (obj.Key.endsWith(".json")) {
                items.push({
                    key: obj.Key,
                    size: obj.Size,
                    lastModified: obj.LastModified,
                });
            }
        }
        continuationToken = res.NextContinuationToken;
    } while (continuationToken);

    return items;
}

/**
 * Fetch and parse a single JSON file from S3.
 * @param {string} key - full S3 key, e.g. "funds/360-one.json"
 * @returns {Promise<object|null>}
 */
export async function getJsonFile(key) {
    if (useLocalFallback()) {
        const filePath = getLocalFilePath(key);
        if (!fs.existsSync(filePath)) return null;
        try {
            const body = fs.readFileSync(filePath, "utf-8");
            return JSON.parse(body);
        } catch (e) {
            console.error(`Error parsing local file ${filePath}:`, e);
            return null;
        }
    }

    try {
        const client = getClient();
        const cmd = new GetObjectCommand({ Bucket: BUCKET, Key: key });
        const res = await client.send(cmd);
        const body = await res.Body.transformToString("utf-8");
        return JSON.parse(body);
    } catch (e) {
        if (e.name === "NoSuchKey") return null;
        throw e;
    }
}

/**
 * Upload a JSON object to S3.
 * @param {string} key - full S3 key, e.g. "funds/360-one.json"
 * @param {object} data - JSON-serializable object
 */
export async function putJsonFile(key, data) {
    if (useLocalFallback()) {
        const filePath = getLocalFilePath(key);
        const dir = path.dirname(filePath);
        if (!fs.existsSync(dir)) {
            fs.mkdirSync(dir, { recursive: true });
        }
        fs.writeFileSync(filePath, JSON.stringify(data, null, 2), "utf-8");
        return;
    }

    const client = getClient();
    const cmd = new PutObjectCommand({
        Bucket: BUCKET,
        Key: key,
        Body: JSON.stringify(data, null, 2),
        ContentType: "application/json",
    });
    await client.send(cmd);
}

/**
 * Upload raw buffer/string content to S3.
 * @param {string} key - full S3 key
 * @param {Buffer|string} body - file content
 * @param {string} contentType - MIME type
 */
export async function putFile(key, body, contentType = "application/octet-stream") {
    if (useLocalFallback()) {
        const filePath = getLocalFilePath(key);
        const dir = path.dirname(filePath);
        if (!fs.existsSync(dir)) {
            fs.mkdirSync(dir, { recursive: true });
        }
        fs.writeFileSync(filePath, body);
        return;
    }

    const client = getClient();
    const cmd = new PutObjectCommand({
        Bucket: BUCKET,
        Key: key,
        Body: body,
        ContentType: contentType,
    });
    await client.send(cmd);
}

/**
 * Delete a file from S3.
 * @param {string} key - full S3 key
 */
export async function deleteFile(key) {
    if (useLocalFallback()) {
        const filePath = getLocalFilePath(key);
        if (fs.existsSync(filePath)) {
            fs.unlinkSync(filePath);
        }
        return;
    }

    const client = getClient();
    const cmd = new DeleteObjectCommand({ Bucket: BUCKET, Key: key });
    await client.send(cmd);
}

/**
 * Check if a file exists in S3 and return its metadata.
 * @param {string} key
 * @returns {Promise<{size: number, lastModified: Date}|null>}
 */
export async function headFile(key) {
    if (useLocalFallback()) {
        const filePath = getLocalFilePath(key);
        if (!fs.existsSync(filePath)) return null;
        const stats = fs.statSync(filePath);
        return { size: stats.size, lastModified: stats.mtime };
    }

    try {
        const client = getClient();
        const cmd = new HeadObjectCommand({ Bucket: BUCKET, Key: key });
        const res = await client.send(cmd);
        return { size: res.ContentLength, lastModified: res.LastModified };
    } catch (e) {
        if (e.name === "NotFound" || e.$metadata?.httpStatusCode === 404) return null;
        throw e;
    }
}

