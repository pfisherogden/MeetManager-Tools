// DataReceiver.js - Google Apps Script
// Deployed as a Web App (Run as: Me, Access: Anyone)

const SHEET_NAME = "Scoreboard";
const CACHE_KEY = "scoreboard_state";
const CACHE_TTL_SEC = 1800; // 30 minutes cache life

/**
 * Helper to get the active scoreboard sheet.
 */
function getScoreboardSheet() {
	const ss = SpreadsheetApp.getActiveSpreadsheet();
	let sheet = ss.getSheetByName(SHEET_NAME);
	if (!sheet) {
		// Auto-create sheet if it doesn't exist
		sheet = ss.insertSheet(SHEET_NAME);
		sheet
			.getRange("A1:C1")
			.setValues([["Event", "Heat", "Last_Write_Timestamp"]]);
		sheet.getRange("A2:C2").setValues([[1, 1, Date.now()]]);
	}
	return sheet;
}

/**
 * Reads state from sheet and updates the cache.
 */
function getAndCacheState(sheet) {
	const values = sheet.getRange("A2:C2").getValues()[0];
	const state = {
		event: Number(values[0]) || 1,
		heat: Number(values[1]) || 1,
		timestamp: Number(values[2]) || Date.now(),
	};

	const cache = CacheService.getScriptCache();
	cache.put(CACHE_KEY, JSON.stringify(state), CACHE_TTL_SEC);
	return state;
}

/**
 * Handle GET request: read state.
 */
function _doGet(_e) {
	const cache = CacheService.getScriptCache();
	const cachedVal = cache.get(CACHE_KEY);

	let state;
	if (cachedVal) {
		try {
			state = JSON.parse(cachedVal);
		} catch (_err) {
			// If parsing fails, fall back to sheet
			const sheet = getScoreboardSheet();
			state = getAndCacheState(sheet);
		}
	} else {
		// Cache miss - read from sheet
		const sheet = getScoreboardSheet();
		state = getAndCacheState(sheet);
	}

	return ContentService.createTextOutput(JSON.stringify(state)).setMimeType(
		ContentService.MimeType.JSON,
	);
}

/**
 * Handle POST request: write state.
 */
function _doPost(e) {
	const lock = LockService.getScriptLock();
	try {
		// Acquire lock for up to 5 seconds to prevent concurrent write collisions
		if (!lock.tryLock(5000)) {
			return ContentService.createTextOutput(
				JSON.stringify({
					success: false,
					error: "Lock timeout: Another write operation is in progress.",
				}),
			).setMimeType(ContentService.MimeType.JSON);
		}

		// Parse request body
		if (!e.postData?.contents) {
			return ContentService.createTextOutput(
				JSON.stringify({
					success: false,
					error: "Missing request body",
				}),
			).setMimeType(ContentService.MimeType.JSON);
		}

		const requestData = JSON.parse(e.postData.contents);
		const newEvent = Number(requestData.event);
		const newHeat = Number(requestData.heat);
		const clientTimestamp = Number(requestData.timestamp) || Date.now();
		const expectedTimestamp = Number(requestData.expectedTimestamp) || 0;

		if (Number.isNaN(newEvent) || Number.isNaN(newHeat)) {
			return ContentService.createTextOutput(
				JSON.stringify({
					success: false,
					error: "Event and Heat must be valid numbers",
				}),
			).setMimeType(ContentService.MimeType.JSON);
		}

		const sheet = getScoreboardSheet();

		// Concurrency Check: Read current state to see if updated elsewhere
		const cache = CacheService.getScriptCache();
		let currentState;
		const cachedVal = cache.get(CACHE_KEY);
		if (cachedVal) {
			try {
				currentState = JSON.parse(cachedVal);
			} catch (_err) {
				currentState = getAndCacheState(sheet);
			}
		} else {
			currentState = getAndCacheState(sheet);
		}

		// If sheet state is newer than what client expected (and client passed an expectation), conflict!
		if (expectedTimestamp > 0 && currentState.timestamp > expectedTimestamp) {
			return ContentService.createTextOutput(
				JSON.stringify({
					success: false,
					error: "Conflict",
					code: 409,
					currentState: currentState,
				}),
			).setMimeType(ContentService.MimeType.JSON);
		}

		// Write new state to the sheet
		sheet.getRange("A2:C2").setValues([[newEvent, newHeat, clientTimestamp]]);

		// Update cache immediately to keep reads fast and consistent
		const updatedState = {
			event: newEvent,
			heat: newHeat,
			timestamp: clientTimestamp,
		};
		cache.put(CACHE_KEY, JSON.stringify(updatedState), CACHE_TTL_SEC);

		return ContentService.createTextOutput(
			JSON.stringify({
				success: true,
				state: updatedState,
			}),
		).setMimeType(ContentService.MimeType.JSON);
	} catch (err) {
		return ContentService.createTextOutput(
			JSON.stringify({
				success: false,
				error: err.toString(),
			}),
		).setMimeType(ContentService.MimeType.JSON);
	} finally {
		lock.releaseLock();
	}
}

/**
 * Handle manual edits on the spreadsheet directly.
 * Clears or updates the cache when range A2:B2 is changed manually.
 */
function _onEdit(e) {
	if (!e?.range) return;
	const range = e.range;
	const sheet = range.getSheet();

	if (sheet.getName() === SHEET_NAME) {
		const row = range.getRow();
		const col = range.getColumn();

		// Trigger if edit happens in A2 or B2
		if (row === 2 && (col === 1 || col === 2)) {
			getAndCacheState(sheet);
		}
	}
}
