import React from "react";
import type { Metadata } from "next";
import { Inter, Space_Grotesk } from "next/font/google";
import "./globals.css";
// import { ClerkProvider } from "@clerk/nextjs";
import { ChatProvider } from "@/components/providers/chat-provider";
import { ThemeProvider } from "@/components/providers/theme-provider";
import { ToastProvider } from "@/components/providers/toast-provider";

const inter = Inter({ subsets: ["latin"] });
const spaceGrotesk = Space_Grotesk({
  subsets: ["latin"],
  variable: "--font-space-grotesk",
});

export const metadata: Metadata = {
  title: "AI Agent App",
  description: "A FastAPI + Next.js AI agent application",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    // <ClerkProvider>
      <html lang="en" className="dark">
        <body
          className={`${inter.className} ${spaceGrotesk.variable} bg-gray-950 text-white antialiased`}
        >
          <ThemeProvider>
            <ToastProvider>
              <ChatProvider>{children}</ChatProvider>
            </ToastProvider>
          </ThemeProvider>
        </body>
      </html>
    // </ClerkProvider>
  );
}
