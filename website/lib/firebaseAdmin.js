/**
 * Firebase Admin SDK — server-side only (API routes).
 * Used to verify ID tokens and read Firestore.
 */
import admin from "firebase-admin";

if (!admin.apps.length) {
    const serviceAccount = JSON.parse(process.env.FIREBASE_SERVICE_ACCOUNT_KEY || "{}");
    admin.initializeApp({
        credential: admin.credential.cert(serviceAccount),
    });
}

export const adminAuth = admin.auth();
export const adminDb = admin.firestore();
export default admin;
