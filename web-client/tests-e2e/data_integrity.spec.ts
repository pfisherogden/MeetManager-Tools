import { expect, test } from "@playwright/test";
import {
	ensureDatasetActive,
	getE2ETestContext,
	getFixtureData,
	robustClick,
	setupE2ESession,
} from "./utils";

test.describe("Data Integrity and UI Rendering", () => {
	test.beforeEach(async ({ page }, testInfo) => {
		const { getFilename } = getE2ETestContext(testInfo, page);
		const testFileName = getFilename("tiny_champs.json");
		const data = getFixtureData("tiny_champs.json");
		await setupE2ESession(page, testInfo);
		await ensureDatasetActive(page, testInfo, testFileName, data);
	});

	test("should show non-empty dashboard stats", async ({ page }) => {
		await page.goto("/");
		await expect(page.getByTestId("stat-meets")).not.toHaveText("0");
		await expect(page.getByTestId("stat-teams")).not.toHaveText("0");
		await expect(page.getByTestId("stat-athletes")).not.toHaveText("0");
		await expect(page.getByTestId("stat-events")).not.toHaveText("0");
	});

	test("should show consistent and different team colors on Teams page", async ({
		page,
	}) => {
		await page.goto("/teams");
		const rows = page.locator("table tbody tr");

		// Wait for client-side hydration to fetch teams and populate the table
		await expect
			.poll(async () => await rows.count(), { timeout: 15000 })
			.toBeGreaterThan(1);

		const colors = await rows.evaluateAll((list) => {
			return list.map((row) => {
				const badge = row.querySelector("[data-testid='team-color-badge']");
				return badge ? window.getComputedStyle(badge).backgroundColor : null;
			});
		});

		const uniqueColors = new Set(colors.filter((c) => c !== null));
		console.log(
			`Found ${uniqueColors.size} unique team colors:`,
			Array.from(uniqueColors),
		);
		expect(uniqueColors.size).toBeGreaterThan(1);
	});

	test("should show non-empty Events page", async ({ page }) => {
		await page.goto("/events");
		await expect(page.getByRole("table")).toBeVisible();
		await expect(page.locator("table tbody tr")).not.toHaveCount(0);
		await expect(page.locator("table")).toContainText(/Freestyle/i);
	});

	test("should show non-empty Relays page", async ({ page }) => {
		await page.goto("/relays");
		await expect(page.locator("body")).not.toContainText(/No relays found/i);
		await expect(page.locator("table tbody tr")).not.toHaveCount(0);
	});

	test("should show non-empty Scores page", async ({ page }) => {
		await page.goto("/scores");
		await expect(page.getByRole("table")).toBeVisible();
		await expect(page.locator("table tbody tr")).not.toHaveCount(0);
		await expect(page.locator("table")).toContainText(/Total/i);
	});

	test("should generate a single report with a human-readable filename", async ({
		page,
	}) => {
		await page.goto("/reports");

		const meetProgramCard = page.getByTestId("report-card-meet-program-(pdf)");
		await robustClick(meetProgramCard);

		const configCard = page.getByTestId("report-configuration-card");
		await expect(configCard).toBeVisible();

		const downloadPromise = page.waitForEvent("download");
		await configCard.getByTestId("generate-report-button").click();

		const download = await downloadPromise;
		const filename = download.suggestedFilename();
		console.log(`Downloaded filename: ${filename}`);

		// Verify filename matches the human readable pattern (Meet Program PDF_YYYYMMDD-HHMM.pdf)
		expect(filename).toContain("Meet Program PDF");
		expect(filename).toMatch(/Meet Program PDF_\d{8}-\d{4}\.pdf/);
		expect(filename).not.toMatch(/[a-zA-Z0-9]{20,}_/); // No long UID prefix
	});

	test("should generate and download a ZIP bundle without 403 unauthorized error", async ({
		page,
	}) => {
		test.setTimeout(600000);
		await page.goto("/reports");

		// 1. Clear any existing pack items first to ensure a clean state
		const clearBtn = page.getByTestId("clear-pack-button");
		if ((await clearBtn.isVisible()) && (await clearBtn.isEnabled())) {
			await clearBtn.click();
			await expect(page.getByText(/Your pack is empty/i)).toBeVisible();
		}

		// 2. Select "Test Bundle (Fast)" preset
		const presetBtn = page.getByTestId("preset-apply-test");
		await expect(presetBtn).toBeVisible();
		await presetBtn.click();

		// 3. Wait for the bundle button to become enabled (indicates pack has items)
		const bundleBtn = page.getByTestId("generate-bundle-button");
		await expect(bundleBtn).toBeEnabled({ timeout: 20000 });

		// 4. Setup download listener BEFORE clicking generate
		const downloadPromise = page.waitForEvent("download", { timeout: 600000 });

		await bundleBtn.click();

		// 5. The UI triggers an automatic download via window.location.href once complete
		const download = await downloadPromise;
		const downloadUrl = download.url();
		console.log(`Download started: ${downloadUrl}`);

		// 6. Verify the bundle URL contains a token and it's not empty (skip for blob URLs)
		if (!downloadUrl.startsWith("blob:")) {
			expect(downloadUrl).toContain("token=");
			expect(downloadUrl).not.toContain("token=&");
			expect(downloadUrl).not.toMatch(/token=$/); // Should not end with token=
		}

		expect(await download.path()).toBeTruthy();
		const filename = download.suggestedFilename();
		console.log(`Downloaded bundle: ${filename}`);
		expect(filename).toContain(".zip");
	});

	test("should show teams on Athletes page", async ({ page }) => {
		await page.goto("/athletes");
		await expect(page.getByRole("table")).toBeVisible();
		const firstRow = page.locator("table tbody tr").first();
		await expect(firstRow).toBeVisible();
		await expect(firstRow).not.toContainText(/Unknown/i);
	});
});
