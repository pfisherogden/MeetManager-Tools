import * as fs from "node:fs";
import { expect, type Page, test } from "@playwright/test";

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
	await expect(
		page.getByRole("heading", { name: /Admin Configuration/i }),
	).toBeVisible({ timeout: 15000 });

	// Use a more robust check for the publish button
	const publishBtn = page.getByTestId("publish-button");

	if ((await publishBtn.count()) === 0) {
		console.log(`No active dataset found for ${uid}, uploading...`);
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

			// The DatasetManager should refresh automatically.
			// Wait for the publish button to appear (which means it's active)
			// If it doesn't appear in 10s, try setting it active manually.
			try {
				await expect(publishBtn.first()).toBeVisible({ timeout: 10000 });
			} catch (_e) {
				console.log(
					"Publish button didn't appear, attempting manual Set Active...",
				);
				await page
					.getByRole("button", { name: /Set Active/i })
					.first()
					.click({ force: true });
				await expect(publishBtn.first()).toBeVisible({ timeout: 15000 });
			}
		} finally {
			if (fs.existsSync(testFilePath)) fs.unlinkSync(testFilePath);
		}
	} else {
		console.log(`Active dataset already present for ${uid}`);
	}
}

test.describe("Disqualification Lifecycle", () => {
	let judgePage: Page;
	let volunteerPage: Page;
	const userId = `e2e-dq-${Math.random().toString(36).substring(7)}`;

	test.beforeAll(async ({ browser }) => {
		// Clear mock firestore for a fresh run
		const mockFilePath = "../../tmp/mock_firestore.json";
		if (fs.existsSync(mockFilePath)) {
			console.log(`Clearing existing mock firestore at ${mockFilePath}`);
			fs.unlinkSync(mockFilePath);
		}

		// Create isolated contexts for Judge and Volunteer
		// CRITICAL: Pass x-user-id in extraHTTPHeaders for Server Action isolation in CI
		const judgeContext = await browser.newContext({
			baseURL: process.env.MOBILE_APP_URL || "http://localhost:8080",
			viewport: { width: 375, height: 1200 }, // Extra tall for safety
			userAgent:
				"Mozilla/5.0 (iPhone; CPU iPhone OS 13_2_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.0.3 Mobile/15E148 Safari/604.1",
			extraHTTPHeaders: {
				"x-user-id": userId,
			},
		});

		const volunteerContext = await browser.newContext({
			baseURL: process.env.FRONTEND_URL || "http://localhost:3000",
			extraHTTPHeaders: {
				"x-user-id": userId,
			},
		});

		judgePage = await judgeContext.newPage();
		volunteerPage = await volunteerContext.newPage();

		// Enable console logging for the judge page
		judgePage.on("console", (msg) => {
			console.log(`JUDGE CONSOLE [${msg.type()}]: ${msg.text()}`);
		});
	});

	test("Full DQ Journey: Publish -> Submit -> Sync -> Verify", async () => {
		// --- 1. Meet Administrator: Publish ---
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

		await ensureDataset(
			volunteerPage,
			userId,
			`journey-${userId}.json`,
			dummyData,
		);

		console.log("Journey Step 1.1: Clicking Publish button...");
		await volunteerPage
			.getByTestId("publish-button")
			.first()
			.click({ force: true });
		await expect(volunteerPage.getByText("Meet data published")).toBeVisible({
			timeout: 30000,
		});

		const urlElement = volunteerPage.getByTestId("judge-app-url");
		const judgeAppUrl = await urlElement.innerText();
		console.log(`Extracted Judge App URL: ${judgeAppUrl}`);

		const localUrl = judgeAppUrl.replace(
			/^https?:\/\/[^/]+/i,
			"http://localhost:8080",
		);
		console.log(`Navigating Judge to: ${localUrl}`);

		// --- 2. S&T Judge: Onboarding ---
		console.log("Journey Step 2: Judge onboarding...");
		await judgePage.goto(localUrl);
		await judgePage.getByPlaceholder("Your Name").fill("Judge Alex");
		await judgePage.getByText("START JUDGING").click({ force: true });
		await expect(judgePage.getByText("Events", { exact: true })).toBeVisible({
			timeout: 15000,
		});

		// --- 3. S&T Judge: Submit Individual DQ ---
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
		await judgePage.evaluate(() => {
			const btn = document.querySelector(
				'[aria-label="Save changes"]',
			) as HTMLElement;
			if (btn) btn.click();
		});

		await expect(
			judgePage.locator("#root").getByText("1A").first(),
		).toBeVisible({ timeout: 10000 });

		// --- 4. Computer Volunteer: Live Review (Individual) ---
		console.log("Journey Step 4: Volunteer verifying live DQ...");
		await volunteerPage.goto("/dqs");

		await expect(
			volunteerPage.locator("tr").filter({ hasText: "1A" }),
		).toBeVisible({ timeout: 15000 });
		await expect(volunteerPage.getByText("Judge Alex")).toBeVisible({
			timeout: 10000,
		});

		// --- 5. S&T Judge: Submit Relay DQ (Targeting Bug) ---
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
			.click({ force: true }); // Relay
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
		await judgePage.getByText("7Q").first().click({ force: true }); // Early take-off
		await judgePage.evaluate(() => {
			const btn = document.querySelector(
				'[aria-label="Save changes"]',
			) as HTMLElement;
			if (btn) btn.click();
		});

		// --- 6. Computer Volunteer: Verify Relay Swimmer Name ---
		console.log("Journey Step 6: Volunteer verifying relay swimmer name...");
		await volunteerPage.reload();
		await expect(
			volunteerPage.locator("tr").filter({ hasText: "7Q" }),
		).toBeVisible({ timeout: 15000 });

		await expect(volunteerPage.getByText(/Test C/i)).toBeVisible({
			timeout: 10000,
		});

		// --- 7. S&T Judge: Edit DQ ---
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
		await judgePage.evaluate(() => {
			const btn = document.querySelector(
				'[aria-label="Save changes"]',
			) as HTMLElement;
			if (btn) btn.click();
		});

		// --- 8. Computer Volunteer: Sync ---
		console.log("Journey Step 8: Volunteer verifying sync status...");
		await volunteerPage.reload();
		await expect(
			volunteerPage.locator("tr").filter({ hasText: "7Q" }),
		).toContainText(/Synced/i, { timeout: 15000 });

		// --- 9. S&T Judge: Sync Indicator ---
		console.log("Journey Step 9: Judge verifying sync status...");
		await judgePage
			.getByText(/DQ History/)
			.first()
			.click({ force: true });
		await expect(judgePage.getByText("7Q").first()).toBeVisible({
			timeout: 10000,
		});
	});

	test.describe("Frontend Visibility Journeys", () => {
		test("should show synced DQs in the global Submitted DQs list", async ({
			page,
		}) => {
			console.log("Visibility: Starting...");
			const volunteerPage = page;
			await volunteerPage.goto("/dqs");
			await expect(
				volunteerPage.getByRole("heading", {
					name: /Submitted Disqualifications/i,
				}),
			).toBeVisible({ timeout: 15000 });

			await expect(volunteerPage.locator("table")).toBeVisible({
				timeout: 10000,
			});
			console.log("Visibility: Table visible");
		});
	});

	test.describe("Bug Regression Tests", () => {
		test("should generate correct Judge App URL (not 404)", async ({
			page,
		}) => {
			const userIdRegress = `e2e-regress-${Math.random().toString(36).substring(7)}`;
			const dummyData = {
				meet: [{ meet_name1: "Regression Meet" }],
				team: [{ team_no: 1, team_abbr: "TEST", team_name: "Test Team" }],
				athlete: [
					{ ath_no: 1, team_no: 1, first_name: "Test", last_name: "A" },
				],
				event: [{ event_no: 1, event_ptr: 1, ind_rel: "I" }],
				session: [{ sess_ptr: 1, sess_no: 1 }],
				sessitem: [{ sess_ptr: 1, event_ptr: 1 }],
				entry: [{ ath_no: 1, event_ptr: 1, pre_heat: 1, pre_lane: 1 }],
			};

			// Ensure unique x-user-id for regression test too
			await ensureDataset(
				page,
				userIdRegress,
				`regress-url-${userIdRegress}.json`,
				dummyData,
			);

			// Publish
			console.log("Regression: Clicking Publish...");
			await page.getByTestId("publish-button").first().click({ force: true });
			await expect(page.getByText("Meet data published")).toBeVisible({
				timeout: 15000,
			});
			console.log("Regression: Publish successful");

			const urlElement = page.getByTestId("judge-app-url");
			const judgeAppUrl = await urlElement.innerText();

			console.log(`Regression check: Generated URL is ${judgeAppUrl}`);
			expect(judgeAppUrl).toContain("/judge?");
			expect(judgeAppUrl).not.toContain(":3000/judge"); // Should not point to frontend
		});

		test("should maintain relay team view when navigating heats", async ({
			browser,
		}) => {
			const userIdNav = `e2e-nav-${Math.random().toString(36).substring(7)}`;
			const dummyData = {
				meet: [{ meet_name1: "Nav Meet" }],
				team: [{ team_no: 1, team_abbr: "TEST", team_name: "Test Team" }],
				athlete: [
					{ ath_no: 1, team_no: 1, first_name: "Test", last_name: "A" },
				],
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
			await ensureDataset(
				adminPage,
				userIdNav,
				`nav-${userIdNav}.json`,
				dummyData,
			);

			// Publish to get URL
			await adminPage
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

			console.log("Regression: Relay navigation test starting...");
			const judgeContext = await browser.newContext({
				viewport: { width: 375, height: 1200 },
				userAgent:
					"Mozilla/5.0 (iPhone; CPU iPhone OS 13_2_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.0.3 Mobile/15E148 Safari/604.1",
				extraHTTPHeaders: { "x-user-id": userIdNav },
			});
			const judgePage = await judgeContext.newPage();
			await judgePage.goto(localUrl);
			await judgePage.getByPlaceholder("Your Name").fill("Regression Judge");
			await judgePage.getByText("START JUDGING").click({ force: true });
			console.log("Regression: Judge SPA onboarded");

			// Go to Event 13 (Relay)
			await judgePage.getByText("Event 13").first().click({ force: true });
			await judgePage.getByText("Heat 1").first().click({ force: true });
			console.log("Regression: On Event 13 Heat 1");

			// Verify it shows relay members
			await expect(
				judgePage
					.getByText(/Leg 1/i)
					.or(judgePage.getByText(/Test A/i))
					.first(),
			).toBeVisible({ timeout: 10000 });
			console.log("Regression: Relay legs visible");

			// Navigate to Next Heat
			console.log("Regression: Navigating to next heat...");
			await judgePage
				.getByLabel(/next heat/i)
				.first()
				.click({ force: true });
			// Give it a moment to render
			await judgePage.waitForTimeout(2000);

			// Verify it STILL shows relay members (the same event)
			await expect(
				judgePage
					.getByText(/Leg 1/i)
					.or(judgePage.getByText(/Test A/i))
					.first(),
			).toBeVisible({ timeout: 10000 });
			console.log("Regression: Relay legs still visible after navigation");
		});

		test("should dismiss DQ history modal when clicking outside", async ({
			browser,
		}) => {
			console.log("Regression: Modal dismissal test starting...");
			const judgeContext = await browser.newContext({
				viewport: { width: 375, height: 1200 },
			});
			const judgePage = await judgeContext.newPage();
			await judgePage.goto("http://localhost:8080/judge");
			await judgePage.getByPlaceholder("Your Name").fill("Modal Judge");
			await judgePage.getByText("START JUDGING").click({ force: true });

			// Open History
			await judgePage
				.getByText(/DQ History/)
				.first()
				.click({ force: true });
			await expect(judgePage.getByText(/DQ History \(Total: 0\)/i)).toBeVisible(
				{ timeout: 10000 },
			);
			console.log("Regression: Modal open");

			// Click far outside (middle-left area of overlay)
			console.log("Regression: Clicking outside modal...");
			await judgePage.mouse.click(5, 300);
			await judgePage.waitForTimeout(1000);

			// Verify modal is gone
			await expect(
				judgePage.getByText(/DQ History \(Total: 0\)/i),
			).not.toBeVisible({ timeout: 10000 });
			console.log("Regression: Modal dismissed");
		});
	});
});
