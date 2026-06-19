/**
 * @OnlyCurrentDoc
 */

/**
 * Creates the custom menu when the spreadsheet opens.
 */
function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu('Swim Tools')
    .addItem('Check Permissions', 'checkPermissions')
    .addItem('Force Sync All Tabs', 'manualSyncAllTabsToMain')
    .addItem('Auto-Resize All Columns', 'autoResizeAllSheets')
    .addToUi();
}

/**
 * Displays a toast notification to confirm authorization.
 */
function checkPermissions() {
  SpreadsheetApp.getActiveSpreadsheet().toast('Permissions are authorized and active!', 'Authorization Check', 5);
}

/**
 * Triggers on every edit. Synchronizes checkbox changes between the Main tab
 * and Age Group tabs using the unique athlete ID in Column 14.
 * 
 * @param {Object} e The edit event object.
 */
function onEdit(e) {
  var range = e.range;
  var sheet = range.getSheet();
  var sheetName = sheet.getName();
  var column = range.getColumn();
  var row = range.getRow();
  
  // Only sync 'Present' (Col 5) and 'Scratch' (Col 6)
  if (column !== 5 && column !== 6) return;
  if (row < 2) return; // Ignore header

  // Ignore formula-driven tabs
  if (sheetName === 'All Scratches' || sheetName === 'Not Checked In' || sheetName === 'QR Code') return;

  var ss = SpreadsheetApp.getActiveSpreadsheet();
  
  // Get unique ID (Col 14 - ID)
  var athleteId = sheet.getRange(row, 14).getValue();
  if (!athleteId) return;

  // Fallback to range.getValue() if e.value is undefined (common when rapidly unchecking or mobile sync issues)
  var value = (e.value === undefined) ? range.getValue() : e.value;

  var sheetsToUpdate = [];
  var allSheets = ss.getSheets();
  for (var i = 0; i < allSheets.length; i++) {
    var name = allSheets[i].getName();
    if (name !== sheetName && name !== 'All Scratches' && name !== 'Not Checked In' && name !== 'QR Code') {
      sheetsToUpdate.push(allSheets[i]);
    }
  }

  sheetsToUpdate.forEach(function(targetSheet) {
    updateRowById(targetSheet, athleteId, column, value);
  });
}

/**
 * Updates a checkbox value in a target sheet by searching for the athlete ID.
 * 
 * @param {GoogleAppsScript.Spreadsheet.Sheet} sheet The sheet to update.
 * @param {number|string} id The unique athlete ID to search for.
 * @param {number} col The column index to update (5 or 6).
 * @param {string|boolean} val The value to set (TRUE/FALSE).
 */
function updateRowById(sheet, id, col, val) {
  if (!sheet) return;
  var lastRow = sheet.getLastRow();
  if (lastRow < 2) return;
  
  // Note: getValues() returns a 2D array, so data[i][0] corresponds to Column 14.
  // We use strict matching where possible, but ID types might vary (number vs string).
  var data = sheet.getRange(2, 14, lastRow - 1, 1).getValues();
  for (var i = 0; i < data.length; i++) {
    if (String(data[i][0]) === String(id)) {
      sheet.getRange(i + 2, col).setValue(val);
      return;
    }
  }
}

/**
 * Manually triggered sync function to reconcile any missed updates.
 * Pushes any changes from Age Group tabs back to the Main tab.
 */
function manualSyncAllTabsToMain() {
  SpreadsheetApp.getActiveSpreadsheet().toast('Starting full synchronization...', 'Sync', 5);
  syncAllTabsToMain();
  SpreadsheetApp.getActiveSpreadsheet().toast('Synchronization complete!', 'Sync', 5);
}

/**
 * Fallback periodic sync. Sweeps through all Age Group tabs.
 * If an Age Group tab has a Present/Scratch value that the Main tab doesn't have,
 * or if they conflict, it attempts to align them by treating the Age Group tab as the
 * latest source of truth for its specific swimmers.
 */
function syncAllTabsToMain() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var mainSheet = ss.getSheetByName('Main');
  if (!mainSheet) return;

  var lastRow = mainSheet.getLastRow();
  if (lastRow < 2) return;

  // Fetch Main data: we need Present (Col 5), Scratch (Col 6), and ID (Col 14)
  // Range: row 2, col 5, spanning 10 columns (cols 5 to 14)
  var mainRange = mainSheet.getRange(2, 5, lastRow - 1, 10);
  var mainData = mainRange.getValues();
  
  // Build a map of ID -> {present: val, scratch: val, rowIdx: index_in_mainData}
  var mainMap = {};
  for (var i = 0; i < mainData.length; i++) {
    var id = String(mainData[i][9]); // Col 14 is index 9 if we start at 5
    if (id) {
      mainMap[id] = {
        present: mainData[i][0] === true || mainData[i][0] === 'TRUE',
        scratch: mainData[i][1] === true || mainData[i][1] === 'TRUE',
        rowIdx: i
      };
    }
  }

  var allSheets = ss.getSheets();
  var changesMade = false;

  for (var s = 0; s < allSheets.length; s++) {
    var sheet = allSheets[s];
    var name = sheet.getName();
    
    // Skip non-age-group tabs
    if (name === 'Main' || name === 'All Scratches' || name === 'Not Checked In' || name === 'QR Code') {
      continue;
    }

    var sheetLastRow = sheet.getLastRow();
    if (sheetLastRow < 2) continue;

    var sheetData = sheet.getRange(2, 5, sheetLastRow - 1, 10).getValues();
    var sheetUpdates = [];

    for (var i = 0; i < sheetData.length; i++) {
      var id = String(sheetData[i][9]);
      if (!id || !mainMap[id]) continue;

      var sPresent = sheetData[i][0] === true || sheetData[i][0] === 'TRUE';
      var sScratch = sheetData[i][1] === true || sheetData[i][1] === 'TRUE';
      
      var mPresent = mainMap[id].present;
      var mScratch = mainMap[id].scratch;

      // If Age Group has a checked value but Main does not, push Age Group to Main
      if ((sPresent && !mPresent) || (sScratch && !mScratch)) {
        if (sPresent && !mPresent) {
          mainData[mainMap[id].rowIdx][0] = true;
          mainMap[id].present = true;
        }
        if (sScratch && !mScratch) {
          mainData[mainMap[id].rowIdx][1] = true;
          mainMap[id].scratch = true;
        }
        changesMade = true;
      } 
      // If Main has a checked value but Age Group does not, push Main to Age Group
      else if ((mPresent && !sPresent) || (mScratch && !sScratch)) {
        sheetUpdates.push({row: i + 2, present: mPresent, scratch: mScratch});
      }
    }

    // Apply any updates needed back to this specific Age Group sheet
    if (sheetUpdates.length > 0) {
      for (var u = 0; u < sheetUpdates.length; u++) {
        sheet.getRange(sheetUpdates[u].row, 5).setValue(sheetUpdates[u].present);
        sheet.getRange(sheetUpdates[u].row, 6).setValue(sheetUpdates[u].scratch);
      }
    }
  }

  // Apply any accumulated updates back to Main
  if (changesMade) {
    // We only need to write back cols 5 and 6
    var mainWriteBack = [];
    for (var i = 0; i < mainData.length; i++) {
      mainWriteBack.push([mainData[i][0], mainData[i][1]]);
    }
    mainSheet.getRange(2, 5, mainWriteBack.length, 2).setValues(mainWriteBack);
  }
  
  // Auto-resize columns to fit populated data
  autoResizeAllSheets();
}

/**
 * Auto-resizes columns 1 to 13 across all sheets (except QR Code) to fit content.
 */
function autoResizeAllSheets() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheets = ss.getSheets();
  sheets.forEach(function(sheet) {
    var name = sheet.getName();
    if (name !== 'QR Code') {
      var lastRow = sheet.getLastRow();
      if (lastRow > 0) {
        sheet.autoResizeColumns(1, 13);
        // Add padding to auto-resized columns so they don't look cramped
        for (var col = 1; col <= 13; col++) {
          var currentWidth = sheet.getColumnWidth(col);
          sheet.setColumnWidth(col, currentWidth + 15);
        }
      }
    }
  });
}
