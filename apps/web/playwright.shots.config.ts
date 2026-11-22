import { defineConfig, devices } from '@playwright/test';

// Screenshots for design review (not run in CI): `npm run shots -w web` → apps/web/shots/.
export default defineConfig({
	webServer: {
		command: 'node scripts/sync-pack.mjs --fixture && vite build && vite preview',
		port: 4173
	},
	testMatch: '**/*.shots.ts',
	projects: ['dark', 'light'].map((scheme) => ({
		name: scheme,
		use: {
			...devices['Desktop Chrome'],
			viewport: { width: 375, height: 812 },
			hasTouch: true,
			colorScheme: scheme as 'dark' | 'light'
		}
	}))
});
