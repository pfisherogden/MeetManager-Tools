import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
	return twMerge(clsx(inputs));
}

export function setCookie(name: string, value: string, maxAgeSeconds: number) {
	document.cookie = `${name}=${value}; path=/; max-age=${maxAgeSeconds}`;
}
