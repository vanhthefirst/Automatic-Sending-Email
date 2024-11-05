import React from 'react';
import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'CSV Upload Portal',
  description: 'Upload and process CSV files',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  function cn(...classes: string[]): string {
    return classes.filter(Boolean).join(' ')
  }
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={cn(
        "min-h-screen bg-background font-sans antialiased",
        inter.className
      )}>
        {children}
      </body>
    </html>
  )
}