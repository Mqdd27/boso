import { describe, expect, it } from 'vitest';
import { mark, oneSyllable, syllables, toneless } from './pinyin.js';

describe('pinyin', () => {
	it('puts the tone mark on the right vowel', () => {
		expect(['hao3', 'dou1', 'liu4', 'gui4', 'nu:3', 'lve4', 'er2', 'ma5'].map(mark)).toEqual([
			'hǎo',
			'dōu',
			'liù',
			'guì',
			'nǚ',
			'lüè',
			'ér',
			'ma'
		]);
	});

	it('splits a word into coloured syllables', () => {
		expect(syllables('nü3 er2')).toEqual([
			{ text: 'nǚ', tone: 3 },
			{ text: "'ér", tone: 2 }
		]);
		expect(
			syllables('xie4 xie5')
				.map((s) => s.text)
				.join('')
		).toBe('xièxie');
	});

	it('knows single syllables', () => {
		expect(toneless('ma3')).toBe('ma');
		expect([oneSyllable('ma3'), oneSyllable('ni3 hao3'), oneSyllable(undefined)]).toEqual([
			true,
			false,
			false
		]);
	});
});
