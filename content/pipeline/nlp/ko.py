"""Korean Revised Romanization (국어의 로마자 표기법, 2000).

With a krdict pronunciation (발음) the consonants come from it, since it already spells the sound
changes (같이 → [가치]). Without one, `romanize` applies the common sound changes that RR writes
out itself: liaison, palatalization, aspiration, nasalization and ㄹ assimilation. Tensification is
never written in RR, and vowels always follow the spelling.
"""

import re

INITIALS = "ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ"
VOWELS = "ㅏㅐㅑㅒㅓㅔㅕㅖㅗㅘㅙㅚㅛㅜㅝㅞㅟㅠㅡㅢㅣ"
FINALS = ["", *"ㄱㄲㄳㄴㄵㄶㄷㄹㄺㄻㄼㄽㄾㄿㅀㅁㅂㅄㅅㅆㅇㅈㅊㅋㅌㅍㅎ"]

ROMAN_INITIAL = dict(
    zip(INITIALS, "g kk n d tt r m b pp s ss - j jj ch k t p h".split(), strict=True)
)
ROMAN_INITIAL["ㅇ"] = ""
ROMAN_VOWEL = dict(
    zip(VOWELS, "a ae ya yae eo e yeo ye o wa wae oe yo u wo we wi yu eu ui i".split(), strict=True)
)
ROMAN_FINAL = {"": "", "ㄱ": "k", "ㄴ": "n", "ㄷ": "t", "ㄹ": "l", "ㅁ": "m", "ㅂ": "p", "ㅇ": "ng"}

# Final consonant → the one of 7 representative sounds it is pronounced as before a consonant.
NEUTRAL = {
    **dict.fromkeys("ㄱㄲㅋㄳㄺ", "ㄱ"),
    **dict.fromkeys("ㄷㅅㅆㅈㅊㅌㅎ", "ㄷ"),
    **dict.fromkeys("ㅂㅍㅄㄿ", "ㅂ"),
    **dict.fromkeys("ㄴㄵㄶ", "ㄴ"),
    **dict.fromkeys("ㅁㄻ", "ㅁ"),
    **dict.fromkeys("ㄹㄼㄽㄾㅀ", "ㄹ"),
    "ㅇ": "ㅇ",
    "": "",
}
# Double final before a vowel: (stays, moves to the next syllable). ㅎ is silent before a vowel.
SPLIT = {
    "ㄳ": ("ㄱ", "ㅅ"),
    "ㄵ": ("ㄴ", "ㅈ"),
    "ㄶ": ("", "ㄴ"),
    "ㄺ": ("ㄹ", "ㄱ"),
    "ㄻ": ("ㄹ", "ㅁ"),
    "ㄼ": ("ㄹ", "ㅂ"),
    "ㄽ": ("ㄹ", "ㅅ"),
    "ㄾ": ("ㄹ", "ㅌ"),
    "ㄿ": ("ㄹ", "ㅍ"),
    "ㅀ": ("", "ㄹ"),
    "ㅄ": ("ㅂ", "ㅅ"),
    "ㅎ": ("", ""),
}
ASPIRATE = {"ㄱ": "ㅋ", "ㄷ": "ㅌ", "ㅂ": "ㅍ", "ㅈ": "ㅊ"}
NASAL = {"ㄱ": "ㅇ", "ㄷ": "ㄴ", "ㅂ": "ㅁ"}
TENSE = {"ㄲ": "ㄱ", "ㄸ": "ㄷ", "ㅃ": "ㅂ", "ㅆ": "ㅅ", "ㅉ": "ㅈ"}  # tense → plain

Syllable = list[str]  # [initial, vowel, final]


def _decompose(ch: str) -> Syllable | None:
    code = ord(ch) - 0xAC00
    if not 0 <= code < 11172:
        return None
    return [INITIALS[code // 588], VOWELS[code % 588 // 28], FINALS[code % 28]]


def _sound_changes(a: Syllable, b: Syllable) -> None:
    """Apply the sound changes between syllable a and the following syllable b, in place."""
    t, nxt = a[2], b[0]
    if not t:
        return
    if nxt == "ㅇ" and t != "ㅇ":  # liaison: 같이 → 가티, 읽어 → 일거, 좋아 → 조아
        a[2], b[0] = SPLIT.get(t, ("", t))
        b[0] = b[0] or "ㅇ"
        if b[1] == "ㅣ" and b[0] in "ㄷㅌ":  # palatalization: 가티 → 가치
            b[0] = "ㅈ" if b[0] == "ㄷ" else "ㅊ"
        return
    if t in "ㅎㄶㅀ" and nxt in ASPIRATE:  # 좋다 → 조타, 많다 → 만타
        a[2], b[0] = {"ㅎ": "", "ㄶ": "ㄴ", "ㅀ": "ㄹ"}[t], ASPIRATE[nxt]
        return
    if nxt == "ㅎ" and NEUTRAL[t] in ASPIRATE and t not in "ㄼㄺ":  # 축하 → 추카, 입학 → 이팍
        a[2], b[0] = "", ASPIRATE[NEUTRAL[t]]
        return
    t = NEUTRAL[t]
    if nxt == "ㄹ":
        if t == "ㄴ":  # 신라 → 실라
            t = "ㄹ"
        elif t in "ㄱㄷㅂㅁㅇ":  # 종로 → 종노, 독립 → 동닙
            nxt = "ㄴ"
    elif nxt == "ㄴ" and t == "ㄹ":  # 설날 → 설랄
        nxt = "ㄹ"
    if nxt in "ㄴㅁ" and t in NASAL:  # 감사합니다 → 감사함니다
        t = NASAL[t]
    a[2], b[0] = t, nxt


def _romanize_word(syllables: list[Syllable]) -> str:
    out = []
    for i, (initial, vowel, final) in enumerate(syllables):
        after_l = i > 0 and syllables[i - 1][2] == "ㄹ"
        out.append("l" if initial == "ㄹ" and after_l else ROMAN_INITIAL[initial])
        out.append(ROMAN_VOWEL[vowel])
        out.append(ROMAN_FINAL[NEUTRAL[final]])
    return "".join(out)


def romanize(text: str, pron: str | None = None) -> str:
    """Revised Romanization of `text`, using its krdict pronunciation `pron` when given.

    From the pronunciation RR takes the consonant changes (같이 [가치] → gachi), but not
    tensification (먹다 [먹따] → meokda) and not vowel changes (희망 [히망] → huimang).
    """
    if pron:
        written = [_decompose(ch) for ch in text]
        spoken = [_decompose(ch) for ch in clean_pronunciation(pron)]
        if None not in written and None not in spoken and len(written) == len(spoken):
            for w, p in zip(written, spoken, strict=True):
                if TENSE.get(p[0]) == w[0]:
                    p[0] = w[0]
                p[1] = w[1]
            return _romanize_word(spoken)
    out = []
    for run in re.split(r"([가-힣]+)", text):
        if not run or not ("가" <= run[0] <= "힣"):
            out.append(run)
            continue
        syllables = [s for ch in run if (s := _decompose(ch))]
        for a, b in zip(syllables, syllables[1:], strict=False):
            _sound_changes(a, b)
        out.append(_romanize_word(syllables))
    return "".join(out)


def clean_pronunciation(pron: str) -> str:
    """First variant of a krdict pronunciation, without length marks: '가ː치/가치' → '가치'."""
    return re.split(r"[/,]", pron)[0].replace("ː", "").replace(":", "").strip()


def slugify(roman: str) -> str:
    """ID slug from a romanization: lower case [a-z0-9-]."""
    return re.sub(r"[^a-z0-9]+", "-", roman.lower()).strip("-")
