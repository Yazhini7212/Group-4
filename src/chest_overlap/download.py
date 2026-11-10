"""Download the collections from Kaggle and record provenance.

For each collection this writes, under ``<data_root>``:

* ``raw/<key>/...``                     the extracted release, untouched
* ``manifests/<key>_download.json``    source, date, tool version, Kaggle metadata
* ``manifests/<key>_files.csv``        one row per file: path, size, SHA-256

The Kaggle command-line tool is called as a subprocess, so the code works with
both the 1.x and 2.x releases of the ``kaggle`` package.
"""

from __future__ import annotations

import csv
import datetime as dt
import hashlib
import json
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

from tqdm import tqdm

from .config import Collection

DONE_MARKER = ".download_complete"


# --------------------------------------------------------------------------- #
# Kaggle CLI
# --------------------------------------------------------------------------- #
def _kaggle_cmd() -> list[str]:
    exe = shutil.which("kaggle")
    if exe:
        return [exe]
    raise SystemExit(
        "The 'kaggle' command was not found. Install it with\n"
        "    pip install -r requirements.txt\n"
        "and make sure your Python Scripts folder is on PATH."
    )


def _run_kaggle(args: list[str]) -> str:
    cmd = _kaggle_cmd() + args
    print("  $ kaggle " + " ".join(args))
    proc = subprocess.run(cmd, capture_output=True, text=True)
    out = (proc.stdout or "") + (proc.stderr or "")
    if proc.returncode != 0:
        hint = ""
        low = out.lower()
        if "authentication" in low or "401" in low or "credentials" in low:
            hint = (
                "\nKaggle credentials missing. Either run 'kaggle auth login', or create a token at\n"
                "https://www.kaggle.com/settings/api and save it as ~/.kaggle/kaggle.json\n"
                "(legacy key) or set the KAGGLE_API_TOKEN environment variable."
            )
        elif "403" in low or "rules" in low:
            hint = (
                "\nAccess refused. For the RSNA competition you must first open\n"
                "https://www.kaggle.com/competitions/rsna-pneumonia-detection-challenge/rules\n"
                "while logged in and accept the rules."
            )
        raise RuntimeError(f"kaggle command failed:\n{out.strip()}{hint}")
    return out


def _kaggle_version() -> str:
    try:
        return _run_kaggle(["--version"]).strip()
    except Exception:  # noqa: BLE001 - best effort only
        return "unknown"


def _kaggle_download(col: Collection, dest: Path, file_name: str | None = None) -> None:
    group = "competitions" if col.kaggle_kind == "competition" else "datasets"
    args = [group, "download", col.kaggle_ref, "-p", str(dest)]
    if file_name:
        args += ["-f", file_name]
    _run_kaggle(args)


def _kaggle_dataset_metadata(col: Collection, dest: Path) -> dict:
    """Fetch the Kaggle metadata (licence, title, ...) for a dataset."""
    if col.kaggle_kind != "dataset":
        return {"licence": "Kaggle competition rules (accepted on kaggle.com)"}
    tmp = dest / "_kaggle_meta"
    tmp.mkdir(parents=True, exist_ok=True)
    try:
        _run_kaggle(["datasets", "metadata", col.kaggle_ref, "-p", str(tmp)])
        meta_file = next(tmp.glob("*.json"), None)
        return json.loads(meta_file.read_text(encoding="utf-8")) if meta_file else {}
    except Exception as exc:  # noqa: BLE001 - metadata is optional
        return {"error": str(exc)}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# --------------------------------------------------------------------------- #
# Archives and extra files
# --------------------------------------------------------------------------- #
def _extract_all_zips(folder: Path, keep_zip: bool) -> None:
    """Extract every .zip directly inside ``folder`` (Kaggle wraps downloads in zips)."""
    for zpath in sorted(folder.glob("*.zip")):
        print(f"  extracting {zpath.name}")
        with zipfile.ZipFile(zpath) as zf:
            members = zf.infolist()
            for m in tqdm(members, unit="file", leave=False):
                zf.extract(m, folder)  # zipfile strips absolute and '..' parts
        if not keep_zip:
            zpath.unlink()


def _fetch_url(url: str, target: Path) -> None:
    if target.exists():
        print(f"  {target.name} already present")
        return
    print(f"  fetching {url}")
    tmp = target.with_suffix(target.suffix + ".part")
    req = urllib.request.Request(url, headers={"User-Agent": "chest-overlap-data-fetch"})
    with urllib.request.urlopen(req, timeout=120) as resp, open(tmp, "wb") as fh:
        shutil.copyfileobj(resp, fh)
    tmp.replace(target)


# --------------------------------------------------------------------------- #
# Checksums
# --------------------------------------------------------------------------- #
def _sha256(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while block := fh.read(chunk):
            h.update(block)
    return h.hexdigest()


def write_file_manifest(raw_dir: Path, manifest_csv: Path) -> int:
    """Write path, size and SHA-256 for every file under ``raw_dir``.

    Rows from an earlier run are reused when size and modification time are
    unchanged, so re-running after a partial download is cheap.
    """
    previous: dict[str, dict] = {}
    if manifest_csv.exists():
        with open(manifest_csv, newline="", encoding="utf-8") as fh:
            previous = {r["rel_path"]: r for r in csv.DictReader(fh)}

    files = sorted(
        p for p in raw_dir.rglob("*") if p.is_file() and p.name != DONE_MARKER
    )
    manifest_csv.parent.mkdir(parents=True, exist_ok=True)
    tmp = manifest_csv.with_suffix(".csv.part")
    with open(tmp, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["rel_path", "size_bytes", "mtime", "sha256"])
        writer.writeheader()
        for p in tqdm(files, desc=f"checksums {raw_dir.name}", unit="file"):
            rel = p.relative_to(raw_dir).as_posix()
            st = p.stat()
            old = previous.get(rel)
            if old and int(old["size_bytes"]) == st.st_size and old["mtime"] == str(int(st.st_mtime)):
                digest = old["sha256"]
            else:
                digest = _sha256(p)
            writer.writerow(
                {"rel_path": rel, "size_bytes": st.st_size, "mtime": int(st.st_mtime), "sha256": digest}
            )
    tmp.replace(manifest_csv)
    return len(files)


# --------------------------------------------------------------------------- #
# Public entry point
# --------------------------------------------------------------------------- #
def download_collection(
    col: Collection,
    root: Path,
    metadata_only: bool = False,
    force: bool = False,
    keep_zip: bool = False,
    checksums: bool = True,
) -> Path:
    raw_dir = root / "raw" / col.key
    manifests = root / "manifests"
    raw_dir.mkdir(parents=True, exist_ok=True)
    manifests.mkdir(parents=True, exist_ok=True)

    print(f"\n=== {col.name} ({col.kaggle_url}) -> {raw_dir}")
    marker = raw_dir / DONE_MARKER

    if metadata_only:
        if not col.metadata_files:
            print("  this collection has no separate metadata files; nothing to do")
        for f in col.metadata_files:
            if (raw_dir / f).exists() and not force:
                print(f"  {f} already present")
                continue
            _kaggle_download(col, raw_dir, f)
        _extract_all_zips(raw_dir, keep_zip=False)
    elif marker.exists() and not force:
        print(f"  already downloaded ({marker.read_text().strip()}); use --force to redo")
    else:
        print(f"  full download, {col.approx_size}. This can take a long time.")
        _kaggle_download(col, raw_dir)
        _extract_all_zips(raw_dir, keep_zip=keep_zip)
        marker.write_text(dt.datetime.now(dt.timezone.utc).isoformat())

    for fname, url in col.extra_urls.items():
        _fetch_url(url, raw_dir / fname)

    record = {
        "collection": col.key,
        "name": col.name,
        "source": col.kaggle_url,
        "kaggle_ref": col.kaggle_ref,
        "kaggle_kind": col.kaggle_kind,
        "reference": col.reference,
        "extra_urls": col.extra_urls,
        "metadata_only": metadata_only,
        "downloaded_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "kaggle_cli": _kaggle_version(),
        "python": sys.version.split()[0],
        "kaggle_metadata": _kaggle_dataset_metadata(col, raw_dir),
        "notes": col.notes,
    }
    rec_path = manifests / f"{col.key}_download.json"
    rec_path.write_text(json.dumps(record, indent=2), encoding="utf-8")
    print(f"  provenance record: {rec_path}")

    if checksums:
        n = write_file_manifest(raw_dir, manifests / f"{col.key}_files.csv")
        print(f"  checksums for {n} files: {manifests / f'{col.key}_files.csv'}")
    return raw_dir
