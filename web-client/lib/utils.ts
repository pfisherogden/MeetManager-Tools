import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
	return twMerge(clsx(inputs));
}

export function setCookie(name: string, value: string, maxAgeSeconds: number) {
	document.cookie = `${name}=${value}; path=/; max-age=${maxAgeSeconds}`;
}

export function formatAgeGroup(low: number, high: number): string {
	if (low === 0 && high === 0) return "Open";
	if (low === 0 && high > 0) return `${high} & under`;
	if (low > 0 && (high === 0 || high >= 99)) return `${low} & over`;
	return `${low}-${high}`;
}
