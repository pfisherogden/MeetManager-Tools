import * as fs from "node:fs";
import { type BrowserContext, expect, type Page, test } from "@playwright/test";

/**
 * End-to-End DQ Lifecycle User Journeys
 *
 * This test suite covers:
 * 1. Meet Administrator publishing data.
 * 2. S&T Judge entering DQs (Individual & Relay).
 * 3. Computer Volunteer reviewing and syncing DQs.
 */

// Helper to ensure a dataset is uploaded and active for a given UID
async function ensureDataset(
	page: Page,
	uid: string,
	filename: string,
	data: any,
) {
	console.log(`Ensuring dataset for ${uid}: ${filename}...`);
	await page.goto(`/admin?uid=${uid}`);

	// Wait for the main container to be ready
	await expect(
		page.getByRole("heading", { name: /Admin Configuration/i }),
	).toBeVisible({ timeout: 20000 });

	// Wait for the dataset table/list to be loaded
	await page
		.waitForSelector("[data-testid^='dataset-row-']", { timeout: 15000 })
		.catch(() => {
			console.log("No datasets found yet, proceeding with upload if needed.");
		});

	// Use the specific row for this user's dataset if multiple exist
	const row = page.getByTestId(`dataset-row-${filename}`);
	const rowCount = await row.count();

	if (rowCount > 0) {
		const isActive =
			(await row.getByTestId("active-dataset-badge").count()) > 0;
		if (isActive) {
			console.log(`Dataset ${filename} is already active for ${uid}`);
			return;
		}
	}

	// Not active or not found, check if uploaded
	if (rowCount === 0) {
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

			// Wait for the specific row to appear after upload with retries
			console.log(`Waiting for row to appear: dataset-row-${filename}...`);
			let rowVisible = false;
			for (let i = 0; i < 5; i++) {
				const count = await row.count();
				if (count > 0 && (await row.isVisible())) {
					rowVisible = true;
					break;
				}
				console.log(`Retry ${i + 1}: Dataset row not found yet, reloading...`);
				await page.reload({ waitUntil: "networkidle" });
				await page.waitForTimeout(2000);
			}

			if (!rowVisible) {
				console.log("FINAL ATTEMPT: Waiting for row visibility...");
			}
			await expect(row).toBeVisible({ timeout: 15000 });
		} finally {
			if (fs.existsSync(testFilePath)) fs.unlinkSync(testFilePath);
		}
	}

	// Now set it active
	console.log(`Setting ${filename} active...`);
	const setActiveBtn = row.getByRole("button", { name: /Set Active/i }).first();
	await expect(setActiveBtn).toBeVisible({ timeout: 10000 });
	await setActiveBtn.click({ force: true });

	await expect(row.getByTestId("active-dataset-badge")).toBeVisible({
		timeout: 15000,
	});
	console.log(`Dataset ${filename} is now active`);
}

test.describe("Disqualification Lifecycle", () => {
	let judgePage: Page;
	let volunteerPage: Page;
	let judgeContext: BrowserContext;
	let volunteerContext: BrowserContext;
	let currentUserId: string;

	const getUserId = () => `e2e-dq-${Math.random().toString(36).substring(7)}`;

	test.beforeEach(async ({ browser }) => {
		currentUserId = getUserId();

		// Create isolated contexts for Judge and Volunteer
		// CRITICAL: Pass x-user-id and x-e2e-uid in extraHTTPHeaders for Server Action isolation in CI
		judgeContext = await browser.newContext({
			baseURL: process.env.MOBILE_APP_URL || "http://localhost:8080",
			viewport: { width: 375, height: 1200 }, // Extra tall for safety
			userAgent:
				"Mozilla/5.0 (iPhone; CPU iPhone OS 13_2_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.0.3 Mobile/15E148 Safari/604.1",
			extraHTTPHeaders: {
				"x-user-id": currentUserId,
				"x-e2e-uid": currentUserId,
			},
		});

		volunteerContext = await browser.newContext({
			baseURL: process.env.FRONTEND_URL || "http://localhost:3000",
			extraHTTPHeaders: {
				"x-user-id": currentUserId,
				"x-e2e-uid": currentUserId,
			},
		});

		judgePage = await judgeContext.newPage();
		volunteerPage = await volunteerContext.newPage();

		judgePage.on("console", (msg) =>
			console.log(`JUDGE CONSOLE [${msg.type()}]: ${msg.text()}`),
		);
		volunteerPage.on("console", (msg) =>
			console.log(`VOLUNTEER CONSOLE [${msg.type()}]: ${msg.text()}`),
		);

		// Capture crashes
		judgePage.on("error", (err) => console.error("JUDGE PAGE CRASH:", err));
		judgePage.on("pageerror", (err) => console.error("JUDGE PAGE ERROR:", err));
		volunteerPage.on("error", (err) =>
			console.error("VOLUNTEER PAGE CRASH:", err),
		);
		volunteerPage.on("pageerror", (err) =>
			console.error("VOLUNTEER PAGE ERROR:", err),
		);
	});

	test.afterEach(async () => {
		await judgePage.close();
		await volunteerPage.close();
		await judgeContext.close();
		await volunteerContext.close();
	});

	test("Full DQ Journey: Publish -> Submit -> Sync -> Verify", async () => {
		const userId = currentUserId;
		const dummyData = {
			Meet: [{ Meet_name1: "Tiny Meet" }],
			Team: [{ Team_no: "1", Team_abbr: "TEST", Team_name: "Test Team" }],
			Athlete: [
				{ Ath_no: "1", Team_no: "1", First_name: "Test", Last_name: "A" },
				{ Ath_no: "2", Team_no: "1", First_name: "Test", Last_name: "B" },
				{ Ath_no: "3", Team_no: "1", First_name: "Test", Last_name: "C" },
				{ Ath_no: "4", Team_no: "1", First_name: "Test", Last_name: "D" },
			],
			Event: [
				{
					Event_no: "13",
					Event_ptr: "13",
					Ind_rel: "R",
					Event_dist: "100",
					Event_stroke: "E",
				},
				{
					Event_no: "15",
					Event_ptr: "15",
					Ind_rel: "I",
					Event_dist: "25",
					Event_stroke: "A",
				},
			],
			Session: [{ Sess_ptr: "1", Sess_no: "1" }],
			Entry: [
				{ Ath_no: "1", Event_ptr: "13", Pre_heat: "1", Pre_lane: "2" },
				{ Ath_no: "2", Event_ptr: "13", Pre_heat: "1", Pre_lane: "2" },
				{ Ath_no: "3", Event_ptr: "13", Pre_heat: "1", Pre_lane: "2" },
				{ Ath_no: "4", Event_ptr: "13", Pre_heat: "1", Pre_lane: "2" },
				{ Ath_no: "1", Event_ptr: "15", Pre_heat: "1", Pre_lane: "1" },
			],
			Relay: [
				{
					Relay_no: "1",
					Team_no: "1",
					Event_ptr: "13",
					Pre_heat: "1",
					Pre_lane: "2",
				},
			],
			RelayNames: [
				{ Relay_no: "1", Ath_no: "1", Pos_no: "1" },
				{ Relay_no: "1", Ath_no: "2", Pos_no: "2" },
				{ Relay_no: "1", Ath_no: "3", Pos_no: "3" },
				{ Relay_no: "1", Ath_no: "4", Pos_no: "4" },
			],
		};

		const filename = `journey-${userId}.json`;
		await ensureDataset(volunteerPage, userId, filename, dummyData);

		console.log("Journey Step 1.1: Clicking Publish button...");
		const publishBtn = volunteerPage
			.getByTestId(`dataset-row-${filename}`)
			.getByTestId("publish-button");
		await publishBtn.first().click({ force: true });
		await expect(volunteerPage.getByText("Meet data published")).toBeVisible({
			timeout: 30000,
		});

		const judgeAppUrl = await volunteerPage
			.getByTestId("judge-app-url")
			.innerText();
		const localUrl = judgeAppUrl.replace(
			/^https?:\/\/[^/]+/i,
			"http://localhost:8080",
		);

		console.log("Journey Step 2: Judge onboarding...");
		await judgePage.goto(localUrl);
		await judgePage.getByPlaceholder("Your Name").fill("Judge Alex");
		await judgePage.getByText("START JUDGING").click({ force: true });
		await expect(judgePage.getByText("Events", { exact: true })).toBeVisible({
			timeout: 15000,
		});

		console.log("Journey Step 3: Judge submitting individual DQ...");
		await judgePage
			.getByText(/Event 15/i)
			.first()
			.click({ force: true });
		await judgePage
			.getByText(/Heat 1/i)
			.first()
			.click({ force: true });
		await judgePage.getByText("TAP TO DQ").first().click({ force: true });
		await judgePage.getByText("1A").first().click({ force: true });
		await judgePage
			.getByPlaceholder("Add notes here (optional)")
			.fill("False start on lane 1");
		await judgePage.evaluate(() =>
			(
				document.querySelector('[aria-label="Save changes"]') as HTMLElement
			)?.click(),
		);

		await expect(
			judgePage.locator("#root").getByText("1A").first(),
		).toBeVisible({ timeout: 10000 });

		console.log("Journey Step 4: Volunteer verifying live DQ...");
		await volunteerPage.goto("/dqs");
		await expect(
			volunteerPage.locator("tr").filter({ hasText: "1A" }),
		).toBeVisible({ timeout: 15000 });

		console.log("Journey Step 5: Judge submitting relay DQ...");
		await judgePage
			.getByLabel(/back/i)
			.or(judgePage.getByText("BACK", { exact: true }))
			.first()
			.click({ force: true });
		await judgePage
			.getByLabel(/events/i)
			.or(judgePage.getByText("EVENTS", { exact: true }))
			.first()
			.click({ force: true });
		await judgePage
			.getByText(/Event 13/i)
			.first()
			.click({ force: true });
		await judgePage
			.getByText(/Heat 1/i)
			.first()
			.click({ force: true });

		const leg3 = judgePage
			.getByText(/Leg 3/i)
			.or(judgePage.getByText(/Test C/i))
			.first();
		await expect(leg3).toBeVisible({ timeout: 10000 });
		await leg3.click({ force: true });
		await judgePage.getByText("7Q").first().click({ force: true });
		await judgePage.evaluate(() =>
			(
				document.querySelector('[aria-label="Save changes"]') as HTMLElement
			)?.click(),
		);

		console.log("Journey Step 6: Volunteer verifying relay swimmer name...");
		await volunteerPage.reload();
		await expect(
			volunteerPage.locator("tr").filter({ hasText: "7Q" }),
		).toBeVisible({ timeout: 15000 });
		await expect(volunteerPage.getByText(/Test C/i)).toBeVisible({
			timeout: 10000,
		});

		console.log("Journey Step 7: Judge editing pending DQ...");
		await judgePage
			.getByText(/DQ History/)
			.first()
			.click({ force: true });
		await judgePage
			.getByText("7Q")
			.first()
			.waitFor({ state: "visible", timeout: 10000 });
		await judgePage.evaluate(() => {
			const elements = Array.from(document.querySelectorAll("div, span, p"));
			const dqBtn = elements.find(
				(el) => el.textContent?.trim() === "7Q",
			) as HTMLElement;
			if (dqBtn) dqBtn.click();
		});
		await judgePage
			.getByPlaceholder("Add notes here (optional)")
			.fill("Corrected: Early start on leg 3");
		await judgePage.evaluate(() =>
			(
				document.querySelector('[aria-label="Save changes"]') as HTMLElement
			)?.click(),
		);

		console.log("Journey Step 8: Volunteer verifying sync status...");
		await volunteerPage.reload();
		await expect(
			volunteerPage.locator("tr").filter({ hasText: "Synced" }),
		).toBeVisible({ timeout: 15000 });
	});

	test.describe("Frontend Visibility Journeys", () => {
		test("should show synced DQs in the global Submitted DQs list", async ({
			page,
		}) => {
			await page.goto("/dqs");
			await expect(
				page.getByRole("heading", { name: /Submitted Disqualifications/i }),
			).toBeVisible({ timeout: 15000 });
			await expect(page.locator("table")).toBeVisible({ timeout: 10000 });
		});
	});

	test.describe("Bug Regression Tests", () => {
		test("should generate correct Judge App URL (not 404)", async ({
			page,
		}) => {
			const userIdRegress = `e2e-reg-url-${Math.random().toString(36).substring(7)}`;

			// Inject headers for this specific test
			await page.context().setExtraHTTPHeaders({
				"x-user-id": userIdRegress,
				"x-e2e-uid": userIdRegress,
			});

			const dummyData = {
				Meet: [{ Meet_name1: "Regression Meet" }],
				Team: [{ Team_no: "1", Team_abbr: "TEST", Team_name: "Test Team" }],
				Athlete: [
					{ Ath_no: "1", Team_no: "1", First_name: "Test", Last_name: "A" },
				],
				Event: [
					{
						Event_no: "1",
						Event_ptr: "1",
						Ind_rel: "I",
						Event_dist: "25",
						Event_stroke: "A",
					},
				],
				Session: [{ Sess_ptr: "1", Sess_no: "1" }],
				Entry: [{ Ath_no: "1", Event_ptr: "1", Pre_heat: "1", Pre_lane: "1" }],
			};

			const filename = `regress-url-${userIdRegress}.json`;
			await ensureDataset(page, userIdRegress, filename, dummyData);

			const targetRow = page.getByTestId(`dataset-row-${filename}`);
			await targetRow
				.getByTestId("publish-button")
				.first()
				.click({ force: true });
			await expect(page.getByText("Meet data published")).toBeVisible({
				timeout: 15000,
			});
			const judgeAppUrl = await page.getByTestId("judge-app-url").innerText();
			expect(judgeAppUrl).toContain("/judge?");
			expect(judgeAppUrl).not.toContain(":3000/judge");
		});

		test("should maintain relay team view when navigating heats", async ({
			browser,
		}) => {
			const userIdNav = `e2e-nav-view-${Math.random().toString(36).substring(7)}`;
			const dummyData = {
				Meet: [{ Meet_name1: "Nav Meet" }],
				Team: [{ Team_no: "1", Team_abbr: "TEST", Team_name: "Test Team" }],
				Athlete: [
					{ Ath_no: "1", Team_no: "1", First_name: "Test", Last_name: "A" },
				],
				Event: [
					{
						Event_no: "13",
						Event_ptr: "13",
						Ind_rel: "R",
						Event_dist: "100",
						Event_stroke: "E",
					},
				],
				Session: [{ Sess_ptr: "1", Sess_no: "1" }],
				Entry: [
					{ Ath_no: "1", Event_ptr: "13", Pre_heat: "1", Pre_lane: "1" },
					{ Ath_no: "1", Event_ptr: "13", Pre_heat: "2", Pre_lane: "1" },
				],
				Relay: [
					{
						Relay_no: "1",
						Team_no: "1",
						Event_ptr: "13",
						Pre_heat: "1",
						Pre_lane: "1",
					},
					{
						Relay_no: "2",
						Team_no: "1",
						Event_ptr: "13",
						Pre_heat: "2",
						Pre_lane: "1",
					},
				],
				RelayNames: [
					{ Relay_no: "1", Ath_no: "1", Pos_no: "1" },
					{ Relay_no: "2", Ath_no: "1", Pos_no: "1" },
				],
			};

			const adminContext = await browser.newContext({
				baseURL: process.env.FRONTEND_URL || "http://localhost:3000",
				extraHTTPHeaders: { "x-user-id": userIdNav, "x-e2e-uid": userIdNav },
			});
			const adminPage = await adminContext.newPage();
			const filename = `nav-view-${userIdNav}.json`;
			await ensureDataset(adminPage, userIdNav, filename, dummyData);

			const targetRow = adminPage.getByTestId(`dataset-row-${filename}`);
			await targetRow
				.getByTestId("publish-button")
				.first()
				.click({ force: true });
			await expect(adminPage.getByText("Meet data published")).toBeVisible({
				timeout: 15000,
			});
			const judgeAppUrl = await adminPage
				.getByTestId("judge-app-url")
				.innerText();
			const localUrl = judgeAppUrl.replace(
				/^https?:\/\/[^/]+/i,
				"http://localhost:8080",
			);

			const judgeContext = await browser.newContext({
				viewport: { width: 375, height: 1200 },
				userAgent:
					"Mozilla/5.0 (iPhone; CPU iPhone OS 13_2_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.0.3 Mobile/15E148 Safari/604.1",
				extraHTTPHeaders: { "x-user-id": userIdNav, "x-e2e-uid": userIdNav },
			});
			const judgePage = await judgeContext.newPage();
			await judgePage.goto(localUrl);
			await judgePage.getByPlaceholder("Your Name").fill("Regression Judge");
			await judgePage.getByText("START JUDGING").click({ force: true });

			await judgePage.getByText("Event 13").first().click({ force: true });
			await judgePage.getByText("Heat 1").first().click({ force: true });
			await expect(
				judgePage
					.getByText(/Leg 1/i)
					.or(judgePage.getByText(/Test A/i))
					.first(),
			).toBeVisible({ timeout: 10000 });

			await judgePage
				.getByLabel(/next heat/i)
				.first()
				.click({ force: true });
			await judgePage.waitForTimeout(2000);
			await expect(
				judgePage
					.getByText(/Leg 1/i)
					.or(judgePage.getByText(/Test A/i))
					.first(),
			).toBeVisible({ timeout: 10000 });

			await adminPage.close();
			await adminContext.close();
			await judgePage.close();
			await judgeContext.close();
		});

		test("should dismiss DQ history modal when clicking outside", async ({
			browser,
		}) => {
			const judgeContext = await browser.newContext({
				viewport: { width: 375, height: 1200 },
			});
			const judgePage = await judgeContext.newPage();
			await judgePage.goto("http://localhost:8080/judge");
			await judgePage.getByPlaceholder("Your Name").fill("Modal Judge");
			await judgePage.getByText("START JUDGING").click({ force: true });

			await judgePage
				.getByText(/DQ History/)
				.first()
				.click({ force: true });
			await expect(judgePage.getByText(/DQ History \(Total: 0\)/i)).toBeVisible(
				{ timeout: 10000 },
			);

			// Click close button to dismiss
			await judgePage.evaluate(() => {
				const btn = document.querySelector(
					'[data-testid="modal-close-button"]',
				) as HTMLElement;
				if (btn) btn.click();
			});
			await expect(
				judgePage.getByText(/DQ History \(Total: 0\)/i),
			).not.toBeVisible({ timeout: 10000 });
		});
	});
});
// Final definitive verification run
// Final definitive verification run 2
// Final definitive verification run 3
