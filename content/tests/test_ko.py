import pytest

from pipeline.nlp.ko import clean_pronunciation, romanize, slugify

# (written, krdict pronunciation or None, expected RR)
CASES = [
    ("가게", "가ː게", "gage"),
    ("나무", None, "namu"),
    ("한국", None, "hanguk"),  # batchim before nothing
    ("부엌", None, "bueok"),
    ("같이", "가치", "gachi"),  # palatalization from the pronunciation
    ("같이", None, "gachi"),  # ... and from the rules
    ("굳이", None, "guji"),
    ("먹다", "먹따", "meokda"),  # tensification is not written
    ("학교", "학꾜", "hakgyo"),
    ("좋다", "조ː타", "jota"),  # aspiration
    ("좋다", None, "jota"),
    ("축하", None, "chuka"),
    ("놓고", None, "noko"),
    ("신라", None, "silla"),  # ㄴ+ㄹ → ㄹㄹ
    ("설날", "설ː랄", "seollal"),  # ㄹ+ㄴ → ㄹㄹ
    ("종로", None, "jongno"),  # ㅇ+ㄹ → ㅇㄴ
    ("독립", None, "dongnip"),
    ("감사합니다", None, "gamsahamnida"),  # nasalization
    ("한국말", None, "hangungmal"),
    ("음악", None, "eumak"),  # batchim + vowel (liaison)
    ("읽어", None, "ilgeo"),
    ("없어", None, "eopseo"),
    ("많이", None, "mani"),
    ("좋아", None, "joa"),
    ("희망", "히망", "huimang"),  # vowels follow the spelling
    ("시계", "시게", "sigye"),
    ("별로", None, "byeollo"),  # ㄹㄹ → ll
    ("안녕하세요", None, "annyeonghaseyo"),
]


@pytest.mark.parametrize(("written", "pron", "expected"), CASES)
def test_romanize(written, pron, expected):
    assert romanize(written, pron) == expected


def test_mismatched_pronunciation_falls_back_to_rules():
    assert romanize("같이", "가") == "gachi"


def test_clean_pronunciation():
    assert clean_pronunciation("가ː치/가치") == "가치"


def test_slugify():
    assert slugify("Annyeong haseyo!") == "annyeong-haseyo"
