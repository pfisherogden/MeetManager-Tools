"use client";

import { Waves } from "lucide-react";
import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";
import { useAuth } from "@/hooks/use-auth";

export function AuthGuard({ children }: { children: React.ReactNode }) {
	const { user, loading } = useAuth();
	const router = useRouter();
	const pathname = usePathname();

	const isAuthDisabled =
		process.env.NEXT_PUBLIC_AUTH_DISABLED === "true" ||
		process.env.NEXT_PUBLIC_E2E_AUTH_BYPASS === "true";

	if (isAuthDisabled) {
		return <>{children}</>;
	}

	useEffect(() => {
		if (isAuthDisabled) return;
		if (!loading && !user && pathname !== "/login") {
			router.push(`/login?returnUrl=${encodeURIComponent(pathname)}`);
		}
	}, [user, loading, router, pathname, isAuthDisabled]);

	if (loading) {
		return (
			<div className="flex min-h-screen items-center justify-center bg-background">
				<div className="animate-pulse flex flex-col items-center gap-4">
					<Waves className="h-12 w-12 text-primary" />
					<p className="text-sm text-muted-foreground font-medium">
						Authenticating...
					</p>
				</div>
			</div>
		);
	}

	if (!user && pathname !== "/login") {
		return null; // Will redirect in useEffect
	}

	return <>{children}</>;
}
