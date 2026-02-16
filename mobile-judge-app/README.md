# Mobile Judge App

An offline-first React Native (Expo) application for stroke and turn judges to record DQs during a meet.

## Demo

A live web-based demo is automatically deployed to:
[https://pfisherogden.github.io/MeetManager-Tools/](https://pfisherogden.github.io/MeetManager-Tools/)

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
