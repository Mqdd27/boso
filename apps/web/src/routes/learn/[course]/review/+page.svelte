<script lang="ts">
	import { resolve } from '$app/paths';
	import { page } from '$app/state';
	import CourseGate from '#lib/components/CourseGate.svelte';
	import Player from '#lib/components/Player.svelte';
	import { db } from '#lib/db.js';
	import { m } from '#lib/paraglide/messages.js';
	import { getLocale } from '#lib/paraglide/runtime.js';
	import { voiceFor } from '#lib/audio.js';
	import { reviewPool, reviewUnit } from '#lib/srs.js';
	import type { Pack } from '#lib/types.js';

	const courseId = page.params.course ?? '';
	const lang = getLocale();

	const setup = Promise.all([
		db.cards
			.where('[course+due]')
			.between([courseId, 0], [courseId, Date.now()], true, true)
			.toArray(),
		db.itemStats.toArray(),
		voiceFor(courseId.split('-')[0]) // course IDs are <target>-<gloss>
	]).then(([due, stats, voice]) => ({
		due,
		stats: Object.fromEntries(stats.map((s) => [s.id, s])),
		voice
	}));
</script>

<CourseGate>
	{#snippet children(packs: Pack[])}
		{@const course = packs.find((p) => p.course.id === courseId)?.course}
		{#await setup then s}
			{@const unit = course && reviewUnit(course.units, s.due)}
			{#if course && unit}
				<Player
					course={courseId}
					{unit}
					earlier={reviewPool(course.units, unit)}
					lesson={2}
					practice
					review
					{lang}
					voice={s.voice}
					stats={s.stats}
					seed={Date.now()}
				/>
			{:else}
				<p class="py-8" data-testid="review-none">
					{m.review_none()} ·
					<a class="font-bold text-blue-ink underline underline-offset-4" href={resolve('/')}>
						{m.done_home()}
					</a>
				</p>
			{/if}
		{/await}
	{/snippet}
</CourseGate>
