import type { Metadata } from "next";
import { cookies } from "next/headers";
import { Providers } from "@/components/providers";
import { Shell } from "@/components/shell";
import "@fontsource-variable/inter";
import "@/styles/globals.css";
export const dynamic = "force-dynamic";
export const metadata: Metadata = {
  title: "fireflies · Meeting workspace",
  description:
    "An unofficial meeting workspace demonstration with synthetic data.",
};
export default async function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  const value = (await cookies()).get("meeting-theme")?.value;
  const motion = (await cookies()).get("meeting-motion")?.value === "true";
  const theme = value === "dark" || value === "light" ? value : "system";
  return (
    <html lang="en" data-theme={theme} data-reduced-motion={motion}>
      <body>
        <Providers>
          <Shell>{children}</Shell>
        </Providers>
      </body>
    </html>
  );
}
