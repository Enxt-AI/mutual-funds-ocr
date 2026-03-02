"use client";

import { createContext, useContext, useState, useEffect } from "react";
import { onAuthChange, getIdToken, logOut } from "../../lib/firebase";

const AuthContext = createContext({
    user: null,
    loading: true,
    trialMinutesLeft: null,
    trialExpired: false,
    logout: async () => { },
});

export function AuthProvider({ children }) {
    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(true);
    const [trialMinutesLeft, setTrialMinutesLeft] = useState(null);
    const [trialExpired, setTrialExpired] = useState(false);

    useEffect(() => {
        const unsub = onAuthChange(async (fbUser) => {
            if (fbUser) {
                setUser(fbUser);
                // Check trial status
                try {
                    const token = await fbUser.getIdToken();
                    const res = await fetch("/api/auth/trial-status", {
                        headers: { Authorization: `Bearer ${token}` },
                    });
                    if (res.ok) {
                        const data = await res.json();
                        setTrialMinutesLeft(data.minutesLeft);
                        setTrialExpired(data.expired);
                    }
                } catch (e) {
                    console.error("Trial status check failed:", e);
                }
            } else {
                setUser(null);
                setTrialMinutesLeft(null);
                setTrialExpired(false);
            }
            setLoading(false);
        });
        return () => unsub();
    }, []);

    const logout = async () => {
        await logOut();
        setUser(null);
        setTrialDaysLeft(null);
        setTrialExpired(false);
    };

    return (
        <AuthContext.Provider value={{ user, loading, trialMinutesLeft, trialExpired, logout }}>
            {children}
        </AuthContext.Provider>
    );
}

export function useAuth() {
    return useContext(AuthContext);
}
