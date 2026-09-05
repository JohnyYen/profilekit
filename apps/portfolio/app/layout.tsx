import type { Metadata } from "next";
import { JetBrains_Mono } from "next/font/google";
import "./globals.css";

const jetbrainsMono = JetBrains_Mono({
  variable: "--font-jetbrains-mono",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  display: "swap",
});

const siteUrl = "https://johnyyen.dev";
const siteName = "Terminal Portfolio";
const description = "Interactive terminal-style portfolio of Johny A. Pedraza Romero — Backend Engineer. Explore projects, skills, and contact info through a custom terminal interface.";
const title = "Terminal Portfolio | Johny A. Pedraza Romero";

export const metadata: Metadata = {
  title: {
    default: title,
    template: "%s | Terminal Portfolio",
  },
  description,
  keywords: [
    "backend engineer", "software developer", "portfolio",
    "terminal", "Next.js", "TypeScript", "FastAPI", "NestJS",
    "Johny Pedraza", "Jhonny Antonio",
  ],
  authors: [{ name: "Johny A. Pedraza Romero" }],
  creator: "Johny A. Pedraza Romero",
  metadataBase: new URL(siteUrl),
  openGraph: {
    type: "website",
    locale: "en_US",
    alternateLocale: "es_ES",
    url: siteUrl,
    siteName,
    title,
    description,
    images: [{
      url: "/favicon.svg",
      width: 24,
      height: 24,
      alt: "Terminal Portfolio — Dragon Icon",
    }],
  },
  twitter: {
    card: "summary",
    title,
    description,
    images: ["/favicon.svg"],
    creator: "@johnyyen",
  },
  icons: {
    icon: [
      { url: "/favicon.svg", type: "image/svg+xml" },
    ],
  },
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      "max-video-preview": -1,
      "max-image-preview": "large",
      "max-snippet": -1,
    },
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${jetbrainsMono.variable} h-full antialiased`}
      style={{ colorScheme: 'dark' }}
    >
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <meta name="theme-color" content="#0a0a0a" />
        <meta name="google-site-verification" content="" />
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{
            __html: JSON.stringify({
              "@context": "https://schema.org",
              "@type": "Person",
              name: "Johny A. Pedraza Romero",
              alternateName: "Johny Yen",
              url: "https://johnyyen.dev",
              jobTitle: "Backend Engineer",
              knowsAbout: ["Software Architecture", "Backend Development", "API Design", "TypeScript", "Python", "NestJS", "FastAPI"],
              sameAs: [
                "https://github.com/JohnyYen",
                "https://linkedin.com/in/johnyyen",
              ],
            }),
          }}
        />
      </head>
      <body className="min-h-screen bg-[#0a0a0a] text-[var(--text-primary)]">
        {children}
      </body>
    </html>
  );
}