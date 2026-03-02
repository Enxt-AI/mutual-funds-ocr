/**
 * Trial Status API Route
 * Verifies Firebase ID token, checks Firestore createdAt,
 * and returns trial expiry status.
 */
import { NextResponse } from "next/server";
import { adminAuth, adminDb } from "../../../../lib/firebaseAdmin";

const TRIAL_MINUTES = 30;

export async function GET(request) {
    try {
        // Extract token from Authorization header
        const authHeader = request.headers.get("Authorization");
        if (!authHeader?.startsWith("Bearer ")) {
            return NextResponse.json({ error: "Missing token" }, { status: 401 });
        }
        const token = authHeader.split("Bearer ")[1];

        // Verify the ID token
        const decoded = await adminAuth.verifyIdToken(token);
        const uid = decoded.uid;

        // Get user's trial start from Firestore
        const userDoc = await adminDb.collection("users").doc(uid).get();

        if (!userDoc.exists) {
            // User doc doesn't exist yet — create it now (edge case: signed up before Firestore was added)
            await adminDb.collection("users").doc(uid).set({
                email: decoded.email,
                createdAt: new Date(),
            });
            return NextResponse.json({ expired: false, minutesLeft: TRIAL_MINUTES });
        }

        const data = userDoc.data();
        const createdAt = data.createdAt?.toDate?.() || new Date(data.createdAt);
        const now = new Date();
        const diffMs = now.getTime() - createdAt.getTime();
        const diffMinutes = diffMs / (1000 * 60);
        const minutesLeft = Math.max(0, Math.ceil(TRIAL_MINUTES - diffMinutes));
        const expired = diffMinutes >= TRIAL_MINUTES;

        return NextResponse.json({
            expired,
            minutesLeft,
            createdAt: createdAt.toISOString(),
        });
    } catch (error) {
        console.error("Trial status error:", error);
        return NextResponse.json({ error: "Invalid token" }, { status: 401 });
    }
}
