"use client";

import "./globals.css";
import { AuthProvider, useAuth } from "./contexts/AuthContext";
import { LogIn, LogOut, Clock } from "lucide-react";

function Navbar() {
  const { user, loading, trialMinutesLeft, trialExpired, logout } = useAuth();

  return (
    <nav className="navbar">
      <div className="nav-container">
        <a href="/" className="nav-logo">
          <span className="logo-icon">📊</span>
          <span className="logo-text">MutualFund<span className="logo-accent">Tracker</span></span>
        </a>
        <div className="nav-links">
          <a href="/?tab=compare" className="nav-link">Compare Funds</a>
          {!loading && (
            <>
              {user && !trialExpired && trialMinutesLeft != null && (
                <span className="trial-badge">
                  <Clock size={12} />
                  {trialMinutesLeft} min left
                </span>
              )}
              {user && trialExpired && (
                <span className="trial-badge trial-expired">
                  Trial Expired
                </span>
              )}
              {user ? (
                <button className="nav-auth-btn" onClick={logout} title="Sign out">
                  <LogOut size={16} />
                  <span>Logout</span>
                </button>
              ) : (
                <a href="/login" className="nav-auth-btn nav-login-btn">
                  <LogIn size={16} />
                  <span>Login</span>
                </a>
              )}
            </>
          )}
        </div>
      </div>
    </nav>
  );
}

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <head>
        <title>MutualFund Tracker — Premium Fund Analytics</title>
        <meta name="description" content="Track, analyze, and compare mutual fund performance with real-time NAV data, portfolio holdings, and risk metrics." />
      </head>
      <body>
        <AuthProvider>
          <Navbar />
          <main className="main-content">
            {children}
          </main>
          <footer className="footer">
            <div className="footer-container">
              <p>Data sourced from AMC Factsheets &amp; NSE India • For educational purposes only</p>
            </div>
          </footer>
        </AuthProvider>
      </body>
    </html>
  );
}
