You are planning beginner vocabulary units for a Korean course (TOPIK I level) for learners
who speak English or Indonesian.

Make exactly {n_units} themed units from the candidate words below, in learning order: the most
useful, concrete everyday themes first (for example: greetings and basics, numbers, family, food
and drink, time and days, places, school and work, everyday verbs, describing things).

Rules:
- Use only IDs from the candidate list. Never invent words or IDs. Each ID at most once.
- Each unit has 5 to 8 words that clearly belong to its theme.
- These core words MUST each be used in some unit: {required}
- Other candidates are optional; not every candidate has to be used.
- Avoid themes that already exist: {existing_titles}
- `slug`: short English theme in lower case, words joined by "-" (e.g. "food-and-drink").
- `title_en`: short English title. `title_id`: the same title in natural Indonesian.

Reply with JSON only, no prose, in exactly this shape:

{{"units": [{{"slug": "greetings", "title_en": "Greetings", "title_id": "Salam", "items": ["ko.w.example", "..."]}}]}}

Candidates (id | word | part of speech | English | semantic category):
{candidates}
