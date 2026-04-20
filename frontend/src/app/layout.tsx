import type { Metadata } from "next";
import { Inter, Playfair_Display } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });
const playfair = Playfair_Display({ subsets: ["latin"], variable: "--font-playfair" });

export const metadata: Metadata = {
  title: "MoneyPrinter Studio — AI Video Generator",
  description: "Create viral short-form videos in minutes with AI. TikTok, YouTube Shorts, Instagram Reels — automated.",
  keywords: "AI video generator, TikTok, YouTube Shorts, short-form video, automated content",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${inter.variable} ${playfair.variable}`}>
      <body className="min-h-screen bg-[var(--bg-primary)]">
        {children}
      </body>
    </html>
  );
}
