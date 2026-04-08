"use client";

import { Toaster as SonnerToaster } from "@/components/ui/sonner";
import { Toaster } from "@/components/ui/toaster";
import { AuthProvider } from "@/hooks/use-auth";

export function Providers({ children }: { children: React.ReactNode }) {
	return (
		<AuthProvider>
			{children}
			<Toaster />
			<SonnerToaster />
		</AuthProvider>
	);
}
