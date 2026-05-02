import { expect, test } from "@playwright/test";
import {
	ensureDatasetActive,
	getE2ETestContext,
	getFixtureData,
	robustClick,
	setupE2ESession,
	waitForJudgeApp,
} from "./utils";

test.describe("DQ Notes Preservation", () => {
	test.beforeEach(async ({ page }, testInfo) => {
		const { getFilename } = getE2ETestContext(testInfo, page);
		const testFileName = getFilename("tiny_meet.json");
		const data = getFixtureData("tiny_meet.json");
		await setupE2ESession(page, testInfo);
		await ensureDatasetActive(page, testInfo, testFileName, data);
	});

	test("should preserve notes from Judge App to Frontend", async ({
		page,
		baseURL,
	}, testInfo) => {
		const { userId } = getE2ETestContext(testInfo, page);
		const testNote = "Test DQ note 123";

		// 1. Submit DQ with note in Judge App
		// We must provide sync_url so the app knows where to send the DQ
		const token =
			process.env.DATA_ACCESS_TOKEN || "mmtools-default-secret-2024";
		const syncUrl = encodeURIComponent(
			`${baseURL}/api/sync-dqs?token=${token}&uid=${userId}`,
		);
		const judgeUrl = `/judge/index.html?sync_url=${syncUrl}`;
		console.log(`Navigating to Judge App: ${judgeUrl}`);
		await page.goto(judgeUrl);
		await waitForJudgeApp(page);

		// Enter judge name if prompt is visible
		const nameInput = page.getByPlaceholder("Your Name");
		if (await nameInput.isVisible()) {
			await nameInput.fill("Test Judge");
			await page.getByText(/START JUDGING/i).click();
		}

		// Navigate to an event
		console.log("Selecting Event 17...");
		await page
			.getByText(/Event 17/i)
			.first()
			.click();
		await page
			.getByText(/Heat 1/i)
			.first()
			.click();

		// Click a swimmer to DQ
		console.log("Opening DQ Modal...");
		const addDqBtn = page.getByTestId("add-dq-button").first();
		await expect(addDqBtn).toBeVisible({ timeout: 10000 });
		await addDqBtn.click();

		// Wait for modal to appear using the notes placeholder as sentinel
		const notesInput = page.getByPlaceholder(/Add notes here/i);
		await expect(notesInput).toBeVisible({ timeout: 15000 });

		// Select a DQ code and add a note
		console.log("Filling DQ details...");
		await page.getByTestId("dq-code-1A").click();
		await notesInput.fill(testNote);

		// Wait for sync response after save
		console.log("Saving DQ...");
		const syncPromise = page.waitForResponse(
			(r) => r.url().includes("/api/submit-dq") && r.status() === 200,
			{ timeout: 30000 },
		);

		// Try multiple ways to click save
		const saveBtn = page
			.getByTestId("save-dq-button")
			.or(page.getByLabel("Save changes"));
		await robustClick(saveBtn);

		const response = await syncPromise;
		console.log(`Sync response received: ${response.status()}`);

		// 2. Verify note in Judge App History
		console.log("Checking history...");
		// Small delay to allow previous modal to fully close and state to settle
		await page.waitForTimeout(1000);
		await robustClick(page.getByTestId("dq-history-button"));

		// Wait for modal to appear and check for the note
		const historyModal = page.getByTestId("dq-history-modal-content");
		await expect(historyModal).toBeVisible({ timeout: 15000 });
		await expect(historyModal).toContainText(testNote);

		// 3. Verify note in MMTools Frontend
		console.log("Checking frontend...");
		await page.goto("/dqs");
		await expect(page.locator("table")).toContainText(testNote, {
			timeout: 15000,
		});
	});
});
