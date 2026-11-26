// Course-pack shapes, mirroring schema/course-pack.schema.json (the schema is the source of truth).
export type GlossLang = 'en' | 'id';
export type Localized = { en: string; id?: string };

export type Item = {
	id: string;
	type: 'word' | 'phrase' | 'sentence' | 'char';
	text: string;
	roman: string;
	tones?: string;
	gloss: Localized;
	audio?: string;
	source: string;
	license: string;
	author?: string;
	source_ref?: string;
	tokens?: string[];
	gloss_sources?: Partial<Record<GlossLang, Credit>>;
	hints?: { token: string; gloss: Localized }[];
	review: 'needs_review' | 'reviewed';
};

/** The `lang` attribute for an item's text, from its ID ("zh.w.ni3" → zh-Hans). */
export const langOf = (item: Item) => (item.id.startsWith('zh.') ? 'zh-Hans' : 'ko');

export type Credit = { source: string; license: string; author?: string; source_ref?: string };

export type Unit = {
	id: string;
	title: Localized;
	level: string;
	kind?: 'vocab' | 'script';
	items: Item[];
};

export type CourseMeta = {
	id: string;
	target: 'ko' | 'zh';
	title?: Localized;
	glosses: GlossLang[];
	levels: string[];
	version: string;
};

export type Course = CourseMeta & { units: Unit[] };

export type Attribution = {
	source: string;
	license: string;
	url?: string;
	authors?: string[];
	items?: number;
};

export type Manifest = {
	schema_version: 1;
	course: CourseMeta;
	build_date: string;
	attribution: Attribution[];
};

export type Pack = { course: Course; manifest: Manifest };

/** Text in the UI language, falling back to English. */
export function localized(text: Localized, lang: GlossLang): string {
	return (lang === 'id' && text.id) || text.en;
}

export const gloss = (item: Item, lang: GlossLang) => localized(item.gloss, lang);

/** A lesson node on the home path. */
export type NodeState = 'locked' | 'active' | 'done';
