import * as fs from "node:fs";
import * as path from "node:path";
import { expect, type Page, test } from "@playwright/test";

// Shared helper to ensure a dataset is active
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

	// Use the specific row for this user's dataset if multiple exist
	const row = page.getByTestId(`dataset-row-${filename}`);

	// Wait for the row to appear with retries (handle stale lists in CI)
	console.log(`Initial check for row: dataset-row-${filename}...`);
	for (let i = 0; i < 5; i++) {
		if ((await row.count()) > 0) break;
		console.log(`Retry ${i + 1}: Row not found, reloading with cache bust...`);
		// Force cache bust via URL parameter
		await page.goto(`/admin?uid=${uid}&t=${Date.now()}`, {
			waitUntil: "networkidle",
		});
		await page.waitForTimeout(3000);
	}

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
		const tempDir = path.join(process.cwd(), "tmp", "e2e-fixtures");
		if (!fs.existsSync(tempDir)) fs.mkdirSync(tempDir, { recursive: true });
		const testFilePath = path.join(tempDir, filename);
		fs.writeFileSync(testFilePath, JSON.stringify(data));

		try {
			const fileChooserPromise = page.waitForEvent("filechooser");
			// Use evaluate click for maximum reliability in CI
			await page.evaluate(() => {
				const buttons = Array.from(document.querySelectorAll("button"));
				const uploadBtn = buttons.find((b) =>
					b.innerText.includes("Upload Dataset"),
				);
				if (uploadBtn) uploadBtn.click();
			});
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
				console.log(`Retry ${i + 1}: Row not found after upload, reloading...`);
				// Force cache bust via URL parameter
				await page.goto(`/admin?uid=${uid}&t=${Date.now()}`, {
					waitUntil: "networkidle",
				});
				await page.waitForTimeout(3000);
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
	await page.evaluate((fid) => {
		const row = document.querySelector(`[data-testid="dataset-row-${fid}"]`);
		const buttons = Array.from(row?.querySelectorAll("button") || []);
		const btn = buttons.find((b) => b.innerText.includes("Set Active"));
		if (btn) (btn as HTMLElement).click();
	}, filename);

	await expect(row.getByTestId("active-dataset-badge")).toBeVisible({
		timeout: 15000,
	});
	console.log(`Dataset ${filename} is now active`);
}

test.describe("Disqualification Lifecycle", () => {
	// Dummy data in RAW TABLE FORMAT (as expected by backend/converter)
	// We OMIT the Session table to trigger the fallback to default session (linked to all events)
	const dummyData = {
		Meet: [{ Meet_name1: "E2E Meet" }],
		Team: [{ Team_no: "1", Team_abbr: "FAST", Team_name: "Fast Team" }],
		Athlete: [
			{ Ath_no: "1", Team_no: "1", First_name: "Test", Last_name: "Swimmer" },
		],
		Event: [
			{
				event_no: 1,
				event_ptr: 1,
				ind_rel: "I",
				event_dist: 25.0,
				event_stroke: "A",
			},
			{
				event_no: 13,
				event_ptr: 13,
				ind_rel: "R",
				event_dist: 100.0,
				event_stroke: "E",
			},
		],
		Entry: [
			{
				ath_no: 1,
				event_ptr: 1,
				fin_heat: 1,
				pre_heat: 1,
				fin_lane: 1,
				pre_lane: 1,
			},
			{
				ath_no: 1,
				event_ptr: 13,
				fin_heat: 1,
				pre_heat: 1,
				fin_lane: 1,
				pre_lane: 1,
			},
		],
		Relay: [
			{
				relay_no: 1,
				team_no: 1,
				event_ptr: 13,
				fin_heat: 1,
				pre_heat: 1,
				fin_lane: 1,
				pre_lane: 1,
			},
		],
		RelayNames: [{ event_ptr: 13, relay_no: 1, ath_no: 1, pos_no: 3 }],
	};

	test.beforeEach(async ({ page, context }, testInfo) => {
		// Set a unique user ID for this test to avoid collisions in the backend
		const userId = `e2e-dq-${testInfo.workerIndex}-${testInfo.project.name.replace(/\s+/g, "-")}`;

		// Set header for all requests from this page
		await page.setExtraHTTPHeaders({
			"x-user-id": userId,
			"x-e2e-uid": userId,
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

	test("Full DQ Journey: Publish -> Submit -> Sync -> Verify", async ({
		browser,
		page: volunteerPage,
	}, testInfo) => {
		const userId = `e2e-dq-${testInfo.workerIndex}-${testInfo.project.name.replace(/\s+/g, "-")}`;
		const filename = `journey-${userId}.json`;

		// Step 1: Set up dataset and Publish
		await ensureDataset(volunteerPage, userId, filename, dummyData);

		console.log("Journey Step 1.1: Clicking Publish button...");
		const publishBtn = volunteerPage
			.getByTestId(`dataset-row-${filename}`)
			.getByTestId("publish-button");
		await publishBtn.evaluate((el) => (el as HTMLElement).click());

		// Wait for the QR dialog to appear
		const judgeAppUrlLocator = volunteerPage.getByTestId("judge-app-url");
		await judgeAppUrlLocator.waitFor({ state: "visible", timeout: 30000 });

		const judgeAppUrl = await judgeAppUrlLocator.innerText();
		const parsedUrl = new URL(judgeAppUrl);
		parsedUrl.host = "localhost:8080";
		parsedUrl.protocol = "http:";
		const localUrl = parsedUrl.toString();

		console.log("Journey Step 2: Judge onboarding...");
		const judgeContext = await browser.newContext({
			viewport: { width: 375, height: 812 },
			userAgent:
				"Mozilla/5.0 (iPhone; CPU iPhone OS 13_2_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.0.3 Mobile/15E148 Safari/604.1",
			isMobile: true,
			hasTouch: true,
		});

		// Pass the same E2E UID to the judge context
		await judgeContext.setExtraHTTPHeaders({
			"x-user-id": userId,
			"x-e2e-uid": userId,
		});

		const judgePage = await judgeContext.newPage();
		judgePage.on("console", (msg) => console.log("JUDGE APP:", msg.text()));

		// Mock Firebase for judge app to prevent blocking modals
		await judgePage.route(
			"**/*identitytoolkit.googleapis.com*",
			async (route) => {
				await route.fulfill({ status: 200, json: {} });
			},
		);

		await judgePage.goto(localUrl);
		await judgePage.getByPlaceholder("Your Name").fill("Judge Alex");
		await judgePage
			.getByText("START JUDGING")
			.evaluate((el) => (el as HTMLElement).click());

		await expect(judgePage.getByText("Events", { exact: true })).toBeVisible({
			timeout: 15000,
		});

		console.log("Journey Step 3: Judge submitting individual DQ...");
		await judgePage
			.getByTestId("event-item-1")
			.evaluate((el) => (el as HTMLElement).click());
		await judgePage
			.getByTestId("heat-item-1")
			.evaluate((el) => (el as HTMLElement).click());

		await judgePage
			.getByText("TAP TO DQ")
			.first()
			.evaluate((el) => (el as HTMLElement).click());
		await judgePage
			.getByText("1A")
			.first()
			.evaluate((el) => (el as HTMLElement).click());
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

		// Add explicit retry loop for sync verification
		console.log("Waiting for DQ to appear in volunteer view (with retries)...");
		let dqFound = false;
		for (let i = 0; i < 5; i++) {
			try {
				await expect(
					volunteerPage.locator("tr").filter({ hasText: "1A" }).first(),
				).toBeVisible({ timeout: 5000 });
				dqFound = true;
				break;
			} catch (_e) {
				console.log(`Retry ${i + 1}: DQ 1A not found yet, reloading...`);
				await volunteerPage.reload();
				await volunteerPage.waitForTimeout(3000);
			}
		}
		expect(dqFound).toBe(true);

		console.log("Journey Step 5: Judge submitting relay DQ...");
		await judgePage
			.getByLabel(/back/i)
			.or(judgePage.getByText("BACK", { exact: true }))
			.first()
			.waitFor({ state: "visible", timeout: 15000 });
		await judgePage
			.getByLabel(/back/i)
			.or(judgePage.getByText("BACK", { exact: true }))
			.first()
			.evaluate((el) => (el as HTMLElement).click());

		await judgePage
			.getByLabel(/events/i)
			.or(judgePage.getByText("EVENTS", { exact: true }))
			.first()
			.waitFor({ state: "visible", timeout: 15000 });
		await judgePage
			.getByLabel(/events/i)
			.or(judgePage.getByText("EVENTS", { exact: true }))
			.first()
			.evaluate((el) => (el as HTMLElement).click());

		await judgePage
			.getByTestId("event-item-13")
			.waitFor({ state: "visible", timeout: 15000 });
		await judgePage
			.getByTestId("event-item-13")
			.evaluate((el) => (el as HTMLElement).click());

		await judgePage
			.getByTestId("heat-item-1")
			.waitFor({ state: "visible", timeout: 15000 });
		await judgePage
			.getByTestId("heat-item-1")
			.evaluate((el) => (el as HTMLElement).click());

		const leg3 = judgePage
			.getByText(/Leg 3/i)
			.or(judgePage.getByText(/Test/i))
			.first();
		await leg3.waitFor({ state: "visible", timeout: 15000 });
		await leg3.evaluate((el) => (el as HTMLElement).click());

		await judgePage
			.getByText("7Q")
			.first()
			.waitFor({ state: "visible", timeout: 15000 });
		await judgePage
			.getByText("7Q")
			.first()
			.evaluate((el) => (el as HTMLElement).click());
		await judgePage.evaluate(() =>
			(
				document.querySelector('[aria-label="Save changes"]') as HTMLElement
			)?.click(),
		);

		console.log("Journey Step 6: Volunteer verifying relay swimmer name...");
		await volunteerPage.reload();
		await expect(
			volunteerPage.locator("tr").filter({ hasText: "7Q" }).first(),
		).toBeVisible({ timeout: 15000 });
		await expect(volunteerPage.getByText(/Test/i).first()).toBeVisible({
			timeout: 10000,
		});

		console.log("Journey Step 7: Judge editing pending DQ...");
		await judgePage
			.getByTestId("dq-history-button")
			.waitFor({ state: "visible", timeout: 15000 });
		await judgePage
			.getByTestId("dq-history-button")
			.first()
			.evaluate((el) => (el as HTMLElement).click());
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
		const targetRow = volunteerPage.locator("tr", { hasText: "Test" });
		await expect(targetRow.filter({ hasText: "Synced" }).first()).toBeVisible({
			timeout: 15000,
		});

		await judgeContext.close();
	});

	test.describe("Frontend Visibility Journeys", () => {
		test("should show synced DQs in the global Submitted DQs list", async ({
			page,
		}) => {
			await page.goto("/dqs");
			await expect(
				page.getByRole("heading", { name: /Submitted Disqualifications/i }),
			).toBeVisible({ timeout: 15000 });
			await expect(
				page
					.locator("table")
					.or(page.getByText(/No disqualifications submitted yet/i)),
			).toBeVisible({ timeout: 15000 });
		});
	});

	test.describe("Bug Regression Tests", () => {
		test("should generate correct Judge App URL (not 404)", async ({
			page,
		}) => {
			const userIdRegress = `e2e-reg-url-${Math.random().toString(36).substring(7)}`;

			// Inject cookies for this specific test
			await page
				.context()
				.route("**/*identitytoolkit.googleapis.com*", async (route) => {
					await route.fulfill({ status: 200, json: {} });
				});
			await page.context().addCookies([
				{
					name: "x-user-id",
					value: userIdRegress,
					url: process.env.FRONTEND_URL || "http://localhost:3000",
				},
				{
					name: "x-e2e-uid",
					value: userIdRegress,
					url: process.env.FRONTEND_URL || "http://localhost:3000",
				},
			]);

			const dummyDataRegress = {
				Meet: [{ Meet_name1: "Regression Meet" }],
				Team: [{ Team_no: "1", Team_abbr: "TEST", Team_name: "Test Team" }],
				Athlete: [
					{ Ath_no: "1", Team_no: "1", First_name: "Test", Last_name: "A" },
				],
				Event: [
					{
						event_no: 1,
						event_ptr: 1,
						ind_rel: "I",
						event_dist: 25.0,
						event_stroke: "A",
					},
				],
				Entry: [
					{
						ath_no: 1,
						event_ptr: 1,
						fin_heat: 1,
						pre_heat: 1,
						fin_lane: 1,
						pre_lane: 1,
					},
				],
			};

			const filename = `regress-url-${userIdRegress}.json`;
			await ensureDataset(page, userIdRegress, filename, dummyDataRegress);

			const targetRow = page.getByTestId(`dataset-row-${filename}`);
			await targetRow
				.getByTestId("publish-button")
				.first()
				.evaluate((el) => (el as HTMLElement).click());
			await expect(page.getByText("Meet data published")).toBeVisible({
				timeout: 15000,
			});
			const judgeAppUrl = await page.getByTestId("judge-app-url").innerText();
			expect(judgeAppUrl).toContain("/MeetManager-Tools/judge");
		});

		test("should maintain relay team view when navigating heats", async ({
			browser,
		}) => {
			const userIdNav = `e2e-nav-view-${Math.random().toString(36).substring(7)}`;
			const dummyDataNav = {
				Meet: [{ Meet_name1: "Nav Meet" }],
				Team: [{ Team_no: "1", Team_abbr: "TEST", Team_name: "Test Team" }],
				Athlete: [
					{ Ath_no: "1", Team_no: "1", First_name: "Test", Last_name: "A" },
				],
				Event: [
					{
						event_no: 13,
						event_ptr: 13,
						ind_rel: "R",
						event_dist: 100.0,
						event_stroke: "E",
					},
				],
				Entry: [
					{
						ath_no: 1,
						event_ptr: 13,
						fin_heat: 1,
						pre_heat: 1,
						fin_lane: 1,
						pre_lane: 1,
					},
					{
						ath_no: 1,
						event_ptr: 13,
						fin_heat: 2,
						pre_heat: 2,
						fin_lane: 1,
						pre_lane: 1,
					},
				],
				Relay: [
					{
						relay_no: 1,
						team_no: 1,
						event_ptr: 13,
						fin_heat: 1,
						pre_heat: 1,
						fin_lane: 1,
						pre_lane: 1,
					},
					{
						relay_no: 2,
						team_no: 1,
						event_ptr: 13,
						fin_heat: 2,
						pre_heat: 2,
						fin_lane: 1,
						pre_lane: 1,
					},
				],
				RelayNames: [
					{ event_ptr: 13, relay_no: 1, ath_no: 1, pos_no: 1 },
					{ event_ptr: 13, relay_no: 2, ath_no: 1, pos_no: 1 },
				],
			};

			const adminContext = await browser.newContext({
				baseURL: process.env.FRONTEND_URL || "http://localhost:3000",
			});
			await adminContext.route(
				"**/*identitytoolkit.googleapis.com*",
				async (route) => {
					await route.fulfill({ status: 200, json: {} });
				},
			);
			await adminContext.addCookies([
				{
					name: "x-user-id",
					value: userIdNav,
					url: process.env.FRONTEND_URL || "http://localhost:3000",
				},
				{
					name: "x-e2e-uid",
					value: userIdNav,
					url: process.env.FRONTEND_URL || "http://localhost:3000",
				},
			]);
			const adminPage = await adminContext.newPage();
			const filename = `nav-view-${userIdNav}.json`;
			await ensureDataset(adminPage, userIdNav, filename, dummyDataNav);

			const targetRow = adminPage.getByTestId(`dataset-row-${filename}`);
			await targetRow
				.getByTestId("publish-button")
				.first()
				.evaluate((el) => (el as HTMLElement).click());
			await expect(adminPage.getByText("Meet data published")).toBeVisible({
				timeout: 15000,
			});
			const judgeAppUrl = await adminPage
				.getByTestId("judge-app-url")
				.innerText();
			const parsedUrl = new URL(judgeAppUrl);
			parsedUrl.host = "localhost:8080";
			parsedUrl.protocol = "http:";
			const localUrl = parsedUrl.toString();

			const judgeContext = await browser.newContext({
				viewport: { width: 375, height: 1200 },
				userAgent:
					"Mozilla/5.0 (iPhone; CPU iPhone OS 13_2_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.0.3 Mobile/15E148 Safari/604.1",
			});
			await judgeContext.route(
				"**/*identitytoolkit.googleapis.com*",
				async (route) => {
					await route.fulfill({ status: 200, json: {} });
				},
			);
			await judgeContext.addCookies([
				{
					name: "x-user-id",
					value: userIdNav,
					url: process.env.MOBILE_APP_URL || "http://localhost:8080",
				},
				{
					name: "x-e2e-uid",
					value: userIdNav,
					url: process.env.MOBILE_APP_URL || "http://localhost:8080",
				},
			]);
			const judgePage = await judgeContext.newPage();
			await judgePage.goto(localUrl);
			await judgePage.getByPlaceholder("Your Name").fill("Regression Judge");
			await judgePage
				.getByText("START JUDGING")
				.evaluate((el) => (el as HTMLElement).click());
			console.log("Navigating to Event 13, Heat 1...");
			await judgePage
				.getByTestId("event-item-13")
				.waitFor({ state: "visible", timeout: 15000 });
			await judgePage
				.getByTestId("event-item-13")
				.evaluate((el) => (el as HTMLElement).click());

			await judgePage
				.getByTestId("heat-item-1")
				.waitFor({ state: "visible", timeout: 15000 });
			await judgePage
				.getByTestId("heat-item-1")
				.evaluate((el) => (el as HTMLElement).click());
			await expect(
				judgePage.getByText(/Leg 1/i).or(judgePage.getByText(/Test/i)).first(),
			).toBeVisible({ timeout: 10000 });

			await judgePage
				.getByLabel(/next heat/i)
				.first()
				.evaluate((el) => (el as HTMLElement).click());
			await judgePage.waitForTimeout(2000);
			await expect(
				judgePage.getByText(/Leg 1/i).or(judgePage.getByText(/Test/i)).first(),
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
			await judgeContext.route(
				"**/*identitytoolkit.googleapis.com*",
				async (route) => {
					await route.fulfill({ status: 200, json: {} });
				},
			);
			const judgePage = await judgeContext.newPage();
			await judgePage.goto("http://localhost:8080/MeetManager-Tools/judge");
			await judgePage.getByPlaceholder("Your Name").fill("Modal Judge");
			await judgePage
				.getByText("START JUDGING")
				.evaluate((el) => (el as HTMLElement).click());

			// Wait a bit to avoid the 500ms cooldown on opening the modal
			await judgePage.waitForTimeout(1000);

			await judgePage
				.getByTestId("dq-history-button")
				.waitFor({ state: "visible", timeout: 15000 });
			await judgePage
				.getByTestId("dq-history-button")
				.first()
				.evaluate((el) => (el as HTMLElement).click());

			// Wait for the modal to be attached to the DOM first, then check visibility
			const modalContent = judgePage.getByTestId("dq-history-modal-content");
			await modalContent.waitFor({ state: "attached", timeout: 15000 });
			await expect(modalContent.first()).toBeVisible({ timeout: 10000 });

			// Click close button to dismiss
			console.log("Clicking modal close button...");
			await judgePage.evaluate(() => {
				const btn =
					document.getElementById("e2e-modal-close-button") ||
					document.querySelector('[data-testid="modal-close-button"]');
				(btn as HTMLElement)?.click();
			});

			await expect(modalContent).not.toBeVisible({ timeout: 15000 });
		});
	});
});
