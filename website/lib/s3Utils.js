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

/**
 * List all .json file keys under a given S3 prefix.
 * @param {string} prefix - e.g. "funds/" or "status/"
 * @returns {Promise<Array<{key: string, size: number, lastModified: Date}>>}
 */
export async function listJsonFiles(prefix) {
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
