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

### 2. Event Entry Counts (Warnings)
- For every event in the meet, calculate the number of entries.
- If an event has 0 entries, generate a warning.
- **Crucial**: Ensure relay entries are counted from the `relay` table rather than the `entry` table, as relay events do not have rows in the `entry` table.

### 3. Points Awarded with DQs
- A swimmer/relay with status `"Q"` (DQ) or a place of `0` must **not** receive points.
- If points (`score` > 0) are found on a DQ entry, it indicates the event was not rescored after the DQ was entered.

### 4. No Show (NS) / Missing Times
- Generates informational logs of scheduled swims that have no time and no status (or `"NS"` status), indicating possible stopwatch or manual entry failures.
