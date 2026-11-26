from types import SimpleNamespace as NS

import pytest
import yaml

from pipeline import overrides

SENSES = [NS(number=1, en="take out, draw", id="mencabut"), NS(number=2, en="subtract", id=None)]
BY_CODE = {85714: NS(senses=SENSES)}
HINT = overrides.HintOverride(token="빼면", sense="빼다#85714/2", reason="Test fix.")


def sentence(gloss, review="needs_review"):
    return {"id": "ko.s.x", "review": review, "hints": [{"token": "빼면", "gloss": gloss}]}


@pytest.mark.parametrize(
    ("item", "gloss", "kept"),
    [
        (sentence({"en": "take out, draw", "id": "mencabut"}), {"en": "subtract"}, False),
        (sentence({"en": "subtract"}), {"en": "subtract"}, False),  # already fixed: no change
        (sentence({"en": "hand-edited"}), {"en": "hand-edited"}, True),
        (sentence({"en": "take out, draw", "id": "mencabut"}, "reviewed"), None, True),
    ],
)
def test_apply_hints(item, gloss, kept):
    fixed, was_kept = overrides.apply_hints([HINT], item, BY_CODE)
    assert fixed["hints"][0]["gloss"] == (gloss or item["hints"][0]["gloss"])
    assert was_kept is kept


def test_unknown_sense_fails():
    bad = overrides.HintOverride(token="빼면", sense="빼다#85714/9", reason="Test fix.")
    with pytest.raises(ValueError, match="no krdict sense"):
        overrides.apply_hints([bad], sentence({"en": "x"}), BY_CODE)


def test_check_flags_a_hint_override_that_matches_nothing(tmp_path):
    data = {"hints": [HINT.model_dump(), {**HINT.model_dump(), "token": "없는"}]}
    (tmp_path / "overrides.yaml").write_text(yaml.safe_dump(data, allow_unicode=True), "utf-8")
    units = [{"items": [sentence({"en": "x"})]}]
    errors = overrides.check(tmp_path, units)
    assert len(errors) == 1 and "'없는'" in errors[0]
