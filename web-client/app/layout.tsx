import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { ClientLayout } from "./client-layout";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });

export const metadata: Metadata = {
	title: "Meet Manager Tools",
	description: "Tools for managing swim meets",
};

export default function RootLayout({
	children,
}: Readonly<{
	children: React.ReactNode;
}>) {
	return (
		<html lang="en" suppressHydrationWarning>
			<body className={`${inter.variable} font-sans antialiased`}>
				<ClientLayout>{children}</ClientLayout>
			</body>
		</html>
	);
}
