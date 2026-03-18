import { expect, test } from "@playwright/test";

test.describe("UI/UX Bug Reproduction", () => {
	test("Bug 2: Filter Header Sticky overlap", async ({ page }) => {
		await page.goto("/entries");
		await expect(page.locator("table tbody tr").first()).toBeVisible();

		const _sidebar = page.locator("aside"); // shadcn sidebar is usually 'aside' or has data-sidebar
		const _thead = page.locator("thead");

		const zIndexes = await page.evaluate(() => {
			const getZIndex = (el: Element | null) => {
				if (!el) return "not found";
				return window.getComputedStyle(el).zIndex;
			};
			// Sidebar might be deep in the tree or have a specific class
			const sidebar = document.querySelector('[data-sidebar="sidebar"]');
			const thead = document.querySelector("thead");
			return {
				sidebar: getZIndex(sidebar),
				thead: getZIndex(thead),
			};
		});
		console.log("Z-Indexes:", zIndexes);

		// Scroll to the right
		await page.evaluate(() => {
			const scrollable = document.querySelector(".overflow-auto");
			if (scrollable) scrollable.scrollLeft = 500;
		});

		await page.screenshot({ path: "debug/bug2_sticky_header.png" });
	});

	test("Bug 3: Medals UX", async ({ page }) => {
		await page.goto("/entries");
		await expect(page.locator("table tbody tr").first()).toBeVisible();

		// Check for rank styling in first column or place column
		const ranks = page.locator("td").filter({ hasText: /^[123]$/ });
		const count = await ranks.count();
		console.log(`Found ${count} top-3 rank cells`);

		for (let i = 0; i < Math.min(count, 3); i++) {
			const html = await ranks.nth(i).innerHTML();
			console.log(`Rank HTML sample: ${html}`);
		}
	});

	test("Bug 4: Scores section Meet data", async ({ page }) => {
		await page.goto("/scores");
		await expect(page.locator("table tbody tr").first()).toBeVisible();

		const rows = page.locator("table tbody tr");
		const firstRowCells = await rows.first().locator("td").allInnerTexts();
		console.log("First row cells:", firstRowCells);

		// Mapping from ScoresManager columns:
		// 0: Rank, 1: Team, 2: Meet, 3: Individual, 4: Relay, 5: Total
		console.log(`Team: ${firstRowCells[1]}, Meet: ${firstRowCells[2]}`);

		if (!firstRowCells[2] || firstRowCells[2] === "Unknown Meet") {
			console.log("BUG REPRODUCED: Meet name is empty or Unknown Meet");
		}
	});

	test("Bug 7: Team Filter functionality", async ({ page }) => {
		await page.goto("/reports");
		const teamInput = page.locator("#team");
		await teamInput.fill("De");

		// Check for any popover or list
		const suggestions = page.locator(
			'[role="listbox"], [role="menu"], .popover',
		);
		const suggCount = await suggestions.count();
		console.log(`Found ${suggCount} suggestion elements after typing 'De'`);

		// Click filter icon
		await page
			.locator("button")
			.filter({ has: page.locator("svg.lucide-filter") })
			.click();
		// Check if anything happened
		await page.waitForTimeout(1000);
		await page.screenshot({ path: "debug/bug7_filter_click.png" });
	});
});
