# Mobile Judge App

A cross-platform React Native / Expo application for Stroke & Turn judges to record DQs.

## Features
- **Offline First**: Works without internet connection. Stores data locally (SQLite on native, memory on web).
- **URL Configuration**: Initialize with meet data via URL parameters.
- **Sync**: Automatically syncs pending DQs when online if a sync URL is provided.

## Getting Started

### Prerequisites
- Node.js
- Expo CLI (`npm install -g expo-cli`)

### Installation
```bash
npm install
```

### Running locally
```bash
npm start
```

## URL Parameters

The app can be initialized with data by appending query parameters to the URL (Web) or Deep Link (Native).

- `program_url`: URL to a JSON file containing the meet program (events, heats, swimmers).
- `dq_url`: URL to a JSON file containing DQ codes configuration.
- `sync_url`: URL to push pending DQs to (e.g., a backend endpoint or a cloud storage signed URL).

### Example JSON Format

**Program Data (`program_url`):**
```json
{
  "events": [
    { "id": 1, "number": 1, "name": "Event 1", "distance": 100, "stroke": "Medley" }
  ],
  "heats": [
    { "id": 1, "event_id": 1, "number": 1 }
  ],
  "swimmers": [
    { "id": 1, "heat_id": 1, "lane": 1, "name": "Alice", "team": "FAST" }
  ]
}
```

**DQ Codes (`dq_url`):**
```json
{
  "butterfly": [
    { "code": "1A", "description": "Alternating Kick" }
  ]
}
```

## Syncing

If `sync_url` is provided, the app will attempt to push pending DQs when internet connection is available.
- If URL looks like cloud storage (Google/AWS), it uses `PUT`.
- Otherwise, it uses `POST`.
- Body is a JSON array of DQ objects.
