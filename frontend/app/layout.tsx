import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Product Image Extractor",
  description: "Extract and analyze product images from YouTube videos",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}

