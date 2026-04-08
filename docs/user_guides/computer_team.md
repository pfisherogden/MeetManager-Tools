# Computer Team & Meet Director Guide

## 1. Introduction

Welcome to the MMTools platform! As a member of the Computer Team or a Meet Director, you are the backbone of the swim meet. You are responsible for configuring the meet, managing data imports from legacy systems (like Meet Manager), generating crucial reports, and ensuring that volunteers (like Stroke & Turn Judges) have access to the correct data.

This guide provides a comprehensive walkthrough of your core responsibilities and how to execute them within the MMTools Cloud Run environment.

---

## 2. Accessing the System & Authentication

MMTools is securely deployed to Google Cloud Run. Your data is strictly sandboxed to your account, meaning you can only see the meets you upload, and no other users can access your data.

### 2.1. Logging In
1. Navigate to the MMTools frontend URL provided by your administrator (e.g., `https://mmtools-frontend-[hash]-uw.a.run.app`).
2. You will be greeted by the **Login Page**.
3. Click the **"Sign in with Google"** button.
4. An OAuth popup will appear. Select your authorized Google account.
5. Upon successful authentication, you will be redirected to the main **Dashboard**.

*(Screenshot placeholder: The MMTools login screen featuring the "Sign in with Google" button and a blue wave logo.)*
`[Image: Login Screen]`

---

## 3. Data Ingestion: Uploading the `.mdb` File

MMTools relies on data exported from your primary meet management software. Currently, it supports Microsoft Access databases (`.mdb`).

### 3.1. Preparing the Data
Before using MMTools, you must export your meet data:
1. Open your legacy Meet Manager software.
2. Ensure all entries, teams, and events are finalized for the current session.
3. Export the database (usually via `File -> Backup` or a direct `.mdb` export).
4. Save the file to an accessible location on your local computer.

### 3.2. Uploading to MMTools
1. On the left navigation sidebar, click on **Admin**.
2. Locate the **Dataset Manager** section.
3. Click the **Upload** area or drag and drop your `.mdb` file into the designated zone.
4. A progress bar will appear. Behind the scenes, MMTools is securely uploading the file to your isolated Google Cloud Storage (GCS) bucket and initiating the parsing process.
5. Once complete, a success toast notification will appear.

*(Screenshot placeholder: The Admin page showing the drag-and-drop file upload area and a success notification toast.)*
`[Image: Dataset Upload Interface]`

### 3.3. Activating the Dataset
You may have multiple datasets uploaded (e.g., Friday Prelims, Saturday Finals).
1. In the **Dataset Manager**, locate your newly uploaded file in the list.
2. If it is not already active, click the **Set Active** button next to the file name.
3. The system will refresh the cache, and all other pages (Dashboard, Reports, Meets) will now reflect the data from this specific file.

---

## 4. Verifying Meet Data

After activating a dataset, it is crucial to verify that the data parsed correctly.

### 4.1. Using the Dashboard
1. Click **Dashboard** in the sidebar.
2. Review the high-level statistics:
    - **Total Meets**: Should generally be `1`.
    - **Total Teams**: Verify the number of attending clubs.
    - **Total Athletes**: Ensure this matches your expected registration count.
    - **Total Events**: Confirm all events are loaded.

*(Screenshot placeholder: The Dashboard view showing metric cards for Meets, Teams, Athletes, and Events.)*
`[Image: Dashboard Statistics]`

### 4.2. Detailed Verification
If you need to investigate specific anomalies:
- Navigate to **Teams** to see a breakdown of athletes per club.
- Navigate to **Athletes** to search for a specific swimmer and verify their entries.
- Navigate to **Events** to see entry counts per event and heat breakdowns.

---

## 5. Generating Reports

One of the primary functions of MMTools is generating high-quality, readable PDF reports for various stakeholders.

### 5.1. The Reports Manager
1. Click **Reports** in the sidebar.
2. You will see several pre-configured **Bundles** (e.g., "Default Meet Pack") and individual report options.

### 5.2. Pre-Meet Document Generation
To generate the standard packet of documents needed before the meet begins:
1. Locate the **"Default Meet Pack"** card.
2. Click **Generate Bundle**.
3. The system will communicate with the backend via gRPC to compile a zip file containing:
    - **Meet Programs (2-Column)**: For coaches and spectators.
    - **Meet Programs (1-Column)**: For the computer table.
    - **Lane Timer Sheets**: Specially formatted sheets for volunteers behind the blocks, featuring 10 entries per page and designated lines for two automated button times and one stopwatch time.
    - **Stroke & Turn Judge Reports**: Specialized 1-column programs that include blank lines beneath each swimmer's name for recording Disqualification (DQ) codes.
    - **Parent Lineups**: Organized by age group and gender to help staging area volunteers.
4. Once generation is complete, your browser will prompt you to download a `.zip` file containing all PDFs.

*(Screenshot placeholder: The Reports Manager page highlighting the "Default Meet Pack" button and individual report generation options.)*
`[Image: Reports Generation Interface]`

---

## 6. Empowering the Stroke & Turn Judges

MMTools includes a specialized, offline-capable mobile application for Stroke & Turn (S&T) Judges. As the Computer Team, you are responsible for initializing their devices.

### 6.1. Publishing Data
The mobile app needs a lightweight version of the meet program to function offline.
1. Navigate to the **Admin** page.
2. In the Dataset Manager, ensure the correct dataset is active.
3. Click the **Publish to Judge App** button.
4. The system will compile the current events, heats, and swimmers into a highly optimized JSON payload and upload it to a public-facing (but unguessable) URL on your Cloud Storage bucket.

### 6.2. Onboarding Judges
1. Once publishing is complete, a **QR Code Dialog** will appear on your screen.
2. Instruct your S&T Judges to open their smartphone cameras and scan the QR code.
3. The QR code contains a deep link that will open the Mobile Judge App in their mobile browser, automatically downloading the specific program data and configuring the `sync_url` to point back to your backend.
4. *Crucial*: Instruct them to "Add to Home Screen" to install it as a Progressive Web App (PWA), ensuring it works reliably even if the pool deck Wi-Fi drops.

*(Screenshot placeholder: A modal dialog displaying a large QR code with instructions to "Scan to load Meet Program".)*
`[Image: Judge App QR Code]*`

---

## 7. Managing Disqualifications (DQs)

During the meet, Judges will record DQs on their phones.

### 7.1. The Sync Process
1. Judges operate offline. When they have a network connection (e.g., returning to the admin table), they press **Sync** on their mobile app.
2. The DQs are securely transmitted to the MMTools backend via the `/api/sync-dqs` endpoint.

### 7.2. Processing DQs (Future Workflow)
*Note: The automatic integration of synced DQs back into the source `.mdb` file is currently under development.*
Presently, you can verify synced DQs by reviewing the `synced_dqs.json` file in your cloud storage bucket, which can be manually cross-referenced or imported into the primary Meet Manager terminal.

---

## 8. Troubleshooting & Best Practices

- **Browser Caching**: If you upload a new database but the Dashboard numbers do not change, try performing a hard refresh (Ctrl+F5 or Cmd+Shift+R).
- **Session Expiration**: For security, your Google Login session may expire. If you receive "Unauthorized" or 403 errors, return to `/login` to refresh your token.
- **Large Files**: `.mdb` files over 50MB may take a moment to upload and parse. Do not close the browser tab while the upload progress bar is active.

By following this guide, you can ensure a smooth, paper-efficient, and technologically advanced swim meet!
