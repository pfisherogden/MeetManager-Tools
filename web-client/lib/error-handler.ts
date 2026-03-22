import { toast } from "sonner";

/**
 * Handles errors from Next.js Server Actions.
 * Specifically detects "Failed to find Server Action" which occurs after a new deployment,
 * and prompts the user to refresh their browser.
 */
export function handleActionError(error: unknown, fallbackMessage: string) {
	console.error(error);
	const message = error instanceof Error ? error.message : String(error);

	if (
		message.includes("Failed to find Server Action") ||
		message.includes("was not found on the server") ||
		message.includes("Token expired") ||
		message.includes("Authentication required")
	) {
		toast.error("New version available", {
			description:
				"A new version of the app was recently deployed. Please refresh your browser to continue.",
			duration: 10000,
			action: {
				label: "Refresh Now",
				onClick: () => window.location.reload(),
			},
		});
		return;
	}

	toast.error(`${fallbackMessage}: ${message}`);
}
