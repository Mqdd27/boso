<script lang="ts">
	import { resolve } from '$app/paths';
	import { page } from '$app/state';
	import CourseGate from '#lib/components/CourseGate.svelte';
	import Player from '#lib/components/Player.svelte';
	import { db } from '#lib/db.js';
	import { m } from '#lib/paraglide/messages.js';
	import { getLocale } from '#lib/paraglide/runtime.js';
	import { koreanVoice } from '#lib/audio.js';
	import { isScript, section } from '#lib/lesson.js';
	import type { Pack } from '#lib/types.js';

	const courseId = page.params.course ?? '';
	const unitId = page.params.unit ?? '';
	const lang = getLocale();

	const setup = Promise.all([
		db.unitProgress.toArray(),
		db.itemStats.toArray(),
		koreanVoice()
	]).then(([progress, stats, voice]) => ({
		progress: new Map(progress.filter((p) => p.course === courseId).map((p) => [p.unit, p])),
		stats: Object.fromEntries(stats.map((s) => [s.id, s])),
		voice
	}));
</script>

<CourseGate>
	{#snippet children(packs: Pack[])}
		{@const course = packs.find((p) => p.course.id === courseId)?.course}
		{@const index = course?.units.findIndex((u) => u.id === unitId) ?? -1}
		{#await setup then s}
			{#if course && index >= 0}
				{@const p = s.progress.get(unitId)}
				{@const units = section(course.units, isScript(course.units[index]))}
				{@const n = units.indexOf(course.units[index])}
				{@const prev = n === 0 || !!s.progress.get(units[n - 1].id)?.completedAt}
				{#if !prev}
					<p class="py-8">
						🔒 {m.unit_locked()} ·
						<a class="font-bold text-blue-ink underline underline-offset-4" href={resolve('/')}>
							{m.done_home()}
						</a>
					</p>
				{:else}
					<Player
						course={courseId}
						unit={course.units[index]}
						earlier={course.units.slice(0, index)}
						lesson={p?.lessons.includes(1) ? 2 : 1}
						practice={!!p?.completedAt}
						{lang}
						voice={s.voice}
						stats={s.stats}
						seed={Date.now()}
					/>
				{/if}
			{:else}
				<p class="py-8">
					404 · <a class="font-bold text-blue-ink underline underline-offset-4" href={resolve('/')}>
						{m.done_home()}
					</a>
				</p>
			{/if}
		{/await}
	{/snippet}
</CourseGate>
