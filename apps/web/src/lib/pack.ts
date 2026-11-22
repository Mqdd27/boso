import { Ajv2020 } from 'ajv/dist/2020.js';
import schema from '../../../../schema/course-pack.schema.json';
import type { Course, Manifest, Pack } from './types.js';

const ajv = new Ajv2020({ allErrors: true, strictTypes: false });
// The only format the schema uses; a one-liner instead of the ajv-formats dependency.
ajv.addFormat('date-time', (s: string) => !Number.isNaN(Date.parse(s)));
ajv.addSchema(schema);
const validators = {
	course: ajv.compile({ $ref: `${schema.$id}#/$defs/course` }),
	manifest: ajv.compile({ $ref: `${schema.$id}#/$defs/manifest` })
};

export class PackError extends Error {}

/** Throws PackError unless `data` is a valid `course` / `manifest` (whole pack or nothing). */
export function validate(kind: 'course' | 'manifest', data: unknown): void {
	const check = validators[kind];
	if (!check(data)) {
		throw new PackError(`${kind}.json: ${ajv.errorsText(check.errors, { dataVar: kind })}`);
	}
}

export function validatePack(course: unknown, manifest: unknown): Pack {
	validate('course', course);
	validate('manifest', manifest);
	const c = course as Course;
	const seen = new Set<string>();
	for (const id of c.units.flatMap((u) => [u.id, ...u.items.map((i) => i.id)])) {
		if (seen.has(id)) throw new PackError(`course.json: duplicate id ${id}`);
		seen.add(id);
	}
	return { course: c, manifest: manifest as Manifest };
}

async function getJson(url: string, fetcher: typeof fetch): Promise<unknown> {
	const res = await fetcher(url);
	if (!res.ok) throw new PackError(`${url}: HTTP ${res.status}`);
	return res.json();
}

/** Course ids that sync-pack copied into static/packs/. Empty when there are none. */
export async function listCourses(fetcher: typeof fetch = fetch): Promise<string[]> {
	try {
		const index = (await getJson('/packs/index.json', fetcher)) as { courses?: string[] };
		return index.courses ?? [];
	} catch {
		return [];
	}
}

const cache = new Map<string, Promise<Pack>>();

export function loadPack(course: string, fetcher: typeof fetch = fetch): Promise<Pack> {
	let pack = cache.get(course);
	if (!pack) {
		pack = Promise.all([
			getJson(`/packs/${course}/course.json`, fetcher),
			getJson(`/packs/${course}/manifest.json`, fetcher)
		]).then(([c, m]) => validatePack(c, m));
		pack.catch(() => cache.delete(course));
		cache.set(course, pack);
	}
	return pack;
}
