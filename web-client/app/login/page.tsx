"use client";

import { LogIn, Waves } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import {
	Card,
	CardContent,
	CardDescription,
	CardHeader,
	CardTitle,
} from "@/components/ui/card";
import { useAuth } from "@/hooks/use-auth";

export default function LoginPage() {
	const { user, login, loading } = useAuth();
	const router = useRouter();
	const searchParams = useSearchParams();
	const [error, setError] = useState<string | null>(null);
	const [isLoggingIn, setIsLoggingIn] = useState(false);

	const returnUrl = searchParams.get("returnUrl") || "/";

	useEffect(() => {
		if (!loading && user) {
			router.push(returnUrl);
		}
	}, [user, loading, router, returnUrl]);

	const handleLogin = async () => {
		setIsLoggingIn(true);
		setError(null);
		try {
			await login();
			// router.push(returnUrl) will be handled by useEffect
		} catch (e: any) {
			console.error("Login failed", e);
			setError(e.message || "Failed to sign in with Google");
			setIsLoggingIn(false);
		}
	};

	if (loading) {
		return (
			<div className="flex min-h-screen items-center justify-center bg-muted/50">
				<div className="animate-pulse flex flex-col items-center gap-4">
					<Waves className="h-12 w-12 text-primary" />
					<p className="text-sm text-muted-foreground font-medium">
						Loading...
					</p>
				</div>
			</div>
		);
	}

	return (
		<div className="flex min-h-screen items-center justify-center bg-muted/50 p-4">
			<Card className="w-full max-w-md shadow-xl border-t-4 border-t-primary">
				<CardHeader className="space-y-1 flex flex-col items-center text-center pb-8">
					<div className="w-16 h-16 rounded-2xl bg-primary flex items-center justify-center mb-4 shadow-inner">
						<Waves className="h-10 w-10 text-primary-foreground" />
					</div>
					<CardTitle className="text-3xl font-bold tracking-tight">
						MMTools
					</CardTitle>
					<CardDescription className="text-base">
						Swim Meet Data Management
					</CardDescription>
				</CardHeader>
				<CardContent className="space-y-6">
					{error && (
						<div className="p-3 text-sm bg-destructive/10 border border-destructive/20 text-destructive rounded-lg">
							{error}
						</div>
					)}

					<div className="space-y-4">
						<p className="text-sm text-center text-muted-foreground px-4">
							Sign in with your Google account to access your swim meet datasets
							and reports.
						</p>
						<Button
							className="w-full h-12 text-base font-semibold gap-3 shadow-sm hover:shadow-md transition-all"
							size="lg"
							onClick={handleLogin}
							disabled={isLoggingIn}
						>
							{isLoggingIn ? (
								<div className="h-5 w-5 border-2 border-primary-foreground/30 border-t-primary-foreground rounded-full animate-spin" />
							) : (
								<LogIn className="h-5 w-5" />
							)}
							Sign in with Google
						</Button>
					</div>

					<div className="text-center space-y-4">
						<p className="text-xs text-muted-foreground font-medium">
							Your data is automatically sandboxed to your account.
						</p>
						{process.env.NEXT_PUBLIC_BUILD_TIME && (
							<p className="text-[10px] text-muted-foreground/40 font-mono">
								Build:{" "}
								{new Date(process.env.NEXT_PUBLIC_BUILD_TIME).toLocaleString()}
							</p>
						)}
					</div>
				</CardContent>
			</Card>
		</div>
	);
}
