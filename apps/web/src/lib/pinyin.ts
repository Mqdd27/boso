// Numbered pinyin (the item's `tones`: "ni3 hao3") → tone-marked syllables, for tone colours.
const MARKS: Record<string, string> = {
	a: 'āáǎà',
	e: 'ēéěè',
	i: 'īíǐì',
	o: 'ōóǒò',
	u: 'ūúǔù',
	ü: 'ǖǘǚǜ'
};

export type Syllable = { text: string; tone: number };

/** "nü3" → "nü", "ma5" → "ma". */
export const toneless = (numbered: string) => numbered.replace(/[1-5]$/, '').replace(/v|u:/g, 'ü');

/** The tone of a numbered syllable, 5 (neutral) when it has no number. */
export const toneOf = (numbered: string) => Number(/[1-5]$/.exec(numbered)?.[0] ?? 5);

/** One numbered syllable with its tone mark: on a or e, on the o of ou, else on the last vowel. */
export function mark(numbered: string): string {
	const base = toneless(numbered);
	const tone = toneOf(numbered);
	if (tone === 5) return base;
	const at = /[ae]/.test(base)
		? base.search(/[ae]/)
		: base.includes('ou')
			? base.indexOf('o')
			: Math.max(...[...'iouü'].map((v) => base.lastIndexOf(v)));
	if (at < 0) return base;
	return base.slice(0, at) + MARKS[base[at]][tone - 1] + base.slice(at + 1);
}

/** Tone-marked syllables of an item's `tones`, with an apostrophe before a later a/e/o syllable. */
export const syllables = (tones: string): Syllable[] =>
	tones.split(' ').map((s, n) => {
		const text = mark(s);
		return { text: n && /^[aeo]/.test(text.normalize('NFD')) ? `'${text}` : text, tone: toneOf(s) };
	});

/** Single-syllable items can be asked for their tone. */
export const oneSyllable = (tones?: string) => !!tones && /^[a-zü:v]+[1-5]$/.test(tones);
