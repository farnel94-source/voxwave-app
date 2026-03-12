import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
  display: "swap",
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "VoxWave — Dictée vocale intelligente pour Windows & Linux",
  description:
    "Parle, VoxWave écrit. Dictée vocale avec nettoyage IA, injection instantanée et mode hors-ligne. Gratuit.",
  keywords: [
    "dictée vocale",
    "voice to text",
    "speech to text",
    "Windows",
    "Linux",
    "Whisper",
    "IA",
  ],
  openGraph: {
    title: "VoxWave — Parle. VoxWave écrit.",
    description:
      "Dictée vocale intelligente avec nettoyage IA. Gratuit pour Windows & Linux.",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="fr" className={`${geistSans.variable} ${geistMono.variable}`}>
      <body className="antialiased">{children}</body>
    </html>
  );
}
