<script lang="ts">
	import { resolve } from '$app/paths';
	import { goto } from '$app/navigation';
	import { db, recordLesson } from '#lib/db.js';
	import {
		generateLesson,
		arrangedRight,
		asksSound,
		isScript,
		label,
		lessonXp,
		requeue,
		TONES,
		type Exercise
	} from '#lib/lesson.js';
	import { m } from '#lib/paraglide/messages.js';
	import { settings, showRoman } from '#lib/settings.svelte.js';
	import { canListen, pickSource, play, SLOW } from '#lib/audio.js';
	import { dailyTotals, localDate, streak } from '#lib/stats.js';
	import { langOf, localized, type GlossLang, type Item, type Unit } from '#lib/types.js';
	import { mark, toneless, toneOf } from '#lib/pinyin.js';
	import Roman from './Roman.svelte';
	import BuildSyllable from './BuildSyllable.svelte';
	import Sentence from './Sentence.svelte';
	import WordBank from './WordBank.svelte';
	import Badge from './Badge.svelte';
	import Confetti from './Confetti.svelte';
	import Icon from './Icon.svelte';
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
		seed,
		review = false
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
		review?: boolean; // a review session: `unit` holds the due items
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
			// The pool a lesson asks from: this unit and the earlier ones of the same section.
			canListen: canListen(
				[unit, ...earlier.filter((u) => isScript(u) === isScript(unit))].flatMap((u) => u.items),
				voice
			)
		})
	);
	let index = $state(0);
	let selected = $state<number | null>(null);
	let built = $state<string | null>(null);
	let arranged = $state<string[]>([]);
	let checked = $state(false);
	let matchMistakes = $state<Set<string> | null>(null);
	let confirmExit = $state(false);
	let done = $state<{
		xp: number;
		accuracy: number;
		streak: number;
		perfect: boolean;
		seconds: number;
	} | null>(null);
	const started = Date.now();

	let answers = 0;
	let rightAnswers = 0;
	let mistakes = 0;
	const results: { id: string; correct: boolean }[] = [];

	const ex = $derived(queue[index]);
	// Hangul units ask for sounds, so romanization is the answer there: always shown where it is the
	// answer, never where it would give the answer away. Pinyin units are written in pinyin already.
	const script = $derived(asksSound(unit));
	const roman = $derived(!isScript(unit) && showRoman(course));
	const sound = (item: Item) => label(item, lang, script);
	const correct = $derived(
		ex?.kind === 'build'
			? built === ex.item.text
			: ex?.kind === 'arrange'
				? arrangedRight(arranged, ex.item)
				: ex?.kind === 'tone'
					? selected !== null && TONES[selected] === toneOf(ex.item.tones!)
					: !!ex && 'options' in ex && selected !== null && ex.options[selected].id === ex.item.id
	);
	const answered = $derived(
		ex?.kind === 'build'
			? built !== null
			: ex?.kind === 'arrange'
				? arranged.length > 0
				: selected !== null
	);

	function say(item: Item, rate = 1) {
		void play(item, course, voice, rate);
	}
	const audible = (item: Item) => pickSource(item, voice) !== 'none';

	$effect(() => {
		// Autoplay once per exercise (listening always: it has nothing else to show).
		if (
			ex?.kind === 'listen' ||
			ex?.kind === 'tone' ||
			((ex?.kind === 'build' || ex?.kind === 'arrange') && ex.listen)
		)
			say(ex.item);
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
			arranged = [];
			checked = false;
			matchMistakes = null;
			return;
		}
		const xp = lessonXp(mistakes);
		await recordLesson({ course, unit: unit.id, lesson, xp, results, review });
		const totals = dailyTotals(await db.activity.toArray());
		done = {
			xp,
			accuracy: Math.round((100 * rightAnswers) / Math.max(answers, 1)),
			streak: streak(totals, settings.dailyGoal, localDate(new Date())).current,
			perfect: mistakes === 0,
			seconds: Math.round((Date.now() - started) / 1000)
		};
	}

	const canContinue = $derived(
		ex?.kind === 'intro' || (ex?.kind === 'match' ? matchMistakes !== null : checked)
	);

	function onkeydown(e: KeyboardEvent) {
		if (done || confirmExit || !ex) return;
		const count = ex.kind === 'tone' ? TONES.length : 'options' in ex ? ex.options.length : 0;
		if (/^[1-5]$/.test(e.key) && !checked) {
			const n = Number(e.key) - 1;
			if (n < count) selected = n;
		} else if (e.key === 'Enter') {
			e.preventDefault();
			if (canContinue) void next();
			else check();
		}
	}

	const optionState = (n: number) => {
		if (ex?.kind === 'tone') return choiceState(n, TONES[n] === toneOf(ex.item.tones!));
		if (!ex || !('options' in ex)) return undefined;
		return choiceState(n, ex.options[n].id === ex.item.id);
	};
	const choiceState = (n: number, isAnswer: boolean) => {
		if (checked && isAnswer) return 'right';
		if (checked && n === selected) return 'wrong';
		return n === selected ? 'selected' : undefined;
	};
	// Feedback headline: a short rotating message, varied by step.
	const praise = [m.praise_1, m.praise_2, m.praise_3, m.praise_4];
	const miss = [m.miss_1, m.miss_2, m.miss_3];
	const headline = (ok: boolean) => (ok ? praise : miss)[index % (ok ? 4 : 3)]();
	const clock = (s: number) => `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`;
	const sheet = $derived(
		(checked && ex && ex.kind !== 'intro' && ex.kind !== 'match') ||
			(ex?.kind === 'match' && matchMistakes !== null)
	);
	const sheetOk = $derived(ex?.kind === 'match' ? !matchMistakes?.size : correct);
	const title = $derived(
		review
			? m.review_title()
			: practice
				? m.practice_title({ unit: localized(unit.title, lang) })
				: m.lesson_title({ unit: localized(unit.title, lang), lesson })
	);
</script>

<svelte:window {onkeydown} />

{#snippet speakers()}
	{#if ex && 'item' in ex}
		{@const item = ex.item}
		<div class="flex items-end gap-3">
			<button
				type="button"
				class="btn btn-blue size-24 !p-0"
				aria-label={m.play_again()}
				onclick={() => say(item)}
			>
				<Icon name="speaker" size={48} />
			</button>
			<button
				type="button"
				class="btn btn-outline size-14 !p-0 text-2xl"
				aria-label={m.listen_slow()}
				data-testid="listen-slow"
				onclick={() => say(item, SLOW)}
			>
				🐢
			</button>
		</div>
	{/if}
{/snippet}

{#if done}
	<Confetti />
	<section
		class="flex flex-1 flex-col items-center justify-center gap-6 py-10 text-center"
		data-testid="lesson-done"
	>
		<div
			class="done-pop flex size-28 items-center justify-center rounded-full bg-gold-fill text-gold-on"
		>
			<Icon name="star" size={64} filled />
		</div>
		<h1 class="text-3xl font-black text-gold-ink">{m.done_title()}</h1>
		{#if done.perfect}<p class="font-bold text-muted">{m.done_perfect()}</p>{/if}
		<ul class="grid w-full max-w-md grid-cols-3 gap-3">
			{#each [{ label: m.done_xp_label(), value: m.done_xp( { xp: done.xp } ), icon: 'bolt', tone: 'border-gold-fill bg-gold-fill text-gold-ink' }, { label: m.done_accuracy_label(), value: m.done_percent( { percent: done.accuracy } ), icon: 'target', tone: 'border-green-fill bg-green-fill text-green-ink' }, { label: m.done_time_label(), value: clock(done.seconds), icon: 'clock', tone: 'border-blue-fill bg-blue-fill text-blue-ink' }] as const as card, n (n)}
				<li
					class="done-card overflow-hidden rounded-card border-2 {card.tone}"
					style:animation-delay="{150 + n * 120}ms"
				>
					<p class="label px-1 py-1 text-[0.7rem] text-white {n === 0 ? '!text-gold-on' : ''}">
						{card.label}
					</p>
					<p
						class="flex items-center justify-center gap-1 rounded-t-xl bg-bg py-3 text-xl font-black"
					>
						<Icon name={card.icon} size={20} filled={card.icon === 'bolt'} />{card.value}
					</p>
				</li>
			{/each}
		</ul>
		<p class="flex items-center gap-1 font-extrabold text-orange-ink">
			<Icon name="flame" filled />{m.done_streak({ days: done.streak })}
		</p>
		<div class="mt-2 flex w-full max-w-md flex-col gap-3">
			{#if lesson === 1 && !practice}
				<button type="button" class="btn w-full" onclick={() => location.reload()}>
					{m.done_next()}
				</button>
			{/if}
			<a
				href={resolve('/')}
				class="btn w-full {lesson === 1 && !practice ? 'btn-outline' : ''}"
				data-testid="back-home"
			>
				{m.done_home()}
			</a>
		</div>
	</section>
{:else if ex}
	<header class="flex items-center gap-3 pt-4 pb-2">
		<button
			type="button"
			class="flex size-11 items-center justify-center rounded-xl text-muted hover:bg-raised"
			aria-label={m.exit()}
			onclick={() => (confirmExit = true)}
		>
			<Icon name="x" size={28} />
		</button>
		<div
			class="h-4 flex-1 overflow-hidden rounded-full bg-locked-fill"
			role="progressbar"
			aria-label={m.progress_label()}
			aria-valuemin={0}
			aria-valuemax={queue.length}
			aria-valuenow={index}
		>
			<div
				class="progress h-full rounded-full bg-green-fill"
				style:width="{(100 * index) / queue.length}%"
			></div>
		</div>
	</header>
	<p class="label mb-3 text-muted">{title}</p>

	<section
		class="flex flex-1 flex-col"
		data-testid="exercise"
		data-kind={ex.kind}
		data-listen={'listen' in ex ? ex.listen : undefined}
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
			<h2 class="mb-5 text-2xl font-extrabold">
				{script ? m.prompt_match_sound() : m.prompt_match()}
			</h2>
			{#key index}
				<MatchPairs items={ex.items} right={ex.right} label={sound} {roman} ondone={onMatchDone} />
			{/key}
		{:else}
			<h2 class="mb-5 text-2xl font-extrabold">
				{ex.kind === 'tone'
					? m.prompt_tone()
					: ex.kind === 'arrange'
						? ex.listen
							? m.prompt_arrange_listen()
							: m.prompt_arrange()
						: ex.kind === 'build'
							? m.prompt_build()
							: ex.kind === 'meaning'
								? script
									? m.prompt_sound()
									: ex.item.type === 'sentence'
										? m.prompt_sentence()
										: m.prompt_meaning()
								: ex.kind === 'word'
									? script
										? m.prompt_letter()
										: m.prompt_word()
									: script
										? m.prompt_listen_letter()
										: m.prompt_listen()}
			</h2>
			<div class="mb-6 flex flex-col items-center gap-2 text-center" data-testid="prompt">
				{#if ex.kind === 'tone'}
					{@render speakers()}
					<p class="text-3xl font-bold" data-testid="toneless">
						{#if ex.item.text !== ex.item.roman}<span lang={langOf(ex.item)}>{ex.item.text}</span>
						{/if}{toneless(ex.item.tones!)}
					</p>
				{:else if ex.kind === 'meaning'}
					{#if ex.item.type === 'sentence'}
						<Sentence item={ex.item} {lang} />
					{:else}
						<p class="text-5xl font-bold" lang={langOf(ex.item)}>
							{#if ex.item.text === ex.item.roman}<Roman item={ex.item} />{:else}{ex.item.text}{/if}
						</p>
					{/if}
					{#if roman}<p class="text-lg text-muted" data-testid="roman">
							<Roman item={ex.item} />
						</p>{/if}
				{:else if ex.kind === 'word' || ((ex.kind === 'build' || ex.kind === 'arrange') && !ex.listen)}
					<p
						class="rounded-card border-2 border-line px-5 py-3 text-2xl font-extrabold"
						data-testid={script ? 'sound' : undefined}
					>
						{sound(ex.item)}
					</p>
				{:else}
					{@render speakers()}
				{/if}
				<Badge item={ex.item} />
			</div>
			{#if ex.kind === 'build'}
				{#key index}
					<BuildSyllable tiles={ex.tiles} disabled={checked} bind:value={built} />
				{/key}
			{:else if ex.kind === 'arrange'}
				{#key index}
					<WordBank
						bank={ex.bank}
						roman={roman ? ex.roman : undefined}
						lang={langOf(ex.item)}
						disabled={checked}
						bind:value={arranged}
					/>
				{/key}
			{:else if ex.kind === 'tone'}
				{@const base = toneless(ex.item.tones!)}
				<ol class="grid grid-cols-2 gap-3 sm:grid-cols-5" data-testid="tones">
					{#each TONES as tone, n (tone)}
						<li class={n === TONES.length - 1 ? 'col-span-2 sm:col-span-1' : ''}>
							<button
								type="button"
								class="card flex min-h-16 w-full flex-col items-center justify-center px-2 py-2"
								disabled={checked}
								aria-pressed={n === selected}
								data-state={optionState(n)}
								data-tone={tone}
								onclick={() => (selected = n)}
							>
								<span class="text-2xl font-bold">{mark(`${base}${tone}`)}</span>
								<span class="text-sm font-semibold opacity-75">
									{tone === 5 ? m.tone_neutral() : m.tone_n({ n: tone })}
								</span>
							</button>
						</li>
					{/each}
				</ol>
				<p class="mt-4 hidden text-sm text-muted sm:block">{m.keyboard_hint_tone()}</p>
			{:else}
				<ol class="flex flex-col gap-3">
					{#each ex.options as option, n (option.id)}
						<li>
							<button
								type="button"
								class="card flex min-h-14 w-full items-center gap-3 px-3 py-2 text-left"
								disabled={checked}
								aria-pressed={n === selected}
								data-state={optionState(n)}
								data-option={option.id}
								onclick={() => (selected = n)}
							>
								<kbd
									class="hidden size-7 shrink-0 items-center justify-center rounded-lg border-2 border-current text-sm font-bold opacity-60 sm:flex"
								>
									{n + 1}
								</kbd>
								{#if ex.kind === 'meaning'}
									<span class="text-lg font-bold">{sound(option)}</span>
								{:else}
									<span class="text-xl font-bold" lang={langOf(option)}>
										{#if option.text === option.roman}<Roman
												item={option}
											/>{:else}{option.text}{/if}
									</span>
									{#if roman}<span class="text-sm opacity-75" data-testid="roman">
											<Roman item={option} />
										</span>{/if}
								{/if}
							</button>
						</li>
					{/each}
				</ol>
				<p class="mt-4 hidden text-sm text-muted sm:block">{m.keyboard_hint()}</p>
			{/if}
		{/if}
	</section>

	<!-- Spacer so the fixed footer never covers the last answer. -->
	<div class="h-36" aria-hidden="true"></div>
	<footer
		class="fixed inset-x-0 bottom-0 z-10 border-t-2 pb-[env(safe-area-inset-bottom)] {sheet
			? sheetOk
				? 'sheet border-transparent bg-green-soft'
				: 'sheet border-transparent bg-red-soft'
			: 'border-line bg-bg'}"
	>
		<div class="mx-auto flex max-w-2xl flex-col gap-4 px-4 py-5">
			{#if sheet}
				<div
					class="flex items-start gap-3 {sheetOk ? 'text-green-ink' : 'text-red-ink'}"
					role="status"
					aria-live="polite"
					data-testid={ex.kind === 'match' ? 'match-feedback' : 'feedback'}
					data-correct={ex.kind === 'match' ? undefined : correct}
				>
					<span
						class="flex size-10 shrink-0 items-center justify-center rounded-full bg-bg"
						aria-hidden="true"
					>
						<Icon name={sheetOk ? 'check' : 'x'} size={26} />
					</span>
					<div class="min-w-0 flex-1">
						{#if ex.kind === 'match'}
							<p class="text-xl font-black">{headline(sheetOk)}</p>
							<p class="font-semibold">{sheetOk ? m.match_done() : m.match_mistakes()}</p>
						{:else}
							<p class="text-xl font-black">{headline(correct)}</p>
							{#if !correct}
								<p class="font-bold">{m.correct_answer()}</p>
								<p class="flex flex-wrap items-center gap-x-2">
									<span class="text-lg font-bold" lang={langOf(ex.item)}>{ex.item.text}</span>
									{#if roman || ex.kind === 'tone'}<span>(<Roman item={ex.item} />)</span>{/if}
									<span>
										= {script
											? `${ex.item.roman} · ${localized(ex.item.gloss, lang)}`
											: sound(ex.item)}
									</span>
									{#if audible(ex.item)}
										<button
											type="button"
											class="flex size-11 items-center justify-center rounded-full hover:bg-bg/60"
											aria-label={m.listen()}
											onclick={() => say(ex.item)}
										>
											<Icon name="speaker" />
										</button>
									{/if}
								</p>
							{/if}
						{/if}
					</div>
				</div>
			{/if}
			{#if canContinue}
				<button
					type="button"
					class="btn w-full {sheet && !sheetOk ? 'btn-red' : ''}"
					onclick={next}
				>
					{m.continue()}
				</button>
			{:else if ex.kind !== 'match'}
				<button type="button" class="btn w-full" disabled={!answered} onclick={check}>
					{m.check()}
				</button>
			{/if}
		</div>
	</footer>
{/if}

<Confirm
	bind:open={confirmExit}
	message={m.exit_confirm()}
	yes={m.exit_yes()}
	no={m.exit_no()}
	onyes={() => goto(resolve('/'))}
/>

<style>
	.progress {
		position: relative;
		transition: width 300ms var(--ease-out-expo);
	}
	.progress::after {
		content: '';
		position: absolute;
		inset: 3px 8px auto;
		height: 4px;
		border-radius: 9999px;
		background: rgb(255 255 255 / 0.3);
	}
	.sheet {
		animation: rise 250ms var(--ease-out-expo);
	}
	@keyframes rise {
		from {
			transform: translateY(100%);
		}
	}
	.done-pop {
		animation: pop 400ms var(--ease-out-expo);
	}
	.done-card {
		animation: pop 300ms var(--ease-out-expo) backwards;
	}
	@keyframes pop {
		from {
			opacity: 0;
			transform: scale(0.8);
		}
	}
</style>
