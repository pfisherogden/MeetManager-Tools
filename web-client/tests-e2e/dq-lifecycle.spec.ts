import * as fs from "node:fs";
import { expect, type Page, test, type BrowserContext } from "@playwright/test";

/**
 * End-to-End DQ Lifecycle User Journeys
 *
 * This test suite covers:
 * 1. Meet Administrator publishing data.
 * 2. S&T Judge entering DQs (Individual & Relay).
 * 3. Computer Volunteer reviewing and syncing DQs.
 */

// Helper to ensure a dataset is uploaded and active for a given UID
async function ensureDataset(page: Page, uid: string, filename: string, data: any) {
	console.log(`Ensuring dataset for ${uid}: ${filename}...`);
	await page.goto(`/admin?uid=${uid}`);
	await expect(
		page.getByRole("heading", { name: /Admin Configuration/i }),
	).toBeVisible({ timeout: 15000 });

	const row = page.locator("tr").filter({ hasText: filename });
	const isActive = (await row.getByTestId("active-dataset-badge").count()) > 0;

	if (isActive) {
		console.log(`Dataset ${filename} is already active for ${uid}`);
		return;
	}

	// Not active, check if uploaded
	if ((await row.count()) === 0) {
		console.log(`No dataset ${filename} found for ${uid}, uploading...`);
		const testFilePath = `tests-e2e/${filename}`;
		fs.writeFileSync(testFilePath, JSON.stringify(data));
		try {
			const fileChooserPromise = page.waitForEvent("filechooser");
			await page
				.getByRole("button", { name: /Upload Dataset/i })
				.first()
				.click({ force: true });
			const fileChooser = await fileChooserPromise;
			await fileChooser.setFiles(testFilePath);
			await expect(
				page.getByText(/Dataset uploaded successfully/i),
			).toBeVisible({ timeout: 20000 });

			// Reload after upload to refresh the list
			await page.reload();
			await page.waitForTimeout(2000);
		} finally {
			if (fs.existsSync(testFilePath)) fs.unlinkSync(testFilePath);
		}
	}

	// Now set it active
	console.log(`Setting ${filename} active...`);
	const targetRow = page.locator("tr").filter({ hasText: filename });
	await targetRow
		.getByRole("button", { name: /Set Active/i })
		.first()
		.click({ force: true });
	await expect(targetRow.getByTestId("active-dataset-badge")).toBeVisible({
		timeout: 15000,
	});
	console.log(`Dataset ${filename} is now active`);
}

test.describe("Disqualification Lifecycle", () => {
	let judgePage: Page;
	let volunteerPage: Page;
	let judgeContext: BrowserContext;
	let volunteerContext: BrowserContext;
	
	const getUserId = () => `e2e-dq-${Math.random().toString(36).substring(7)}`;

	test.beforeEach(async ({ browser }) => {
		const userId = getUserId();
		
		// Create isolated contexts for Judge and Volunteer
		// CRITICAL: Pass x-user-id in extraHTTPHeaders for Server Action isolation in CI
		judgeContext = await browser.newContext({
			baseURL: process.env.MOBILE_APP_URL || "http://localhost:8080",
			viewport: { width: 375, height: 1200 }, // Extra tall for safety
			userAgent:
				"Mozilla/5.0 (iPhone; CPU iPhone OS 13_2_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.0.3 Mobile/15E148 Safari/604.1",
			extraHTTPHeaders: { "x-user-id": userId },
		});

		volunteerContext = await browser.newContext({
			baseURL: process.env.FRONTEND_URL || "http://localhost:3000",
			extraHTTPHeaders: { "x-user-id": userId },
		});

		judgePage = await judgeContext.newPage();
		volunteerPage = await volunteerContext.newPage();

		judgePage.on("console", (msg) => console.log(`JUDGE CONSOLE [${msg.type()}]: ${msg.text()}`));
		volunteerPage.on("console", (msg) => console.log(`VOLUNTEER CONSOLE [${msg.type()}]: ${msg.text()}`));
		
		// Capture crashes
		judgePage.on("error", err => console.error("JUDGE PAGE CRASH:", err));
		judgePage.on("pageerror", err => console.error("JUDGE PAGE ERROR:", err));
		volunteerPage.on("error", err => console.error("VOLUNTEER PAGE CRASH:", err));
		volunteerPage.on("pageerror", err => console.error("VOLUNTEER PAGE ERROR:", err));
	});

	test.afterEach(async () => {
		await judgePage.close();
		await volunteerPage.close();
		await judgeContext.close();
		await volunteerContext.close();
	});

	test("Full DQ Journey: Publish -> Submit -> Sync -> Verify", async () => {
		const contextHeaders = await volunteerPage.context().request.headers();
		const userId = contextHeaders["x-user-id"] || "unknown";
		const dummyData = {
			meet: [{ meet_name1: "Journey Meet" }],
			team: [{ team_no: 1, team_abbr: "TEST", team_name: "Test Team" }],
			athlete: [
				{ ath_no: 1, team_no: 1, first_name: "Test", last_name: "A" },
				{ ath_no: 2, team_no: 1, first_name: "Test", last_name: "B" },
				{ ath_no: 3, team_no: 1, first_name: "Test", last_name: "C" },
				{ ath_no: 4, team_no: 1, first_name: "Test", last_name: "D" },
			],
			event: [
				{ event_no: 13, event_ptr: 13, ind_rel: "R" },
				{ event_no: 15, event_ptr: 15, ind_rel: "I" },
			],
			session: [{ sess_ptr: 1, sess_no: 1 }],
			sessitem: [
				{ sess_ptr: 1, event_ptr: 13 },
				{ sess_ptr: 1, event_ptr: 15 },
			],
			entry: [
				{ ath_no: 1, event_ptr: 13, pre_heat: 1, pre_lane: 2 },
				{ ath_no: 2, event_ptr: 13, pre_heat: 1, pre_lane: 2 },
				{ ath_no: 3, event_ptr: 13, pre_heat: 1, pre_lane: 2 },
				{ ath_no: 4, event_ptr: 13, pre_heat: 1, pre_lane: 2 },
				{ ath_no: 1, event_ptr: 15, pre_heat: 1, pre_lane: 1 },
			],
			relay: [
				{ relay_no: 1, team_no: 1, event_ptr: 13, pre_heat: 1, pre_lane: 2 },
			],
			relaynames: [
				{ relay_no: 1, ath_no: 1, pos: 1 },
				{ relay_no: 1, ath_no: 2, pos: 2 },
				{ relay_no: 1, ath_no: 3, pos: 3 },
				{ relay_no: 1, ath_no: 4, pos: 4 },
			],
		};

		const filename = `journey-${userId}.json`;
		await ensureDataset(volunteerPage, userId, filename, dummyData);

		console.log("Journey Step 1.1: Clicking Publish button...");
		const publishBtn = volunteerPage.locator("tr").filter({ hasText: filename }).getByTestId("publish-button");
		await publishBtn.first().click({ force: true });
		await expect(volunteerPage.getByText("Meet data published")).toBeVisible({ timeout: 30000 });

		const judgeAppUrl = await volunteerPage.getByTestId("judge-app-url").innerText();
		const localUrl = judgeAppUrl.replace(/^https?:\/\/[^/]+/i, "http://localhost:8080");

		console.log("Journey Step 2: Judge onboarding...");
		await judgePage.goto(localUrl);
		await judgePage.getByPlaceholder("Your Name").fill("Judge Alex");
		await judgePage.getByText("START JUDGING").click({ force: true });
		await expect(judgePage.getByText("Events", { exact: true })).toBeVisible({ timeout: 15000 });

		console.log("Journey Step 3: Judge submitting individual DQ...");
		await judgePage.getByText(/Event 15/i).first().click({ force: true });
		await judgePage.getByText(/Heat 1/i).first().click({ force: true });
		await judgePage.getByText("TAP TO DQ").first().click({ force: true });
		await judgePage.getByText("1A").first().click({ force: true });
		await judgePage.getByPlaceholder("Add notes here (optional)").fill("False start on lane 1");
		await judgePage.evaluate(() => (document.querySelector('[aria-label="Save changes"]') as HTMLElement)?.click());

		await expect(judgePage.locator("#root").getByText("1A").first()).toBeVisible({ timeout: 10000 });

		console.log("Journey Step 4: Volunteer verifying live DQ...");
		await volunteerPage.goto("/dqs");
		await expect(volunteerPage.locator("tr").filter({ hasText: "1A" })).toBeVisible({ timeout: 15000 });

		console.log("Journey Step 5: Judge submitting relay DQ...");
		await judgePage.getByLabel(/back/i).or(judgePage.getByText("BACK", { exact: true })).first().click({ force: true });
		await judgePage.getByLabel(/events/i).or(judgePage.getByText("EVENTS", { exact: true })).first().click({ force: true });
		await judgePage.getByText(/Event 13/i).first().click({ force: true });
		await judgePage.getByText(/Heat 1/i).first().click({ force: true });

		const leg3 = judgePage.getByText(/Leg 3/i).or(judgePage.getByText(/Test C/i)).first();
		await expect(leg3).toBeVisible({ timeout: 10000 });
		await leg3.click({ force: true });
		await judgePage.getByText("7Q").first().click({ force: true });
		await judgePage.evaluate(() => (document.querySelector('[aria-label="Save changes"]') as HTMLElement)?.click());

		console.log("Journey Step 6: Volunteer verifying relay swimmer name...");
		await volunteerPage.reload();
		await expect(volunteerPage.locator("tr").filter({ hasText: "7Q" })).toBeVisible({ timeout: 15000 });
		await expect(volunteerPage.getByText(/Test C/i)).toBeVisible({ timeout: 10000 });

		console.log("Journey Step 7: Judge editing pending DQ...");
		await judgePage.getByText(/DQ History/).first().click({ force: true });
		await judgePage.getByText("7Q").first().waitFor({ state: "visible", timeout: 10000 });
		await judgePage.evaluate(() => {
			const elements = Array.from(document.querySelectorAll("div, span, p"));
			const dqBtn = elements.find(el => el.textContent?.trim() === "7Q") as HTMLElement;
			if (dqBtn) dqBtn.click();
		});
		await judgePage.getByPlaceholder("Add notes here (optional)").fill("Corrected: Early start on leg 3");
		await judgePage.evaluate(() => (document.querySelector('[aria-label="Save changes"]') as HTMLElement)?.click());

		console.log("Journey Step 8: Volunteer verifying sync status...");
		await volunteerPage.reload();
		await expect(volunteerPage.locator("tr").filter({ hasText: "7Q" })).toContainText(/Synced/i, { timeout: 15000 });
	});

	test.describe("Frontend Visibility Journeys", () => {
		test("should show synced DQs in the global Submitted DQs list", async ({ page }) => {
			await page.goto("/dqs");
			await expect(page.getByRole("heading", { name: /Submitted Disqualifications/i })).toBeVisible({ timeout: 15000 });
			await expect(page.locator("table")).toBeVisible({ timeout: 10000 });
		});
	});

	test.describe("Bug Regression Tests", () => {
		test("should generate correct Judge App URL (not 404)", async ({ page }) => {
			const contextHeaders = await page.context().request.headers();
			const userIdRegress = contextHeaders["x-user-id"] || "regress-user";
			const dummyData = {
				meet: [{ meet_name1: "Regression Meet" }],
				team: [{ team_no: 1, team_abbr: "TEST", team_name: "Test Team" }],
				athlete: [{ ath_no: 1, team_no: 1, first_name: "Test", last_name: "A" }],
				event: [{ event_no: 1, event_ptr: 1, ind_rel: "I" }],
				session: [{ sess_ptr: 1, sess_no: 1 }],
				sessitem: [{ sess_ptr: 1, event_ptr: 1 }],
				entry: [{ ath_no: 1, event_ptr: 1, pre_heat: 1, pre_lane: 1 }],
			};

			const filename = `regress-url-${userIdRegress}.json`;
			await ensureDataset(page, userIdRegress, filename, dummyData);

			await page.locator("tr").filter({ hasText: filename }).getByTestId("publish-button").first().click({ force: true });
			await expect(page.getByText("Meet data published")).toBeVisible({ timeout: 15000 });
			const judgeAppUrl = await page.getByTestId("judge-app-url").innerText();
			expect(judgeAppUrl).toContain("/judge?");
			expect(judgeAppUrl).not.toContain(":3000/judge");
		});

		test("should maintain relay team view when navigating heats", async ({ browser }) => {
			const userIdNav = `e2e-nav-view-${Math.random().toString(36).substring(7)}`;
			const dummyData = {
				meet: [{ meet_name1: "Nav Meet" }],
				team: [{ team_no: 1, team_abbr: "TEST", team_name: "Test Team" }],
				athlete: [{ ath_no: 1, team_no: 1, first_name: "Test", last_name: "A" }],
				event: [{ event_no: 13, event_ptr: 13, ind_rel: "R" }],
				session: [{ sess_ptr: 1, sess_no: 1 }],
				sessitem: [{ sess_ptr: 1, event_ptr: 13 }],
				entry: [
					{ ath_no: 1, event_ptr: 13, pre_heat: 1, pre_lane: 1 },
					{ ath_no: 1, event_ptr: 13, pre_heat: 2, pre_lane: 1 },
				],
				relay: [
					{ relay_no: 1, team_no: 1, event_ptr: 13, pre_heat: 1, pre_lane: 1 },
					{ relay_no: 2, team_no: 1, event_ptr: 13, pre_heat: 2, pre_lane: 1 },
				],
				relaynames: [
					{ relay_no: 1, ath_no: 1, pos: 1 },
					{ relay_no: 2, ath_no: 1, pos: 1 },
				],
			};

			const adminContext = await browser.newContext({
				baseURL: process.env.FRONTEND_URL || "http://localhost:3000",
				extraHTTPHeaders: { "x-user-id": userIdNav },
			});
			const adminPage = await adminContext.newPage();
			const filename = `nav-view-${userIdNav}.json`;
			await ensureDataset(adminPage, userIdNav, filename, dummyData);

			await adminPage.locator("tr").filter({ hasText: filename }).getByTestId("publish-button").first().click({ force: true });
			await expect(adminPage.getByText("Meet data published")).toBeVisible({ timeout: 15000 });
			const judgeAppUrl = await adminPage.getByTestId("judge-app-url").innerText();
			const localUrl = judgeAppUrl.replace(/^https?:\/\/[^\/]+/i, "http://localhost:8080");

			const judgeContext = await browser.newContext({
				viewport: { width: 375, height: 1200 },
				userAgent: "Mozilla/5.0 (iPhone; CPU iPhone OS 13_2_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.0.3 Mobile/15E148 Safari/604.1",
				extraHTTPHeaders: { "x-user-id": userIdNav },
			});
			const judgePage = await judgeContext.newPage();
			await judgePage.goto(localUrl);
			await judgePage.getByPlaceholder("Your Name").fill("Regression Judge");
			await judgePage.getByText("START JUDGING").click({ force: true });

			await judgePage.getByText("Event 13").first().click({ force: true });
			await judgePage.getByText("Heat 1").first().click({ force: true });
			await expect(judgePage.getByText(/Leg 1/i).or(judgePage.getByText(/Test A/i)).first()).toBeVisible({ timeout: 10000 });

			await judgePage.getByLabel(/next heat/i).first().click({ force: true });
			await judgePage.waitForTimeout(2000);
			await expect(judgePage.getByText(/Leg 1/i).or(judgePage.getByText(/Test A/i)).first()).toBeVisible({ timeout: 10000 });
			
			await adminPage.close();
			await adminContext.close();
			await judgePage.close();
			await judgeContext.close();
		});

		test("should dismiss DQ history modal when clicking outside", async ({ browser }) => {
			const judgeContext = await browser.newContext({
				viewport: { width: 375, height: 1200 },
			});
			const judgePage = await judgeContext.newPage();
			await judgePage.goto("http://localhost:8080/judge");
			await judgePage.getByPlaceholder("Your Name").fill("Modal Judge");
			await judgePage.getByText("START JUDGING").click({ force: true });

			await judgePage.getByText(/DQ History/).first().click({ force: true });
			await expect(judgePage.getByText(/DQ History \(Total: 0\)/i)).toBeVisible({ timeout: 10000 });

			await judgePage.mouse.click(5, 300);
			await judgePage.waitForTimeout(1000);
			await expect(judgePage.getByText(/DQ History \(Total: 0\)/i)).not.toBeVisible({ timeout: 10000 });
		});
	});
});
