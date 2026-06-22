/**
 * Firebase Client SDK — browser-side initialization.
 * Uses NEXT_PUBLIC_ env vars so they're available in client components.
 */
import { initializeApp, getApps } from "firebase/app";
import { getAuth, createUserWithEmailAndPassword, signInWithEmailAndPassword, signOut as fbSignOut, onAuthStateChanged } from "firebase/auth";
import { getFirestore, doc, setDoc, getDoc, serverTimestamp } from "firebase/firestore";

const firebaseConfig = {
    apiKey: process.env.NEXT_PUBLIC_FIREBASE_API_KEY || "AIzaSyFakeKeyPlaceholderHere12345",
    authDomain: process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN || "mock-app.firebaseapp.com",
    projectId: process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID || "mock-app",
    storageBucket: process.env.NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET || "mock-app.appspot.com",
    messagingSenderId: process.env.NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID || "1234567890",
    appId: process.env.NEXT_PUBLIC_FIREBASE_APP_ID || "1:1234567890:web:abcdef123456",
};

// Initialize Firebase (prevent re-init in hot reload)
const app = getApps().length === 0 ? initializeApp(firebaseConfig) : getApps()[0];
const auth = getAuth(app);
const db = getFirestore(app);

/**
 * Sign up a new user and store their createdAt timestamp in Firestore.
 */
export async function signUp(email, password) {
    const cred = await createUserWithEmailAndPassword(auth, email, password);
    // Store trial start in Firestore
    await setDoc(doc(db, "users", cred.user.uid), {
        email: cred.user.email,
        createdAt: serverTimestamp(),
    });
    return cred.user;
}

/**
 * Sign in an existing user.
 */
export async function signIn(email, password) {
    const cred = await signInWithEmailAndPassword(auth, email, password);
    return cred.user;
}

/**
 * Sign out the current user.
 */
export async function logOut() {
    await fbSignOut(auth);
}

/**
 * Listen for auth state changes.
 */
export function onAuthChange(callback) {
    return onAuthStateChanged(auth, callback);
}

/**
 * Get the current user's ID token (for server-side verification).
 */
export async function getIdToken() {
    const user = auth.currentUser;
    if (!user) return null;
    return user.getIdToken();
}

export { auth, db };
