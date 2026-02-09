import type { Metadata } from "next";
import Link from "next/link";
import { ProjectProvider } from "@/components/ProjectProvider";
import "./globals.css";

export const metadata: Metadata = {
  title: "Solar Pile Design Tool",
  description: "Axial capacity, lateral p-y analysis, group effects, ASCE 7 load combinations",
};

const NAV_ITEMS = [
  { href: "/", label: "Project Setup" },
  { href: "/soil-profile", label: "Soil Profile" },
  { href: "/pile-properties", label: "Pile Properties" },
  { href: "/loading", label: "Loading" },
  { href: "/axial-capacity", label: "Axial Capacity" },
  { href: "/lateral-analysis", label: "Lateral Analysis" },
  { href: "/group-analysis", label: "Group Analysis" },
];

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-gray-50 text-gray-900 min-h-screen flex">
        <ProjectProvider>
          {/* Sidebar */}
          <aside className="w-64 bg-gray-900 text-white min-h-screen p-4 flex-shrink-0">
            <h1 className="text-lg font-bold mb-1">Solar Pile Design</h1>
            <p className="text-xs text-gray-400 mb-6">Foundation Analysis Tool</p>
            <nav className="space-y-1">
              {NAV_ITEMS.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  className="block px-3 py-2 rounded text-sm hover:bg-gray-700 transition-colors"
                >
                  {item.label}
                </Link>
              ))}
            </nav>
          </aside>

          {/* Main content */}
          <main className="flex-1 p-8 overflow-auto">
            {children}
          </main>
        </ProjectProvider>
      </body>
    </html>
  );
}
