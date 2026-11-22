import { describe, expect, it } from 'vitest';
import en from '../../messages/en.json';
import id from '../../messages/id.json';

describe('messages', () => {
	it('every locale has the same keys as English', () => {
		expect(Object.keys(id).sort()).toEqual(Object.keys(en).sort());
	});

	it('no message is empty', () => {
		for (const messages of [en, id]) {
			for (const value of Object.values(messages)) expect(value).not.toBe('');
		}
	});
});
