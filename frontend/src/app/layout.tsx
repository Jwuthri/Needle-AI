import React from "react";
import type { Metadata } from "next";
import { Inter, Space_Grotesk, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import { ClerkProvider } from "@clerk/nextjs";
import { ChatProvider } from "@/components/providers/chat-provider";
import { ThemeProvider } from "@/components/providers/theme-provider";
import { ToastProvider } from "@/components/providers/toast-provider";
import { AppLayout } from "@/components/layout/app-layout";

const inter = Inter({ subsets: ["latin"] });
const spaceGrotesk = Space_Grotesk({
  subsets: ["latin"],
  variable: "--font-space-grotesk",
});
const jetBrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-jetbrains-mono",
});

export const metadata: Metadata = {
  title: "NeedleAI - Product Review Analysis",
  description: "AI-powered product review analysis platform",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <ClerkProvider
      appearance={{
        baseTheme: {
          dark: true,
        },
        variables: {
          colorPrimary: '#10b981',
          colorBackground: '#030712',
          colorText: '#ffffff',
          colorInputBackground: '#1f2937',
          colorInputText: '#ffffff',
        },
        elements: {
          formButtonPrimary: 'bg-emerald-600 hover:bg-emerald-700',
          card: 'bg-gray-900 border-gray-800',
        },
      }}
    >
      <html lang="en" className="dark">
        <body
          className={`${inter.className} ${spaceGrotesk.variable} ${jetBrainsMono.variable} bg-gray-950 text-white antialiased`}
        >
          <ThemeProvider>
            <ToastProvider>
              <ChatProvider>
                <AppLayout>{children}</AppLayout>
              </ChatProvider>
            </ToastProvider>
          </ThemeProvider>
        </body>
      </html>
    </ClerkProvider>
  );
}
