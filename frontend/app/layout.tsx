import type { Metadata } from "next";
import { Crimson_Pro, Plus_Jakarta_Sans } from "next/font/google";
import "./globals.css";

const crimson = Crimson_Pro({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-crimson",
  display: "swap",
});

const jakarta = Plus_Jakarta_Sans({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-jakarta",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Carnatify — Identify, understand, and savour Carnatic music",
  description:
    "Carnatify identifies the raga and composition of a Carnatic performance and unfolds its meaning — bridging centuries of tradition with the ear of a machine.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={`${crimson.variable} ${jakarta.variable}`}>
      <body className="grain min-h-[100dvh]">{children}</body>
    </html>
  );
}
