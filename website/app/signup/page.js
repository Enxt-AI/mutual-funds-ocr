"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { signUp } from "../../lib/firebase";
import styles from "./page.module.css";

export default function SignupPage() {
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [confirmPassword, setConfirmPassword] = useState("");
    const [error, setError] = useState("");
    const [loading, setLoading] = useState(false);
    const router = useRouter();

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError("");

        if (password.length < 6) {
            setError("Password must be at least 6 characters.");
            return;
        }
        if (password !== confirmPassword) {
            setError("Passwords do not match.");
            return;
        }

        setLoading(true);
        try {
            await signUp(email, password);
            router.push("/");
        } catch (err) {
            if (err.code === "auth/email-already-in-use") {
                setError("An account with this email already exists.");
            } else if (err.code === "auth/weak-password") {
                setError("Password is too weak. Use at least 6 characters.");
            } else {
                setError(err.message || "Signup failed.");
            }
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className={styles.authPage}>
            <div className={styles.authCard}>
                <div className={styles.authHeader}>
                    <span className={styles.authIcon}>🚀</span>
                    <h1 className={styles.authTitle}>Start Free Trial</h1>
                    <p className={styles.authSub}>Get 30 minutes of full access to all fund data</p>
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
                            placeholder="At least 6 characters"
                            className={styles.input}
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            required
                            minLength={6}
                        />
                    </div>
                    <div className={styles.inputGroup}>
                        <label className={styles.inputLabel}>Confirm Password</label>
                        <input
                            type="password"
                            placeholder="Repeat password"
                            className={styles.input}
                            value={confirmPassword}
                            onChange={(e) => setConfirmPassword(e.target.value)}
                            required
                        />
                    </div>
                    <button type="submit" className={styles.authBtn} disabled={loading}>
                        {loading ? "Creating Account..." : "Create Account"}
                    </button>
                </form>
                <div className={styles.authFooter}>
                    Already have an account? <a href="/login" className={styles.authLink}>Sign in</a>
                </div>
                <div className={styles.trialNote}>
                    <span>⏱️</span> Your 30-minute free trial starts immediately after sign up
                </div>
            </div>
        </div>
    );
}
