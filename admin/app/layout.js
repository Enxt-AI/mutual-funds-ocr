import "./globals.css";

export const metadata = {
    title: "Admin Panel — MutualFund Tracker",
    description: "Upload factsheets and manage fund data",
};

export default function RootLayout({ children }) {
    return (
        <html lang="en">
            <body>{children}</body>
        </html>
    );
}
