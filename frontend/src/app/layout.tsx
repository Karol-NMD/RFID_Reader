import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Link from "next/link";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "TagIt",
  description: "Developed by Nanosatellite Missions Design Ltd",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
      >
        <nav className="bg-blue-700 text-white px-6 py-3 flex justify-between items-center">
          <h1 className="text-xl font-bold">📶 TagIt</h1>
          <div className="space-x-4">
            <Link href="/" className="hover:underline">Dashboard</Link>
            <Link href="/export" className="hover:underline">Export</Link>
          </div>
        </nav>
        <main className="p-4">{children}</main>
      </body>
    </html>
  );
}
