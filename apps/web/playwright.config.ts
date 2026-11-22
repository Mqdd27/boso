import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
	// Production build + preview (no dev-only behaviour) with the fixture pack: no Python needed.
	webServer: {
		command: 'node scripts/sync-pack.mjs --fixture && vite build && vite preview',
		port: 4173
	},
	testMatch: '**/*.e2e.{ts,js}',
	projects: [
		{
			name: 'mobile',
			use: { ...devices['Desktop Chrome'], viewport: { width: 360, height: 800 }, hasTouch: true }
		},
		{
			name: 'desktop',
			use: { ...devices['Desktop Chrome'], viewport: { width: 1280, height: 800 } }
		}
	]
});
