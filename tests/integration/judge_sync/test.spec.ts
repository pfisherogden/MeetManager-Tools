import { test, expect } from '@playwright/test';

test('judge app syncs DQ to mock server', async ({ page }) => {
  // The judge-app is served at http://judge-app:8080
  // The mock-server is at http://mock-server:8081
  const syncUrl = 'http://mock-server:8081/sync';
  const appUrl = `http://judge-app:8080/?sync_url=${encodeURIComponent(syncUrl)}`;

  console.log(`Opening app at ${appUrl}`);
  await page.goto(appUrl);

  // Wait for loading to finish
  await expect(page.getByText('Events')).toBeVisible({ timeout: 10000 });

  // Select an event
  await page.getByText('Girls 8&U 100 Medley Relay').click();

  // Select a heat
  await page.getByText('Heat 1').click();

  // Tap to DQ a swimmer
  await page.getByText('Alice Smith').click();

  // Select a DQ code (e.g., 1A)
  await page.getByText('1A').click();

  // The app should have triggered a sync.
  // We'll poll the mock server's /verify endpoint to check if it received the DQ.
  
  let received = false;
  for (let i = 0; i < 10; i++) {
    const response = await page.request.get('http://mock-server:8081/verify');
    const data = await response.json();
    console.log('Mock server data:', data);
    
    if (data.length > 0) {
      const dq = data[0][0]; // data is array of requests, each request is array of DQs
      if (dq.dq_code === '1A' && dq.swimmer_id === 1) {
        received = true;
        break;
      }
    }
    await new Promise(r => setTimeout(r, 1000));
  }

  expect(received).toBe(true);
});
