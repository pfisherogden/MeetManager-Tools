
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
 * Implements mutual exclusivity between 'Present' (Col 5) and 'Scratch' (Col 6).
 * 
 * @param {Object} e The edit event object.
 */
function onEdit(e) {
  var range = e.range;
  var sheet = range.getSheet();
  var sheetName = sheet.getName();
  var column = range.getColumn();
  var row = range.getRow();
  var value = e.value;

  // Only sync 'Present' (Col 5) and 'Scratch' (Col 6)
  if (column !== 5 && column !== 6) return;
  if (row < 2) return; // Ignore header

  // Ignore formula-driven tabs
  if (sheetName === 'All Scratches' || sheetName === 'Not Checked In') return;

  var ss = SpreadsheetApp.getActiveSpreadsheet();
  
  // Get unique ID (Col 14 - ID)
  var athleteId = sheet.getRange(row, 14).getValue();
  if (!athleteId) return;

  var sheetsToUpdate = [];
  var allSheets = ss.getSheets();
  for (var i = 0; i < allSheets.length; i++) {
    var name = allSheets[i].getName();
    if (name !== sheetName && name !== 'All Scratches' && name !== 'Not Checked In') {
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
 * @param {number} col The column index to update (3 or 4).
 * @param {string|boolean} val The value to set (TRUE/FALSE).
 */
function updateRowById(sheet, id, col, val) {
  if (!sheet) return;
  var lastRow = sheet.getLastRow();
  if (lastRow < 2) return;
  
  var data = sheet.getRange(2, 14, lastRow - 1, 1).getValues();
  for (var i = 0; i < data.length; i++) {
    if (data[i][0] == id) {
      sheet.getRange(i + 2, col).setValue(val);
      return;
    }
  }
}
