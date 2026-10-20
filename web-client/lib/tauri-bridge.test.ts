import { describe, expect, it, vi } from "vitest";
import { downloadFile } from "./tauri-bridge";

describe("downloadFile browser fallback (#629)", () => {
	it("stops click propagation on synthetic download links so NextTopLoader spinner does not trigger", async () => {
		const documentClickSpy = vi.fn();
		document.addEventListener("click", documentClickSpy);

		try {
			await downloadFile(
				"meet_reports_2026.zip",
				"/api/data?path=users/u1/published/bundles/meet_reports_2026.zip&token=abc",
			);

			expect(documentClickSpy).not.toHaveBeenCalled();
		} finally {
			document.removeEventListener("click", documentClickSpy);
		}
	});
});
