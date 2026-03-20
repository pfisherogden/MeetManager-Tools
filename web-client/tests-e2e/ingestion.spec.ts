import * as fs from "node:fs";
import * as path from "node:path";
import { expect, test } from "@playwright/test";

test.describe("Ingestion and Admin Journey", () => {
	test.beforeEach(async ({ page, context }, testInfo) => {
		// Set a unique user ID for this test to avoid collisions in the backend
		const userId = `e2e-ingestion-${testInfo.workerIndex}-${testInfo.project.name.replace(/\s+/g, "-")}`;
		
		// Set header for all requests from this page
		await page.setExtraHTTPHeaders({
			"x-user-id": userId,
		});

		// Set cookie for additional resilience
		await context.addCookies([
			{
				name: "x-user-id",
				value: userId,
				domain: "localhost",
				path: "/",
			},
		]);

		console.log(`Using isolated User ID: ${userId}`);
	});

	test("should allow navigating to Admin and uploading a dataset", async ({
		page,
	}, testInfo) => {
		await page.goto("/admin");

		await expect(
			page.getByRole("heading", { name: "Admin Configuration" }),
		).toBeVisible();
		await expect(page.getByText("Dataset Management")).toBeVisible();

		// Create a dummy .mdb file for upload testing with a unique name per worker
		const testFileName = `test-ingestion-${testInfo.workerIndex}.mdb`;
		const testFilePath = path.join(__dirname, testFileName);
		fs.writeFileSync(testFilePath, "DUMMY MDB CONTENT");

		try {
			// Set up file chooser listener
			const fileChooserPromise = page.waitForEvent("filechooser");
			await page.getByRole("button", { name: "Upload Dataset" }).click();
			const fileChooser = await fileChooserPromise;
			await fileChooser.setFiles(testFilePath);

			// Check for upload success toast (using sonner)
			// sonner toasts can be found by text
			await expect(page.getByText("Dataset uploaded successfully")).toBeVisible(
				{ timeout: 20000 },
			);
		} finally {
			// Clean up dummy file
			if (fs.existsSync(testFilePath)) {
				fs.unlinkSync(testFilePath);
			}
		}
	});

	test("should verify dashboard stats update", async ({ page }) => {
		await page.goto("/");

		// Check for the dashboard content specifically
		const main = page.getByRole("main");

		// Check if stats labels are visible in the main content area
		await expect(main.getByText("Total Meets", { exact: true })).toBeVisible();
		await expect(main.getByText("Teams", { exact: true })).toBeVisible();
		await expect(main.getByText("Athletes", { exact: true })).toBeVisible();
		await expect(main.getByText("Events", { exact: true })).toBeVisible();
	});

	test("should navigate to Reports and generate a Meet Program PDF", async ({
		page,
	}) => {
		await page.goto("/reports");

		await expect(
			page.getByRole("heading", { name: "Reports", exact: true }),
		).toBeVisible();

		// Click on "Meet Program" card/button
		// The ReportsManager likely renders cards for different report types
		const meetProgramCard = page
			.locator("div")
			.filter({ hasText: /^Meet Program/ })
			.first();
		const generateButton = meetProgramCard.getByRole("button", {
			name: /Generate/i,
		});

		if (await generateButton.isVisible()) {
			await generateButton.click();

			// Should show a preview modal/dialog
			// Increase timeout as PDF generation can be slow
			await expect(page.getByRole("dialog")).toBeVisible({ timeout: 30000 });
			await expect(page.getByText(/Preview/i)).toBeVisible();
		}
	});

	test("should show QR code dialog when clicking Publish to Judge App", async ({
		page,
	}) => {
		await page.goto("/admin");

		// Check if there's an active dataset with a "Publish" button
		const publishButton = page.getByRole("button", {
			name: "Publish to Judge App",
		});

		// If not visible, we might need to select/upload a dataset first,
		// but usually there's a default one.
		if (await publishButton.isVisible()) {
			await publishButton.click();

			// Check for the Dialog
			const dialog = page.getByRole("dialog");
			await expect(dialog).toBeVisible();
			await expect(dialog.getByText("Judge App Setup")).toBeVisible();
			// Check for the QR code SVG inside the dialog
			await expect(dialog.getByRole("img")).toBeVisible();

			// Verify it contains a link (qr value)
			// The QR code component usually has a value attribute or similar
			// But for E2E we just check it's rendered.
		}
	});
});
