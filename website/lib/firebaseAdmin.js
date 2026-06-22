/**
 * Firebase Admin SDK — server-side only (API routes).
 * Used to verify ID tokens and read Firestore.
 */
import admin from "firebase-admin";

if (!admin.apps.length) {
    try {
        const key = process.env.FIREBASE_SERVICE_ACCOUNT_KEY;
        if (key && key.trim()) {
            const serviceAccount = JSON.parse(key);
            admin.initializeApp({
                credential: admin.credential.cert(serviceAccount),
            });
        } else {
            admin.initializeApp({
                projectId: process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID || "mock-app"
            });
        }
    } catch (e) {
        console.warn("Firebase Admin SDK failed to initialize:", e.message);
        try {
            admin.initializeApp({
                projectId: "mock-app"
            });
        } catch (_) {}
    }
}

export const adminAuth = admin.auth();
export const adminDb = admin.firestore();
export default admin;
