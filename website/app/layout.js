import "./globals.css";

export const metadata = {
  title: "MutualFund Tracker — Premium Fund Analytics",
  description: "Track, analyze, and compare mutual fund performance with real-time NAV data, portfolio holdings, and risk metrics.",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>
        <nav className="navbar">
          <div className="nav-container">
            <a href="/" className="nav-logo">
              <span className="logo-icon">📊</span>
              <span className="logo-text">MutualFund<span className="logo-accent">Tracker</span></span>
            </a>
            <div className="nav-links">
              <a href="/?tab=compare" className="nav-link">Compare Funds</a>
            </div>
          </div>
        </nav>
        <main className="main-content">
          {children}
        </main>
        <footer className="footer">
          <div className="footer-container">
            <p>Data sourced from AMC Factsheets & NSE India • For educational purposes only</p>
          </div>
        </footer>
      </body>
    </html >
  );
}
