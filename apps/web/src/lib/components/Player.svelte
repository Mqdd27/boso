<script lang="ts">
	import { resolve } from '$app/paths';
	import { goto } from '$app/navigation';
	import { db, recordLesson } from '#lib/db.js';
	import {
		generateLesson,
		isScript,
		label,
		lessonXp,
		requeue,
		type Exercise
	} from '#lib/lesson.js';
	import { m } from '#lib/paraglide/messages.js';
	import { settings, showRoman } from '#lib/settings.svelte.js';
	import { canListen, pickSource, play, SLOW } from '#lib/audio.js';
	import { dailyTotals, localDate, streak } from '#lib/stats.js';
	import { localized, type GlossLang, type Item, type Unit } from '#lib/types.js';
	import BuildSyllable from './BuildSyllable.svelte';
	import Badge from './Badge.svelte';
	import Confirm from './Confirm.svelte';
	import IntroCard from './IntroCard.svelte';
	import MatchPairs from './MatchPairs.svelte';

	let {
		course,
		unit,
		earlier,
		lesson,
		practice,
		lang,
		voice,
		stats,
		seed
	}: {
		course: string;
		unit: Unit;
		earlier: Unit[];
		lesson: 1 | 2;
		practice: boolean;
		lang: GlossLang;
		voice: SpeechSynthesisVoice | null;
		stats: Record<string, import('#lib/lesson.js').ItemStat>;
		seed: number;
	} = $props();

	// The lesson is generated once, when the player mounts.
	// svelte-ignore state_referenced_locally
	let queue: Exercise[] = $state(
		generateLesson({
			unit,
			earlier,
			stats,
			lesson,
			seed,
			lang,
			canListen: canListen([...unit.items, ...earlier.flatMap((u) => u.items)], voice)
		})
	);
	let index = $state(0);
	let selected = $state<number | null>(null);
	let built = $state<string | null>(null);
	let checked = $state(false);
	let matchMistakes = $state<Set<string> | null>(null);
	let confirmExit = $state(false);
	let done = $state<{ xp: number; accuracy: number; streak: number; perfect: boolean } | null>(
		null
	);

	let answers = 0;
	let rightAnswers = 0;
	let mistakes = 0;
	const results: { id: string; correct: boolean }[] = [];

	const ex = $derived(queue[index]);
	// Script units (Hangul) ask for sounds, so romanization is the answer there: always shown where
	// it is the answer, never where it would give the answer away.
	const script = $derived(isScript(unit));
	const roman = $derived(!script && showRoman(course));
	const sound = (item: Item) => label(item, lang, script);
	const correct = $derived(
		ex?.kind === 'build'
			? built === ex.item.text
			: !!ex && 'options' in ex && selected !== null && ex.options[selected].id === ex.item.id
	);
	const answered = $derived(ex?.kind === 'build' ? built !== null : selected !== null);

	function say(item: Item, rate = 1) {
		void play(item, course, voice, rate);
	}
	const audible = (item: Item) => pickSource(item, voice) !== 'none';

	$effect(() => {
		// Autoplay once per exercise (listening always: it has nothing else to show).
		if (ex?.kind === 'listen' || (ex?.kind === 'build' && ex.listen)) say(ex.item);
		else if (ex?.kind === 'intro' && settings.autoplay) say(ex.item);
	});

	function grade(ok: boolean, ids: string[]) {
		answers++;
		if (ok) rightAnswers++;
		else {
			mistakes++;
			queue = requeue(queue, index);
		}
		for (const id of ids) results.push({ id, correct: ok });
	}

	function check() {
		if (!ex || ex.kind === 'intro' || ex.kind === 'match' || !answered || checked) return;
		checked = true;
		grade(correct, [ex.item.id]);
	}

	function onMatchDone(wrong: Set<string>) {
		if (ex?.kind !== 'match') return;
		matchMistakes = wrong;
		answers++;
		if (wrong.size) {
			mistakes++;
			queue = requeue(queue, index);
		} else rightAnswers++;
		for (const item of ex.items) results.push({ id: item.id, correct: !wrong.has(item.id) });
	}

	async function next() {
		if (index + 1 < queue.length) {
			index++;
			selected = null;
			built = null;
			checked = false;
			matchMistakes = null;
			return;
		}
		const xp = lessonXp(mistakes);
		await recordLesson({ course, unit: unit.id, lesson, xp, results });
		const totals = dailyTotals(await db.activity.toArray());
		done = {
			xp,
			accuracy: Math.round((100 * rightAnswers) / Math.max(answers, 1)),
			streak: streak(totals, settings.dailyGoal, localDate(new Date())).current,
			perfect: mistakes === 0
		};
	}

	const canContinue = $derived(
		ex?.kind === 'intro' || (ex?.kind === 'match' ? matchMistakes !== null : checked)
	);

	function onkeydown(e: KeyboardEvent) {
		if (done || confirmExit || !ex) return;
		if (/^[1-4]$/.test(e.key) && 'options' in ex && !checked) {
			const n = Number(e.key) - 1;
			if (n < ex.options.length) selected = n;
		} else if (e.key === 'Enter') {
			e.preventDefault();
			if (canContinue) void next();
			else check();
		}
	}

	const optionClass = (n: number) => {
		if (!ex || !('options' in ex)) return '';
		const isAnswer = ex.options[n].id === ex.item.id;
		if (checked && isAnswer) return 'border-green-600 bg-green-50 dark:bg-green-950';
		if (checked && n === selected) return 'border-red-600 bg-red-50 dark:bg-red-950';
		if (n === selected) return 'border-sky-500 bg-sky-50 dark:bg-sky-950';
		return 'border-zinc-300 dark:border-zinc-700';
	};
	const title = $derived(
		practice
			? m.practice_title({ unit: localized(unit.title, lang) })
			: m.lesson_title({ unit: localized(unit.title, lang), lesson })
	);
</script>

<svelte:window {onkeydown} />

{#if done}
	<section class="flex flex-col items-center gap-3 py-10 text-center" data-testid="lesson-done">
		<h1 class="text-3xl font-bold">🎉 {m.done_title()}</h1>
		<p class="text-4xl font-bold text-amber-500">{m.done_xp({ xp: done.xp })}</p>
		{#if done.perfect}<p>{m.done_perfect()}</p>{/if}
		<p>{m.done_accuracy({ percent: done.accuracy })}</p>
		<p>🔥 {m.done_streak({ days: done.streak })}</p>
		<div class="mt-4 flex w-full flex-col gap-2">
			{#if lesson === 1 && !practice}
				<button
					type="button"
					class="min-h-12 rounded-xl bg-green-600 font-semibold text-white"
					onclick={() => location.reload()}
				>
					{m.done_next()}
				</button>
			{/if}
			<a
				href={resolve('/')}
				class="flex min-h-12 items-center justify-center rounded-xl border font-semibold"
				data-testid="back-home"
			>
				{m.done_home()}
			</a>
		</div>
	</section>
{:else if ex}
	<header class="flex items-center gap-3 py-3">
		<button
			type="button"
			class="min-h-11 min-w-11 rounded-xl border px-3"
			aria-label={m.exit()}
			onclick={() => (confirmExit = true)}
		>
			✕
		</button>
		<div
			class="h-3 flex-1 overflow-hidden rounded-full bg-zinc-200 dark:bg-zinc-800"
			role="progressbar"
			aria-label={m.progress_label()}
			aria-valuemin={0}
			aria-valuemax={queue.length}
			aria-valuenow={index}
		>
			<div
				class="h-full bg-green-500 transition-all"
				style:width="{(100 * index) / queue.length}%"
			></div>
		</div>
	</header>
	<p class="mb-2 text-sm opacity-70">{title}</p>

	<section
		class="flex flex-1 flex-col"
		data-testid="exercise"
		data-kind={ex.kind}
		data-step={index}
	>
		{#if ex.kind === 'intro'}
			<IntroCard
				item={ex.item}
				{lang}
				roman={roman || script}
				onlisten={audible(ex.item) ? (rate?: number) => say(ex.item, rate) : undefined}
			/>
		{:else if ex.kind === 'match'}
			<h2 class="mb-3 text-xl font-semibold">
				{script ? m.prompt_match_sound() : m.prompt_match()}
			</h2>
			{#key index}
				<MatchPairs items={ex.items} right={ex.right} label={sound} {roman} ondone={onMatchDone} />
			{/key}
		{:else}
			<h2 class="mb-3 text-xl font-semibold">
				{ex.kind === 'build'
					? m.prompt_build()
					: ex.kind === 'meaning'
						? script
							? m.prompt_sound()
							: m.prompt_meaning()
						: ex.kind === 'word'
							? script
								? m.prompt_letter()
								: m.prompt_word()
							: script
								? m.prompt_listen_letter()
								: m.prompt_listen()}
			</h2>
			<div class="mb-5 flex flex-col items-center gap-2 text-center" data-testid="prompt">
				{#if ex.kind === 'meaning'}
					<p class="text-5xl font-bold" lang="ko">{ex.item.text}</p>
					{#if roman}<p class="opacity-80" data-testid="roman">{ex.item.roman}</p>{/if}
				{:else if ex.kind === 'word' || (ex.kind === 'build' && !ex.listen)}
					<p class="text-3xl font-semibold" data-testid={script ? 'sound' : undefined}>
						{sound(ex.item)}
					</p>
				{:else}
					<button
						type="button"
						class="min-h-16 min-w-16 rounded-full bg-sky-500 text-3xl text-white"
						aria-label={m.play_again()}
						onclick={() => say(ex.item)}
					>
						🔊
					</button>
					<button
						type="button"
						class="min-h-11 min-w-11 rounded-full border text-xl"
						aria-label={m.listen_slow()}
						data-testid="listen-slow"
						onclick={() => say(ex.item, SLOW)}
					>
						🐢
					</button>
				{/if}
				<Badge item={ex.item} />
			</div>
			{#if ex.kind === 'build'}
				{#key index}
					<BuildSyllable tiles={ex.tiles} disabled={checked} bind:value={built} />
				{/key}
			{:else}
				<ol class="flex flex-col gap-2">
					{#each ex.options as option, n (option.id)}
						<li>
							<button
								type="button"
								class="flex min-h-12 w-full items-center gap-3 rounded-xl border-2 px-3 py-2 text-left {optionClass(
									n
								)}"
								disabled={checked}
								aria-pressed={n === selected}
								data-option={option.id}
								onclick={() => (selected = n)}
							>
								<kbd class="hidden rounded border px-1.5 text-xs opacity-60 sm:inline">{n + 1}</kbd>
								{#if ex.kind === 'meaning'}
									<span class={script ? 'text-lg font-semibold' : ''}>{sound(option)}</span>
								{:else}
									<span class="text-lg font-semibold" lang="ko">{option.text}</span>
									{#if roman}<span class="text-sm opacity-70" data-testid="roman">
											{option.roman}
										</span>{/if}
								{/if}
							</button>
						</li>
					{/each}
				</ol>
				<p class="mt-3 hidden text-xs opacity-60 sm:block">{m.keyboard_hint()}</p>
			{/if}
		{/if}
	</section>

	<footer class="sticky bottom-0 mt-4 bg-white pt-2 pb-4 dark:bg-zinc-950">
		{#if checked && ex.kind !== 'intro' && ex.kind !== 'match'}
			<div
				class="mb-2 rounded-xl p-3 {correct
					? 'bg-green-100 text-green-900 dark:bg-green-950 dark:text-green-100'
					: 'bg-red-100 text-red-900 dark:bg-red-950 dark:text-red-100'}"
				role="status"
				data-testid="feedback"
				data-correct={correct}
			>
				<p class="font-semibold">{correct ? `✓ ${m.correct()}` : `✗ ${m.wrong()}`}</p>
				{#if !correct}
					<p>
						<span lang="ko">{ex.item.text}</span>
						{#if roman}({ex.item.roman}){/if} = {script
							? `${ex.item.roman} · ${localized(ex.item.gloss, lang)}`
							: sound(ex.item)}
					</p>
				{/if}
			</div>
		{/if}
		{#if ex.kind === 'match' && matchMistakes}
			<p class="mb-2 rounded-xl bg-zinc-100 p-3 font-semibold dark:bg-zinc-800" role="status">
				{matchMistakes.size ? `✗ ${m.match_mistakes()}` : `✓ ${m.match_done()}`}
			</p>
		{/if}
		{#if canContinue}
			<button
				type="button"
				class="min-h-12 w-full rounded-xl bg-green-600 font-semibold text-white"
				onclick={next}
			>
				{m.continue()}
			</button>
		{:else if ex.kind !== 'match'}
			<button
				type="button"
				class="min-h-12 w-full rounded-xl bg-green-600 font-semibold text-white disabled:opacity-40"
				disabled={!answered}
				onclick={check}
			>
				{m.check()}
			</button>
		{/if}
	</footer>
{/if}

<Confirm
	bind:open={confirmExit}
	message={m.exit_confirm()}
	yes={m.exit_yes()}
	no={m.exit_no()}
	onyes={() => goto(resolve('/'))}
/>
