import { describe, expect, it } from 'vitest';
import { compose, confusable, decompose, similar } from './hangul.js';

describe('hangul', () => {
	it.each([
		['ㄱ', 'ㅏ', '', '가'],
		['ㄱ', 'ㅏ', 'ㄱ', '각'],
		['ㄲ', 'ㅙ', '', '꽤'],
		['ㅇ', 'ㅣ', 'ㄺ', '읽'],
		['ㅎ', 'ㅣ', 'ㅎ', '힣']
	])('%s + %s + %s = %s and back', (initial, vowel, final, block) => {
		expect(compose(initial, vowel, final)).toBe(block);
		expect(decompose(block)).toEqual({ initial, vowel, final });
	});

	it('rejects parts in the wrong slot and non-blocks', () => {
		expect(compose('ㅏ', 'ㄱ')).toBeNull();
		expect(compose('ㄸ', 'ㅏ', 'ㄸ')).toBeNull(); // ㄸ is never a final
		expect(decompose('ㄱ')).toBeNull();
		expect(decompose('가나')).toBeNull();
	});

	it('knows look-alikes', () => {
		expect(confusable('ㅓ', 'ㅗ')).toBe(true);
		expect(confusable('ㄱ', 'ㄲ')).toBe(true);
		expect(confusable('ㄱ', 'ㅏ')).toBe(false);
		expect(similar('가', '카')).toBe(true);
		expect(similar('가', '너')).toBe(false);
	});
});
