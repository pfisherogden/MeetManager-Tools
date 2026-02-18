# Mobile Judge App User Journeys

This document outlines the core user journeys for the Mobile Judge App. These flows should be verified manually or via automated tests before every release.

## 1. Add DQ (Individual)
**Goal**: Verify a judge can successfully disqualify a swimmer in an individual event.

1.  Open the app and ensure you are on the "Events" view.
2.  Tap an individual event (e.g., Event 1).
3.  Tap a heat (e.g., Heat 1).
4.  Tap "TAP TO DQ" for a swimmer (e.g., Lane 4).
5.  **Verification**: The DQ Modal opens.
6.  Select a DQ code (e.g., "1A").
7.  Add a note (optional).
8.  Tap the "Save" icon (Floppy disk).
9.  **Verification**: The modal closes, and the swimmer row now displays the DQ code (e.g., "1A") in red.
10. **Verification**: The "Offline Queue" count in the header increments by 1.

## 2. Edit DQ
**Goal**: Verify a judge can modify an existing pending DQ.

1.  *Prerequisite*: Perform "Add DQ" flow.
2.  Tap "Offline Queue: X" in the header OR tap the swimmer row with the existing DQ.
3.  **Verification**: The DQ Selection Modal opens, pre-populated with:
    *   The correct Swimmer/Event details.
    *   The previously selected code (e.g., "1A").
    *   Any existing notes.
4.  Select an additional code (e.g., "1B") or deselect the existing one.
5.  Modify the note.
6.  Tap "Save".
7.  **Verification**: The modal closes. The swimmer row updates to show the new codes (e.g., "1A, 1B").
8.  **Verification**: The Offline Queue count remains the same (it updates the existing record).

## 3. Delete DQ (Individual)
**Goal**: Verify a judge can remove a pending DQ from the queue.

1.  *Prerequisite*: Perform "Add DQ" flow.
2.  Tap "Offline Queue: X" in the header to open the Queue Modal.
3.  Locate the pending DQ in the list.
4.  Tap the **Trash Icon** next to the entry.
5.  **Verification**: The entry is immediately removed from the list.
6.  **Verification**: The "Offline Queue" count decrements by 1.
7.  Close the modal.
8.  **Verification**: The swimmer row in the Event/Heat view reverts to "TAP TO DQ".

## 4. Clear All DQs
**Goal**: Verify a judge can reset the entire offline queue.

1.  *Prerequisite*: Add multiple DQs (e.g., 2-3 different swimmers).
2.  Tap "Offline Queue: X" in the header.
3.  Tap the **"CLEAR ALL"** button in the top-right of the modal.
4.  **Verification**: All entries are removed from the list.
5.  **Verification**: The "Offline Queue" count becomes 0.
6.  Close the modal.
7.  **Verification**: All affected swimmer rows revert to "TAP TO DQ".

## 5. Relay DQ (Specific Leg)
**Goal**: Verify a judge can DQ a specific swimmer in a relay team.

1.  Tap a Relay event (e.g., Event 5 'Mixed 200 Medley Relay').
2.  Tap a heat.
3.  Tap a specific leg row (e.g., "Leg 2 (Breast)").
4.  **Verification**: The DQ Modal opens with "Leg 2" selected.
5.  Select a stroke-appropriate code (e.g., "3A" for Breaststroke).
6.  Tap "Save".
7.  **Verification**: The modal closes. The specific leg row shows the DQ code.
8.  **Verification**: The team header row also indicates a DQ status (or remains neutral depending on specific UI requirements, but the leg must be marked).

## 6. Program View Navigation
**Goal**: Verify the "Program View" (continuous scroll) works as expected.

1.  Toggle the view switch from "Events" to "Program".
2.  **Verification**: Converting to a single continuous list of events.
3.  Scroll down to a specific event.
4.  Tap a swimmer or relay leg to add a DQ.
5.  **Verification**: The DQ flow works identically to the "Events" view.
6.  Save the DQ.
7.  **Verification**: The view does not reset to the top; it maintains scroll position (mostly) or allows easy return.
8.  Use the "Down Arrow" icon in the header.
9.  **Verification**: The view jumps to the next event header.

## 7. Offline Persistence (Simulated)
**Goal**: Verify DQs are stored even if the app is reloaded (if persistence is implemented).
*Note: This depends on the specific persistence implementation (e.g., local storage/AsyncStorage).*

1.  Add a DQ.
2.  Reload the page/app.
3.  **Verification**: The Offline Queue count is preserved.
4.  **Verification**: The pending DQ is still visible in the queue.
