import type { Metadata } from "next";
import "@fontsource-variable/inter";
import "@/styles/globals.css";
export const metadata: Metadata = {
  title: "fireflies · Meeting workspace",
  description:
    "An unofficial meeting workspace demonstration with synthetic data.",
};
export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
