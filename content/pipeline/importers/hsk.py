"""HSK 2.0 (2012) word lists, one word a line. Only the level number per word is used
(LICENSES.md, decision 1): the list itself is never shipped."""

from pathlib import Path


def words(path: Path) -> list[str]:
    """The words of one level file, in list order."""
    text = path.read_text(encoding="utf-8-sig")
    return [w.strip() for w in text.splitlines() if w.strip()]
