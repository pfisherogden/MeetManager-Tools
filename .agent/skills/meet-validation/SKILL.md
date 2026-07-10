---
name: meet-validation
description: Guidelines and procedures for validating completed/scored swim meet MDB database files and running rule compliance checks in MeetManager-Tools.
---

# Meet Validation Skill

This skill contains instructions for validating MDB files for common database errors, administrative typos, and TVSL swim rules violations.

## Core Architecture

Validations are executed using:
1. **gRPC Interface**: `ValidateMeet` defined in the service protobuf contract.
2. **Logic File**: [meet_validation.py](file:///Users/pfo/Developer/MeetManager-Tools/backend/src/meet_validation.py), containing decoupled business rules logic.
3. **Tests**: [test_meet_validation.py](file:///Users/pfo/Developer/MeetManager-Tools/backend/tests/test_meet_validation.py).

## Rules and Validation Logic

When checking meet data, apply these TVSL Rules logic:

### 1. TVSL Entry Limits (Rule 12)
- **Individual Events**: Max 3 per athlete.
- **Total Events**: Max 4 per athlete (individual + relays).
- **Exhibition Exemption**: Swims marked as exhibition (`Pre_exh` or `Fin_exh` containing non-empty characters in `entry` or `relay` tables) do **not** count towards the athlete's entry limits.
- **Relay Event Entry**: Relay entries must be looked up in the `relay` table (linked to the athlete via the `relaynames` table). Relays are not present in the individual `entry` table.

### 2. Points Awarded with DQs
- A swimmer/relay with status `"Q"` (DQ) or a place of `0` must **not** receive points.
- If points (`score` > 0) are found on a DQ entry, it indicates the event was not rescored after the DQ was entered.

### 3. No Show (NS) / Missing Times
- Generates informational logs of scheduled swims that have no time and no status (or `"NS"` status), indicating possible stopwatch or manual entry failures.

### 4. Team Splashes Limit
- **Rule**: Validate that no team exceeds the league limit of 420 splashes in a meet.
- **Formula**: Total Splashes = (Count of non-scratched individual entries) + (4 * Count of non-scratched relay entries).
- **Scratches**: Excluded from splash counts (status `R`/`NS`, or `scr_stat == 1`).

