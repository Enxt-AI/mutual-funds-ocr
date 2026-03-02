"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { signIn } from "../../lib/firebase";
import styles from "./page.module.css";

export default function LoginPage() {
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [error, setError] = useState("");
    const [loading, setLoading] = useState(false);
    const router = useRouter();

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError("");
        setLoading(true);
        try {
            await signIn(email, password);
            router.push("/");
        } catch (err) {
            if (err.code === "auth/user-disabled") {
                setError("This account's trial has expired.");
            } else if (err.code === "auth/invalid-credential" || err.code === "auth/wrong-password" || err.code === "auth/user-not-found") {
                setError("Invalid email or password.");
            } else {
                setError(err.message || "Login failed.");
            }
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className={styles.authPage}>
            <div className={styles.authCard}>
                <div className={styles.authHeader}>
                    <span className={styles.authIcon}>🔐</span>
                    <h1 className={styles.authTitle}>Welcome Back</h1>
                    <p className={styles.authSub}>Sign in to access fund analytics</p>
                </div>
                <form onSubmit={handleSubmit} className={styles.authForm}>
                    {error && <div className={styles.authError}>{error}</div>}
                    <div className={styles.inputGroup}>
                        <label className={styles.inputLabel}>Email</label>
                        <input
                            type="email"
                            placeholder="you@example.com"
                            className={styles.input}
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            required
                        />
                    </div>
                    <div className={styles.inputGroup}>
                        <label className={styles.inputLabel}>Password</label>
                        <input
                            type="password"
                            placeholder="••••••••"
                            className={styles.input}
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            required
                        />
                    </div>
                    <button type="submit" className={styles.authBtn} disabled={loading}>
                        {loading ? "Signing in..." : "Sign In"}
                    </button>
                </form>
                <div className={styles.authFooter}>
                    Don&apos;t have an account? <a href="/signup" className={styles.authLink}>Create one — 3 days free</a>
                </div>
            </div>
        </div>
    );
}
