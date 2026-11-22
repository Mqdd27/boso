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
