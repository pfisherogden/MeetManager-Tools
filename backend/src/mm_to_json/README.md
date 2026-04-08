# Meet Manager MDB Schema Notes

This document captures discovered patterns and column names for the underlying Microsoft Access (`.mdb`) database used by Meet Manager.

## Key Tables & Columns

### Event Table (`Event` or `MTEVENT`)
- **`Event_ptr`**: Primary Key (Long).
- **`Event_no`**: Human-readable event number (Integer).
- **`Ind_rel`**: Indicator for Individual ('I') vs Relay ('R') events.
- **`Event_sex`**: Gender of the event.
- **`Event_stroke`**: Stroke code.

### Entry Table (`Entry` or `ENTRY`)
- **`Event_ptr`**: Foreign Key to Event (Long).
- **`Ath_no`**: Foreign Key to Athlete (Long).
- **`Pre_heat`, `Pre_lane`**: Heat and Lane for Prelims.
- **`Pre_stat`**: Status for Prelims (e.g., 'DQ' for Disqualified, 'SCR' for Scratched).
- **`Pre_dqcode`**: Disqualification code for Prelims.
- **`Fin_heat`, `Fin_lane`, `Fin_stat`, `Fin_dqcode`**: Corresponding columns for Finals.

### Relay Table (`Relay` or `RELAY`)
- **`Event_ptr`**: Foreign Key to Event (Long).
- **`Relay_no`**: Primary Key for the relay entry (Long).
- **`Pre_stat`, `Pre_dqcode`**: Status and DQ code for Prelims.
- **`Fin_stat`, `Fin_dqcode`**: Status and DQ code for Finals.

## Synchronization Logic
When syncing DQ data from mobile apps:
1. Resolve the `Event_ptr` by matching the human-readable `event_id` against the `Event_no`.
2. Determine if the event is a relay using the `Ind_rel` column.
3. Update either the `ENTRY` (for individual) or `RELAY` (for relay) table using the athlete/relay ID and the resolved `Event_ptr`.
