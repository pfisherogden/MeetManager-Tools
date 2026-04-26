import { expect, test } from "@playwright/test";
import { robustClick } from "./utils";

test.describe("Mobile Judge App Journey", () => {
	test.beforeEach(async ({ page, context }, testInfo) => {
		// Set a unique user ID for this test to avoid collisions in the backend
		// UNLESS we are in auth bypass mode, then we MUST use the fixed UID.
		const userId =
			process.env.NEXT_PUBLIC_E2E_AUTH_BYPASS === "true"
				? "e2e-bypass-user"
				: `e2e-judge-${testInfo.workerIndex}-${testInfo.project.name.replace(/\s+/g, "-")}`;

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

	// Set baseURL to the judge app endpoint.
	// In local dev, the judge app is mounted as a static directory in the frontend.
	test.use({
		baseURL: process.env.MOBILE_APP_URL || "http://localhost:3100/judge/",
		viewport: { width: 390, height: 1200 }, // Ensure tall enough for all DQ codes
	});

	test("should allow adding a DQ in individual event", async ({ page }) => {
		console.log("[Judge] Navigating to /...");
		await page.goto("/", { waitUntil: "networkidle" });
		await expect(page.getByPlaceholder("Your Name")).toBeVisible({
			timeout: 30000,
		});

		// 0. Handle Judge Name Prompt
		console.log("[Judge] Filling name prompt...");
		const nameInput = page.getByPlaceholder("Your Name");
		await nameInput.fill("E2E Test Judge");

		console.log("[Judge] Clicking START JUDGING...");
		await robustClick(page.getByText("START JUDGING"));

		// 1. Verify we are on the Events view
		await expect(page.getByText("Events", { exact: true })).toBeVisible();

		// 2. Tap an individual event (e.g., Event 1)
		const event1 = page.getByText(/#1 |Event 1/i).first();
		await robustClick(event1);

		// 3. Tap a heat (e.g., Heat 1)
		const heat1 = page.getByText(/Heat 1/i).first();
		await robustClick(heat1);

		// 4. Tap "TAP TO DQ" for a swimmer
		const tapToDq = page.getByText("TAP TO DQ").first();
		await robustClick(tapToDq);

		// 5. Verify DQ Modal opens
		await expect(
			page.getByPlaceholder("Add notes here (optional)"),
		).toBeVisible();

		// 6. Select a DQ code (e.g., "1A") via new data-testid
		const code1A_selector = "[data-testid='dq-code-1A']";
		// First, wait for the element to be attached to the DOM
		await page.waitForSelector(code1A_selector, {
			state: "attached",
			timeout: 10000,
		});
		// Then, use page.evaluate to scroll and click it
		await page.evaluate((selector) => {
			const element = document.querySelector(selector) as HTMLElement;
			if (element) {
				element.scrollIntoView({ block: "center" });
				element.click();
			} else {
				throw new Error(
					`E2E Error: Element with selector "${selector}" not found in the DOM.`,
				);
			}
		}, code1A_selector);

		// 7. Add a note
		await page
			.getByPlaceholder("Add notes here (optional)")
			.fill("Test DQ Note");

		// 8. Tap Save (checkmark-circle icon)
		const saveBtn = page.getByLabel("Save changes");
		await robustClick(saveBtn);

		// 9. Verification: Modal closes and DQ code is displayed
		await expect(
			page.getByPlaceholder("Add notes here (optional)"),
		).not.toBeVisible();
		await expect(page.getByText("1A")).toBeVisible();

		// 10. Verification: DQ History count increments
		await expect(page.getByText(/DQ History \(Pending: 1\)/)).toBeVisible();
	});

	test("should toggle between Event and Program views", async ({ page }) => {
		await page.goto("/", { waitUntil: "networkidle" });
		await expect(page.getByPlaceholder("Your Name")).toBeVisible({
			timeout: 30000,
		});

		// 0. Handle Judge Name Prompt
		const nameInput = page.getByPlaceholder("Your Name");
		await nameInput.fill("E2E Test Judge");
		await robustClick(page.getByText("START JUDGING"));

		// Default is Event view
		await expect(page.getByText("Events", { exact: true })).toBeVisible();

		// Switch to Program view
		const programBtn = page.getByText("SWITCH TO PROGRAM VIEW");
		await robustClick(programBtn);

		// Verify Program View is shown
		await expect(page.getByText("SWITCH TO EVENT VIEW")).toBeVisible();

		// In program mode, check if we see event headers
		await expect(page.getByText(/#1 |Event 1/i).first()).toBeVisible();

		// Switch back
		const eventViewBtn = page.getByText("SWITCH TO EVENT VIEW");
		await robustClick(eventViewBtn);
		await expect(page.getByText("Events", { exact: true })).toBeVisible();
	});

	test("should manage offline queue (clear all)", async ({ page }) => {
		await page.goto("/", { waitUntil: "networkidle" });
		await expect(page.getByPlaceholder("Your Name")).toBeVisible({
			timeout: 30000,
		});

		// 0. Handle Judge Name Prompt
		const nameInput = page.getByPlaceholder("Your Name");
		await nameInput.fill("E2E Test Judge");
		await robustClick(page.getByText("START JUDGING"));

		// Add a DQ first
		await robustClick(page.getByText(/#1 |Event 1/i).first());
		await robustClick(page.getByText(/Heat 1/i).first());
		await robustClick(page.getByText("TAP TO DQ").first());

		const code1A_selector = "[data-testid='dq-code-1A']";
		await page.waitForSelector(code1A_selector, {
			state: "attached",
			timeout: 10000,
		});
		await page.evaluate((selector) => {
			const element = document.querySelector(selector) as HTMLElement;
			if (element) {
				element.scrollIntoView({ block: "center" });
				element.click();
			} else {
				throw new Error(
					`E2E Error: Element with selector "${selector}" not found in the DOM.`,
				);
			}
		}, code1A_selector);

		await robustClick(page.getByLabel("Save changes"));

		await expect(page.getByText(/DQ History \(Pending: 1\)/)).toBeVisible();

		// Open DQ History
		const historyBtn = page.getByText(/DQ History \(Pending: 1\)/);
		await robustClick(historyBtn);

		// Verify modal content
		await expect(page.getByText("DQ History (Total: 1)")).toBeVisible();
		await expect(page.getByText(/CLEAR PENDING/i)).toBeVisible();

		// Clear Pending
		await robustClick(page.getByText(/CLEAR PENDING/i));

		// Verification
		await expect(page.getByText("No DQs recorded")).toBeVisible();

		// Close modal
		await page.keyboard.press("Escape");

		const closeBtn = page.getByTestId("modal-close-button");
		if (await closeBtn.isVisible()) {
			await robustClick(closeBtn);
		}

		// Queue count should be 0
		await expect(page.getByText(/DQ History \(Pending: 0\)/)).toBeVisible();
	});

	test("should support offline-first DQ entry with network recovery", async ({
		page,
		context,
	}) => {
		await page.goto("/", { waitUntil: "networkidle" });
		await expect(page.getByPlaceholder("Your Name")).toBeVisible({
			timeout: 30000,
		});

		// 0. Handle Judge Name Prompt
		const nameInput = page.getByPlaceholder("Your Name");
		await nameInput.fill("Offline Judge");
		await robustClick(page.getByText("START JUDGING"));

		// 1. Go Offline
		console.log("[Test] Going OFFLINE...");
		await context.setOffline(true);

		// 2. Add DQ while offline
		await robustClick(page.getByText(/#1 |Event 1/i).first());
		await robustClick(page.getByText(/Heat 1/i).first());
		await robustClick(page.getByText("TAP TO DQ").first());

		const code1A_selector = "[data-testid='dq-code-1A']";
		await page.waitForSelector(code1A_selector, {
			state: "attached",
			timeout: 10000,
		});
		await page.evaluate((selector) => {
			const element = document.querySelector(selector) as HTMLElement;
			if (element) {
				element.scrollIntoView({ block: "center" });
				element.click();
			} else {
				throw new Error(
					`E2E Error: Element with selector "${selector}" not found in the DOM.`,
				);
			}
		}, code1A_selector);

		await robustClick(page.getByLabel("Save changes"));

		// 3. Verify it is pending locally
		await expect(page.getByText(/DQ History \(Pending: 1\)/)).toBeVisible();

		// 4. Go Online
		console.log("[Test] Going ONLINE...");
		await context.setOffline(false);

		// 5. Trigger Sync and verify
		console.log("[Test] Opening DQ History...");
		const historyTrigger = page.getByText(/DQ History \(Pending: 1\)/);
		await robustClick(historyTrigger);

		console.log("[Test] Waiting for SYNC NOW button...");
		const syncBtn = page.getByRole("button", { name: /SYNC NOW/i });

		console.log("[Test] Clicking SYNC NOW...");
		await robustClick(syncBtn, { timeout: 30000 });

		await expect(page.getByText(/Successfully synced/i)).toBeVisible({
			timeout: 45000,
		});
		await expect(page.getByText(/DQ History \(Pending: 0\)/)).toBeVisible();
	});
});
