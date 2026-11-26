"""Download raw sources into sources/ and pin them in sources.lock (name → file + sha256)."""

import hashlib
import json
import re
import shutil
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

CONTENT = Path(__file__).resolve().parents[1]
SOURCES = CONTENT / "sources"
LOCK = CONTENT / "sources.lock"

KRDICT_PAGE = "https://krdict.korean.go.kr/download/downloadPopup"
KRDICT_DOWNLOAD = "https://krdict.korean.go.kr/dicBatchDownload?seq={seq}"
KRDICT_FILE = "krdict/krdict-json.zip"
USER_AGENT = "boso-content-pipeline"

TATOEBA = "https://downloads.tatoeba.org/exports/"
# Per-language exports keep the download small; the CC0 list only exists as one global file.
TATOEBA_FILES = [
    "per_language/kor/kor_sentences_detailed.tsv.bz2",
    "per_language/kor/kor-eng_links.tsv.bz2",
    "per_language/kor/kor-ind_links.tsv.bz2",
    "per_language/kor/kor_tags.tsv.bz2",
    "per_language/eng/eng_sentences_detailed.tsv.bz2",
    "per_language/eng/eng_tags.tsv.bz2",
    "per_language/ind/ind_sentences_detailed.tsv.bz2",
    "per_language/ind/ind_tags.tsv.bz2",
    "sentences_CC0.tar.bz2",
]


CEDICT_URL = "https://www.mdbg.net/chinese/export/cedict/cedict_1_0_ts_utf-8_mdbg.txt.gz"
CEDICT_FILE = "cedict/cedict_1_0_ts_utf-8_mdbg.txt.gz"
# HSK 2.0 (2012) lists, pinned to one commit. Only word → level is used (LICENSES.md decision 1).
HSK_COMMIT = "8a6f229c699e2fd7ac8708156c55c3afb2be7e1f"
HSK_URL = (
    "https://raw.githubusercontent.com/glxxyz/hskhsk.com/{commit}/data/lists/"
    "HSK%20Official%202012%20L{level}.txt"
)
HSK_LEVELS = (1, 2)


def hsk_key(level: int) -> str:
    return f"hsk:l{level}"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_lock(lock: Path = LOCK) -> dict:
    return json.loads(lock.read_text(encoding="utf-8")) if lock.is_file() else {}


def _get(url: str) -> urllib.request.Request:
    return urllib.request.Request(url, headers={"User-Agent": USER_AGENT})


def krdict_json_seq(html: str) -> str:
    """The download id of the 'Json 전체 내려받기' button on krdict's download popup."""
    for seq, label in re.findall(r"batchDownload\('(\d+)'\)[^>]*>(?:\s*<[^>]+>)*([^<]*)", html):
        if "json" in label.lower():
            return seq
    raise RuntimeError(f"no JSON download button found on {KRDICT_PAGE}")


def fetch_krdict(src: Path | None = None, sources: Path = SOURCES, lock: Path = LOCK) -> Path:
    """Copy `src` (a manually downloaded JSON zip) or download the full krdict JSON dump."""
    dest = sources / KRDICT_FILE
    dest.parent.mkdir(parents=True, exist_ok=True)
    if src:
        if src.resolve() != dest.resolve():
            shutil.copyfile(src, dest)
        url = None
    else:
        with urllib.request.urlopen(_get(KRDICT_PAGE), timeout=60) as r:
            url = KRDICT_DOWNLOAD.format(seq=krdict_json_seq(r.read().decode("utf-8")))
        with urllib.request.urlopen(_get(url), timeout=600) as r, dest.open("wb") as f:
            shutil.copyfileobj(r, f)
    entries = read_lock(lock)
    entries["krdict"] = {
        "file": KRDICT_FILE,
        "sha256": sha256(dest),
        "url": url or "manual download from https://krdict.korean.go.kr (사전 전체 내려받기)",
        "fetched": datetime.now(UTC).date().isoformat(),
    }
    lock.write_text(json.dumps(entries, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return dest


def _download(name: str, url: str, rel: str, sources: Path, lock: Path, force: bool) -> Path:
    """Download `url` to sources/`rel` (unless already there) and pin it in sources.lock."""
    dest = sources / rel
    downloaded = force or not dest.is_file()
    if downloaded:
        dest.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(_get(url), timeout=600) as r, dest.open("wb") as f:
            shutil.copyfileobj(r, f)
    entries = read_lock(lock)
    today = datetime.now(UTC).date().isoformat()
    old = entries.get(name, {}).get("fetched", today)
    entries[name] = {
        "file": rel,
        "sha256": sha256(dest),
        "url": url,
        "fetched": today if downloaded else old,
    }
    lock.write_text(json.dumps(entries, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return dest


def fetch_cedict(sources: Path = SOURCES, lock: Path = LOCK, force: bool = False) -> Path:
    return _download("cedict", CEDICT_URL, CEDICT_FILE, sources, lock, force)


def fetch_hsk(sources: Path = SOURCES, lock: Path = LOCK, force: bool = False) -> list[Path]:
    return [
        _download(
            hsk_key(n),
            HSK_URL.format(commit=HSK_COMMIT, level=n),
            f"hsk/hsk2012-l{n}.txt",
            sources,
            lock,
            force,
        )
        for n in HSK_LEVELS
    ]


def tatoeba_key(remote: str) -> str:
    """sources.lock key of one Tatoeba export: tatoeba:kor_sentences_detailed."""
    return "tatoeba:" + Path(remote).name.split(".")[0]


def fetch_tatoeba(sources: Path = SOURCES, lock: Path = LOCK, force: bool = False) -> list[Path]:
    """Download the Tatoeba exports (skipping files already on disk unless `force`)."""
    entries = read_lock(lock)
    out = []
    for remote in TATOEBA_FILES:
        rel = f"tatoeba/{Path(remote).name}"
        dest = sources / rel
        downloaded = force or not dest.is_file()
        if downloaded:
            dest.parent.mkdir(parents=True, exist_ok=True)
            with (
                urllib.request.urlopen(_get(TATOEBA + remote), timeout=600) as r,
                dest.open("wb") as f,
            ):
                shutil.copyfileobj(r, f)
        today = datetime.now(UTC).date().isoformat()
        old = entries.get(tatoeba_key(remote), {}).get("fetched", today)
        entries[tatoeba_key(remote)] = {
            "file": rel,
            "sha256": sha256(dest),
            "url": TATOEBA + remote,
            "fetched": today if downloaded else old,
        }
        out.append(dest)
    lock.write_text(json.dumps(entries, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return out


def check(name: str, sources: Path = SOURCES, lock: Path = LOCK) -> Path:
    """Path of a fetched source, after checking it matches sources.lock."""
    entry = read_lock(lock).get(name)
    if not entry:
        raise RuntimeError(f"{name} is not in {lock.name}; run `pipeline fetch {name}`")
    path = sources / entry["file"]
    if not path.is_file():
        raise RuntimeError(f"{path} is missing; run `pipeline fetch {name}`")
    if sha256(path) != entry["sha256"]:
        raise RuntimeError(f"{path} does not match the sha256 in {lock.name}")
    return path
