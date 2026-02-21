# Mobile Judge App

An offline-first React Native (Expo) application for stroke and turn judges to record DQs during a meet.

## Demo

A live web-based demo is automatically deployed to:
[https://pfisherogden.github.io/MeetManager-Tools/](https://pfisherogden.github.io/MeetManager-Tools/)

## Features
- **Offline First**: Works without internet connection. Stores data locally (SQLite on native, memory on web).
- **URL Configuration**: Initialize with meet data via URL parameters.
- **Sync**: Automatically syncs pending DQs when online if a sync URL is provided.

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

## Deployment Workflow

The app is automatically built and deployed to GitHub Pages via GitHub Actions.

### Automated Deployment
- **Trigger**: Any push to the `main` branch that includes changes in the `mobile-judge-app/` directory.
- **Workflow**: `.github/workflows/deploy-mobile.yml`
- **Steps**:
  1. Sets up Node.js (v18).
  2. Installs dependencies using `npm ci --legacy-peer-deps`.
  3. Builds the web bundle using `npx expo export --platform web`.
  4. Deploys the `dist/` directory to the `gh-pages` branch.

### Manual Deployment (Emergency/Testing)
If you need to deploy manually from your local machine:
1. Ensure you have the build tools installed: `cd mobile-judge-app && npm install`.
2. Generate the build: `npm run build-web`.
3. Use `git subtree` to push the `dist` folder to the `gh-pages` branch:
   ```bash
   git subtree push --prefix mobile-judge-app/dist origin gh-pages
   ```

## Local Development

1. **Install dependencies**:
   ```bash
   cd mobile-judge-app
   npm install
   ```

2. **Start the web version**:
   ```bash
   npm run web
   ```

3. **Run tests**:
   ```bash
   npm test
   ```
