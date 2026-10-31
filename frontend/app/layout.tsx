import type { Metadata } from "next";
import "./globals.css";
import { Sidebar } from "../components/sidebar";
export const metadata: Metadata = { title:"NetCoop — Network Operations", description:"Evidence-first campus network diagnostics" };
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body><div className="shell"><Sidebar/><main className="content">{children}</main></div></body></html>;
}
