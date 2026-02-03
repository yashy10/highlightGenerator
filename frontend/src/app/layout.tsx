import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Highlight Generator",
  description: "AI-powered sports highlight generator",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="bg-zinc-950 text-zinc-100 antialiased">{children}</body>
    </html>
  );
}
