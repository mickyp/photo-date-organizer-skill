#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


DATE_RE = re.compile(r"^(\d{4})(?:[-.](\d{2})[-.](\d{2})|(\d{2})(\d{2}))")
YEAR_RE = re.compile(r"^\d{4}$")
MONTH_RE = re.compile(r"^\d{2}$")
PHOTO_EXTS = {".jpg", ".jpeg", ".heic", ".png"}
UNSUPPORTED_REPORT_NAME = "unsupported_file_formats.md"


@dataclass
class Stats:
    moved: int = 0
    already_ok: int = 0
    skipped_non_photo: int = 0
    skipped_no_date: int = 0
    skipped_year_month_mismatch: int = 0
    name_collisions: int = 0
    skipped_scan_folders: list[str] = field(default_factory=list)
    unsupported_files: list[str] = field(default_factory=list)
    sample_moves: list[str] = field(default_factory=list)


def parse_mode(path: Path, mode: str) -> str:
    if mode in {"year", "month"}:
        return mode
    if YEAR_RE.fullmatch(path.name):
        return "year"
    if path.parent and YEAR_RE.fullmatch(path.parent.name) and MONTH_RE.fullmatch(path.name):
        return "month"
    raise ValueError("auto mode cannot infer year/month from path")


def is_photo_file(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in PHOTO_EXTS


def parse_date_prefix(name: str) -> tuple[str, str, str] | None:
    m = DATE_RE.match(name)
    if not m:
        return None
    year = m.group(1)
    month = m.group(2) or m.group(4)
    day = m.group(3) or m.group(5)
    if not month or not day:
        return None
    return year, month, day


def safe_dest_path(dst: Path, stats: Stats) -> Path:
    if not dst.exists():
        return dst
    stem = dst.stem
    suffix = dst.suffix
    i = 1
    while True:
        candidate = dst.with_name(f"{stem} ({i}){suffix}")
        if not candidate.exists():
            stats.name_collisions += 1
            return candidate
        i += 1


def record_sample(stats: Stats, src: Path, dst: Path, base: Path) -> None:
    if len(stats.sample_moves) < 20:
        stats.sample_moves.append(f"{src.relative_to(base)} -> {dst.relative_to(base)}")


def process_month_files(month_dir: Path, year: str, month: str, apply: bool, stats: Stats) -> None:
    for child in sorted(month_dir.iterdir()):
        if child.is_dir():
            if child.name == "@eaDir":
                continue
            stats.skipped_scan_folders.append(str(child))
            continue

        if not is_photo_file(child):
            if child.name == UNSUPPORTED_REPORT_NAME:
                continue
            stats.skipped_non_photo += 1
            stats.unsupported_files.append(str(child))
            continue

        parsed = parse_date_prefix(child.name)
        if not parsed:
            stats.skipped_no_date += 1
            continue

        yy, mm, dd = parsed
        if yy != year or mm != month:
            stats.skipped_year_month_mismatch += 1
            continue

        target_dir = month_dir / f"{year}.{month}.{dd}"
        dst = target_dir / child.name

        if child == dst:
            stats.already_ok += 1
            continue

        dst = safe_dest_path(dst, stats)
        record_sample(stats, child, dst, month_dir)
        if apply:
            target_dir.mkdir(parents=True, exist_ok=True)
            child.rename(dst)
            stats.moved += 1


def run_year_mode(year_dir: Path, apply: bool) -> Stats:
    if not YEAR_RE.fullmatch(year_dir.name):
        raise ValueError("現在不是 年份的檔案目錄")

    stats = Stats()
    year = year_dir.name

    year_files = []
    month_dirs = []
    for child in sorted(year_dir.iterdir()):
        if child.is_dir():
            if child.name == "@eaDir":
                continue
            if MONTH_RE.fullmatch(child.name):
                month_dirs.append(child)
            else:
                stats.skipped_scan_folders.append(str(child))
            continue
        if child.name == UNSUPPORTED_REPORT_NAME:
            continue
        if is_photo_file(child):
            year_files.append(child)
        else:
            stats.skipped_non_photo += 1
            stats.unsupported_files.append(str(child))

    for src in year_files:
        parsed = parse_date_prefix(src.name)
        if not parsed:
            stats.skipped_no_date += 1
            continue

        yy, mm, dd = parsed
        if yy != year:
            stats.skipped_year_month_mismatch += 1
            continue

        month_dir = year_dir / mm
        target_dir = month_dir / f"{year}.{mm}.{dd}"
        dst = target_dir / src.name
        dst = safe_dest_path(dst, stats)
        record_sample(stats, src, dst, year_dir)

        if apply:
            target_dir.mkdir(parents=True, exist_ok=True)
            src.rename(dst)
            stats.moved += 1

    for month_dir in month_dirs:
        month_stats = Stats()
        process_month_files(month_dir, year, month_dir.name, apply, month_stats)
        stats.moved += month_stats.moved
        stats.already_ok += month_stats.already_ok
        stats.skipped_non_photo += month_stats.skipped_non_photo
        stats.skipped_no_date += month_stats.skipped_no_date
        stats.skipped_year_month_mismatch += month_stats.skipped_year_month_mismatch
        stats.name_collisions += month_stats.name_collisions
        stats.skipped_scan_folders.extend(month_stats.skipped_scan_folders)
        stats.unsupported_files.extend(month_stats.unsupported_files)
        for item in month_stats.sample_moves:
            if len(stats.sample_moves) < 20:
                stats.sample_moves.append(f"{month_dir.name}/{item}")

    return stats


def run_month_mode(month_dir: Path, apply: bool) -> Stats:
    if not MONTH_RE.fullmatch(month_dir.name) or not YEAR_RE.fullmatch(month_dir.parent.name):
        raise ValueError("現在不是 月份的檔案目錄")

    stats = Stats()
    process_month_files(month_dir, month_dir.parent.name, month_dir.name, apply, stats)
    return stats


def write_unsupported_report(target: Path, stats: Stats) -> Path | None:
    if not stats.unsupported_files:
        return None

    report_path = target / UNSUPPORTED_REPORT_NAME
    unique_files = sorted(set(stats.unsupported_files))

    def rel(path_str: str) -> str:
        p = Path(path_str)
        try:
            return str(p.relative_to(target))
        except ValueError:
            return str(p)

    ext_counter = Counter()
    for p in unique_files:
        ext = Path(p).suffix.lower() or "<no_extension>"
        ext_counter[ext] += 1

    lines: list[str] = []
    lines.append("# Unsupported File Formats")
    lines.append("")
    lines.append(f"- Generated at: `{datetime.now().isoformat(timespec='seconds')}`")
    lines.append(f"- Scan target: `{target}`")
    lines.append(f"- Unsupported file count: **{len(unique_files)}**")
    lines.append("")
    lines.append("## Extension Summary")
    lines.append("")
    for ext, count in sorted(ext_counter.items(), key=lambda x: (x[0])):
        lines.append(f"- `{ext}`: {count}")
    lines.append("")
    lines.append("## File List")
    lines.append("")
    for p in unique_files:
        lines.append(f"- `{rel(p)}`")
    lines.append("")

    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Organize photos into yyyy.MM.dd folders")
    parser.add_argument("target", type=Path, help="Target year or month folder path")
    parser.add_argument("--mode", choices=["auto", "year", "month"], default="auto")
    parser.add_argument("--apply", action="store_true", help="Apply moves (default is preview)")
    args = parser.parse_args()

    target = args.target.expanduser().resolve()
    if not target.exists() or not target.is_dir():
        print("target directory does not exist")
        return 1

    try:
        mode = parse_mode(target, args.mode)
        stats = run_year_mode(target, args.apply) if mode == "year" else run_month_mode(target, args.apply)
    except ValueError as err:
        print(str(err))
        return 1

    report_path = write_unsupported_report(target, stats)

    print(f"mode={mode}")
    print(f"target={target}")
    print(f"apply={args.apply}")
    print(f"moved={stats.moved}")
    print(f"already_ok={stats.already_ok}")
    print(f"skipped_non_photo={stats.skipped_non_photo}")
    print(f"skipped_no_date={stats.skipped_no_date}")
    print(f"skipped_year_month_mismatch={stats.skipped_year_month_mismatch}")
    print(f"name_collisions={stats.name_collisions}")
    print(f"skipped_scan_folders={len(stats.skipped_scan_folders)}")
    print(f"unsupported_files={len(set(stats.unsupported_files))}")
    if report_path:
        print(f"unsupported_report={report_path}")

    if stats.skipped_scan_folders:
        print("skipped_scan_folder_list:")
        for d in stats.skipped_scan_folders:
            print(d)

    if stats.sample_moves:
        print("sample_moves:")
        for s in stats.sample_moves:
            print(s)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
