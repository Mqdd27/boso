import { afterEach, describe, expect, it, vi } from 'vitest';
import { canListen, pickSource, play } from './audio.js';
import type { Item } from './types.js';

const item = (audio?: string): Item => ({
	id: 'ko.w.ne',
	type: 'word',
	text: '네',
	roman: 'ne',
	gloss: { en: 'yes' },
	source: 'krdict',
	license: 'CC BY-SA 2.0 KR',
	review: 'needs_review',
	...(audio ? { audio } : {})
});
const voice = { lang: 'ko-KR' } as SpeechSynthesisVoice;

describe('pickSource', () => {
	it('prefers the file, then speech, then nothing', () => {
		expect(pickSource(item('ko/w.ne.opus'), null)).toBe('file');
		expect(pickSource(item(), voice)).toBe('speech');
		expect(pickSource(item(), null)).toBe('none');
	});

	it('allows listening only when every item can be heard', () => {
		expect(canListen([item('ko/w.ne.opus'), item()], voice)).toBe(true);
		expect(canListen([item('ko/w.ne.opus'), item()], null)).toBe(false);
		expect(canListen([item('ko/w.ne.opus')], null)).toBe(true);
	});
});

describe('play', () => {
	const spoken: string[] = [];
	function stub(error?: string) {
		const played: { src: string; rate: number }[] = [];
		class FakeAudio {
			playbackRate = 1;
			constructor(public src: string) {}
			play() {
				if (error) return Promise.reject(Object.assign(new Error(error), { name: error }));
				played.push({ src: this.src, rate: this.playbackRate });
				return Promise.resolve();
			}
			pause() {}
		}
		vi.stubGlobal('Audio', FakeAudio);
		vi.stubGlobal(
			'SpeechSynthesisUtterance',
			class {
				constructor(public text: string) {}
			}
		);
		vi.stubGlobal('speechSynthesis', {
			cancel() {},
			speak: (u: { text: string }) => spoken.push(u.text)
		});
		return played;
	}
	afterEach(() => {
		vi.unstubAllGlobals();
		spoken.length = 0;
	});

	it('plays the pack file, slowly when asked', async () => {
		const played = stub();
		expect(await play(item('ko/w.ne.opus'), 'ko-en', voice, 0.7)).toBe('file');
		expect(played).toEqual([{ src: '/packs/ko-en/audio/ko/w.ne.opus', rate: 0.7 }]);
	});

	it('falls back to speech when the file is missing or broken', async () => {
		stub('NotSupportedError');
		expect(await play(item('ko/w.ne.opus'), 'ko-en', voice)).toBe('speech');
		expect(spoken).toEqual(['네']);
	});

	it('stays silent when autoplay is blocked', async () => {
		stub('NotAllowedError');
		expect(await play(item('ko/w.ne.opus'), 'ko-en', voice)).toBe('none');
		expect(spoken).toEqual([]);
	});

	it('has nothing to play without a file or a voice', async () => {
		stub();
		expect(await play(item(), 'ko-en', null)).toBe('none');
	});
});

describe('pinyin items', () => {
	it('are never read by a speech voice', () => {
		const ma = { ...item(), id: 'zh.c.ma3', text: 'mǎ', roman: 'mǎ' };
		expect(pickSource(ma, voice)).toBe('none');
		expect(pickSource({ ...ma, audio: 'zh/c.ma3.opus' }, voice)).toBe('file');
	});
});
