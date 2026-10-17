import { act, renderHook, waitFor } from "@testing-library/react";
import Cookies from "js-cookie";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { getGoogleConfig } from "@/app/actions";
import { useGooglePicker } from "./use-google-picker";

vi.mock("@/app/actions", () => ({
	getGoogleConfig: vi.fn(),
}));

vi.mock("js-cookie", () => ({
	default: {
		get: vi.fn(),
		set: vi.fn(),
	},
}));

const mockSignInWithPopup = vi.fn();
const mockCredentialFromResult = vi.fn();

vi.mock("firebase/auth", () => ({
	signInWithPopup: (...args: any[]) => mockSignInWithPopup(...args),
	GoogleAuthProvider: {
		credentialFromResult: (...args: any[]) => mockCredentialFromResult(...args),
	},
}));

vi.mock("@/lib/firebase", () => ({
	auth: { name: "mock-auth" },
	googleProvider: { providerId: "google.com" },
}));

describe("useGooglePicker", () => {
	let lastCallback: ((data: any) => void) | null = null;
	let mockSetVisible: ReturnType<typeof vi.fn>;
	let mockAddView: ReturnType<typeof vi.fn>;
	let mockSetOAuthToken: ReturnType<typeof vi.fn>;
	let mockSetDeveloperKey: ReturnType<typeof vi.fn>;
	let mockSetAppId: ReturnType<typeof vi.fn>;
	let mockSetOrigin: ReturnType<typeof vi.fn>;
	let mockSetIncludeFolders: ReturnType<typeof vi.fn>;
	let mockSetSelectFolderEnabled: ReturnType<typeof vi.fn>;

	beforeEach(() => {
		vi.clearAllMocks();
		lastCallback = null;
		mockSetVisible = vi.fn();
		mockAddView = vi.fn().mockReturnThis();
		mockSetOAuthToken = vi.fn().mockReturnThis();
		mockSetDeveloperKey = vi.fn().mockReturnThis();
		mockSetAppId = vi.fn().mockReturnThis();
		mockSetOrigin = vi.fn().mockReturnThis();
		mockSetIncludeFolders = vi.fn().mockReturnThis();
		mockSetSelectFolderEnabled = vi.fn().mockReturnThis();

		(window as any).google = {
			picker: {
				ViewId: { DOCS: "docs" },
				Action: { PICKED: "picked", CANCEL: "cancel" },
				DocsView: vi.fn().mockImplementation(function (this: any) {
					this.setIncludeFolders = mockSetIncludeFolders;
					this.setSelectFolderEnabled = mockSetSelectFolderEnabled;
					return this;
				}),
				PickerBuilder: vi.fn().mockImplementation(function (this: any) {
					this.addView = mockAddView;
					this.setOAuthToken = mockSetOAuthToken;
					this.setDeveloperKey = mockSetDeveloperKey;
					this.setAppId = mockSetAppId;
					this.setOrigin = mockSetOrigin;
					this.setCallback = vi.fn((cb: (data: any) => void) => {
						lastCallback = cb;
						return this;
					});
					this.build = vi.fn(() => ({
						setVisible: mockSetVisible,
					}));
					return this;
				}),
			},
		};
	});

	it("loads config and configures PickerBuilder with DocsView and access token", async () => {
		(getGoogleConfig as any).mockResolvedValue({
			apiKey: "test-google-api-key",
			appId: "99887766",
		});
		(Cookies.get as any).mockReturnValue("cookie-oauth-token");

		const onFileSelect = vi.fn();
		const { result } = renderHook(() => useGooglePicker({ onFileSelect }));

		await waitFor(() => {
			expect(result.current.isLoaded).toBe(true);
			expect(getGoogleConfig).toHaveBeenCalled();
		});
		await act(async () => {
			await Promise.resolve();
		});

		await act(async () => {
			await result.current.openPicker();
		});

		expect(mockSetIncludeFolders).toHaveBeenCalledWith(true);
		expect(mockSetSelectFolderEnabled).toHaveBeenCalledWith(false);
		expect(mockSetOAuthToken).toHaveBeenCalledWith("cookie-oauth-token");
		expect(mockSetDeveloperKey).toHaveBeenCalledWith("test-google-api-key");
		expect(mockSetAppId).toHaveBeenCalledWith("99887766");
		expect(mockSetVisible).toHaveBeenCalledWith(true);

		// Simulate file picked in Google Picker
		act(() => {
			lastCallback?.({
				action: "picked",
				docs: [
					{
						id: "drive-doc-42",
						name: "LeagueChampionships.mdb",
						mimeType: "application/x-msaccess",
						sizeBytes: 204800,
					},
				],
			});
		});

		expect(onFileSelect).toHaveBeenCalledWith({
			id: "drive-doc-42",
			name: "LeagueChampionships.mdb",
			mimeType: "application/x-msaccess",
			sizeBytes: 204800,
			accessToken: "cookie-oauth-token",
		});
	});

	it("handles null getGoogleConfig response in Tauri/offline mode without crashing", async () => {
		(getGoogleConfig as any).mockResolvedValue(null);
		(Cookies.get as any).mockReturnValue("tauri-token");

		const onFileSelect = vi.fn();
		const { result } = renderHook(() => useGooglePicker({ onFileSelect }));

		await waitFor(() => {
			expect(result.current.isLoaded).toBe(true);
		});

		await act(async () => {
			await result.current.openPicker();
		});

		expect(mockSetOAuthToken).toHaveBeenCalledWith("tauri-token");
		expect(mockSetVisible).toHaveBeenCalledWith(true);
	});

	it("authenticates via Firebase signInWithPopup when no accessToken cookie is present", async () => {
		(getGoogleConfig as any).mockResolvedValue({
			apiKey: "test-api-key",
			appId: "12345",
		});
		(Cookies.get as any).mockReturnValue(undefined);
		mockSignInWithPopup.mockResolvedValue({ user: { uid: "u1" } });
		mockCredentialFromResult.mockReturnValue({
			accessToken: "popup-fresh-token",
		});

		const onFileSelect = vi.fn();
		const { result } = renderHook(() => useGooglePicker({ onFileSelect }));

		await waitFor(() => {
			expect(result.current.isLoaded).toBe(true);
		});

		await act(async () => {
			await result.current.openPicker();
		});

		expect(mockSignInWithPopup).toHaveBeenCalled();
		expect(Cookies.set).toHaveBeenCalledWith(
			"googleAccessToken",
			"popup-fresh-token",
			expect.objectContaining({ path: "/" }),
		);
		expect(mockSetOAuthToken).toHaveBeenCalledWith("popup-fresh-token");
		expect(mockSetVisible).toHaveBeenCalledWith(true);
	});
});
