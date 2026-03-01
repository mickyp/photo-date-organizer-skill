#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from dataclasses import dataclass, field
from pathlib import Path


DATE_RE = re.compile(r"^(\d{4})[-.](\d{2})[-.](\d{2})")
YEAR_RE = re.compile(r"^\d{4}$")
MONTH_RE = re.compile(r"^\d{2}$")
PHOTO_EXTS = {".jpg", ".jpeg", ".heic", ".png"}


@dataclass
class Stats:
    moved: int = 0
    already_ok: int = 0
    skipped_non_photo: int = 0
    skipped_no_date: int = 0
    skipped_year_month_mismatch: int = 0
    name_collisions: int = 0
    skipped_scan_folders: list[str] = field(default_factory=list)
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
            stats.skipped_non_photo += 1
            continue

        m = DATE_RE.match(child.name)
        if not m:
            stats.skipped_no_date += 1
            continue

        yy, mm, dd = m.groups()
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
        if is_photo_file(child):
            year_files.append(child)

    if year_files:
        for src in year_files:
            m = DATE_RE.match(src.name)
            if not m:
                stats.skipped_no_date += 1
                continue

            yy, mm, dd = m.groups()
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
        return stats

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
