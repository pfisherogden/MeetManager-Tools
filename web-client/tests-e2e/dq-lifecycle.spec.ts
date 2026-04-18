import { expect, type Page, test } from "@playwright/test";

/**
 * End-to-End DQ Lifecycle User Journeys
 *
 * This test suite covers:
 * 1. Meet Administrator publishing data.
 * 2. S&T Judge entering DQs (Individual & Relay).
 * 3. Computer Volunteer reviewing and syncing DQs.
 */

test.describe.skip("Disqualification Lifecycle", () => {
	let judgePage: Page;
	let volunteerPage: Page;
	const userId = `e2e-dq-${Math.random().toString(36).substring(7)}`;

	test.beforeAll(async ({ browser }) => {
		// Create isolated contexts for Judge and Volunteer
		const judgeContext = await browser.newContext({
			baseURL: process.env.MOBILE_APP_URL || "http://localhost:8080",
			viewport: { width: 375, height: 667 }, // iPhone 6/7/8
			userAgent:
				"Mozilla/5.0 (iPhone; CPU iPhone OS 13_2_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.0.3 Mobile/15E148 Safari/604.1",
		});

		const volunteerContext = await browser.newContext({
			baseURL: process.env.FRONTEND_URL || "http://localhost:3000",
		});

		judgePage = await judgeContext.newPage();
		volunteerPage = await volunteerContext.newPage();

		// Set isolated User ID to avoid CI collisions
		await judgePage.setExtraHTTPHeaders({ "x-user-id": userId });
		await volunteerPage.setExtraHTTPHeaders({ "x-user-id": userId });

		await judgeContext.addCookies([
			{ name: "x-user-id", value: userId, domain: "localhost", path: "/" },
		]);
		await volunteerContext.addCookies([
			{ name: "x-user-id", value: userId, domain: "localhost", path: "/" },
		]);
	});

	test.afterAll(async () => {
		await judgePage.close();
		await volunteerPage.close();
	});

	test("Full DQ Journey: Publish -> Submit -> Sync -> Verify", async () => {
		// --- 1. Meet Administrator / Computer Volunteer: Setup ---
		console.log("Journey Step 1: Volunteer opening main app...");
		await volunteerPage.goto("/");
		await expect(
			volunteerPage.getByRole("heading", { name: "Dashboard" }),
		).toBeVisible();

		// --- 2. S&T Judge: Onboarding ---
		console.log("Journey Step 2: Judge onboarding...");
		await judgePage.goto("/");
		await judgePage.getByPlaceholder("Your Name").fill("Judge Alex");
		await judgePage.getByText("START JUDGING").click();
		await expect(judgePage.getByText("Events", { exact: true })).toBeVisible();

		// --- 3. S&T Judge: Submit Individual DQ ---
		console.log("Journey Step 3: Judge submitting individual DQ...");
		// Use Event 3 for individual Free
		await judgePage
			.getByText(/Event 3/i)
			.first()
			.click();
		await judgePage
			.getByText(/Heat 1/i)
			.first()
			.click();
		await judgePage.getByText("TAP TO DQ").first().click();

		// Select DQ code 1A
		await judgePage.getByText("1A").first().click();
		await judgePage
			.getByPlaceholder("Add notes here (optional)")
			.fill("False start on lane 1");
		await judgePage.getByLabel("Save changes").click();

		// Verify code is shown on the swimmer card
		await expect(
			judgePage.locator("#root").getByText("1A").first(),
		).toBeVisible();

		// --- 4. Computer Volunteer: Live Review (Individual) ---
		console.log("Journey Step 4: Volunteer verifying live DQ...");
		await volunteerPage.goto("/dqs");
		// Verify the DQ row exists
		await expect(
			volunteerPage.locator("tr").filter({ hasText: "1A" }),
		).toBeVisible();
		await expect(volunteerPage.getByText("Judge Alex")).toBeVisible();

		// --- 5. S&T Judge: Submit Relay DQ (Targeting Bug) ---
		console.log("Journey Step 5: Judge submitting relay DQ...");
		await judgePage.getByText("BACK").click(); // Back to heats
		await judgePage.getByText("EVENTS").click(); // Back to events
		await judgePage
			.getByText(/Event 1/i)
			.first()
			.click(); // Relay
		await judgePage
			.getByText(/Heat 1/i)
			.first()
			.click();

		// Find Leg 3 of Lane 1 Relay (nth(2) because 0-indexed)
		const leg3 = judgePage.getByText("TAP TO DQ").nth(2);
		await expect(leg3).toBeVisible();
		await leg3.click();
		await judgePage.getByText("7Q").first().click(); // Early take-off
		await judgePage.getByLabel("Save changes").click();

		// --- 6. Computer Volunteer: Verify Relay Swimmer Name ---
		console.log("Journey Step 6: Volunteer verifying relay swimmer name...");
		await volunteerPage.reload();
		await expect(
			volunteerPage.locator("tr").filter({ hasText: "7Q" }),
		).toBeVisible();

		// Verify relay swimmer name logic (The fix we implemented)
		// Seed for Event 1 Lane 1 has members: ["Alice S.", "Dana R.", "Zoe M.", "Mia K."]
		await expect(volunteerPage.getByText(/Zoe M/i)).toBeVisible();

		// --- 7. S&T Judge: Edit DQ ---
		console.log("Journey Step 7: Judge editing pending DQ...");
		await judgePage.getByText(/DQ History/).click();
		await judgePage.getByText("7Q").first().click();
		await judgePage
			.getByPlaceholder("Add notes here (optional)")
			.fill("Corrected: Early start on leg 3");
		await judgePage.getByLabel("Save changes").click();

		// --- 8. Computer Volunteer: Sync ---
		console.log("Journey Step 8: Volunteer verifying sync status...");
		// Check for the Synced status in the table
		await expect(volunteerPage.getByText("Synced").first()).toBeVisible();

		// --- 9. S&T Judge: Post-Sync Verification ---
		console.log("Journey Step 9: Judge verifying sync status...");
		await judgePage.getByText(/DQ History/).click();
		// In mobile app, the cloud icon changes to cloud-done
		await expect(judgePage.locator('css=[name="cloud-done"]')).toBeVisible();
	});
});
