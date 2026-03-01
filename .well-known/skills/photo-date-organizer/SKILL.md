---
name: photo-date-organizer
description: Organize photos into date folders based on filename prefixes.
---

# Photo Date Organizer

Use this skill when the user asks to organize image files by date in year/month folders.

## Scope

- Work only in user-specified year (`yyyy`) or month (`yyyy/MM`) directories.
- Supported image extensions: `.jpg`, `.jpeg`, `.heic`, `.png` (case-insensitive).
- Scan only files directly under `yyyy` or `yyyy/MM`.
- Do not scan files inside any subdirectory under `yyyy` or `yyyy/MM`.
- If unsupported file formats are found in scanned paths, generate `unsupported_file_formats.md` after scan completes.

## Safety Rules

1. Never run on an unspecified path.
2. Verify target directories exist before writing/moving.
3. Validate directory naming before processing:
   - Year mode requires current directory name to match `^\d{4}$`.
   - Month mode requires parent year `^\d{4}$` and current month `^\d{2}$`.
4. If validation fails, return:
   - `現在不是 年份的檔案目錄` (for year validation failure), or
   - `現在不是 月份的檔案目錄` (for month validation failure).
5. Do not overwrite existing files. If a destination filename exists, append ` (1)`, ` (2)`, etc.

## Date Parsing Rules

- Parse only from filename prefix with either format:
  - `yyyy-MM-dd...`
  - `yyyy.MM.dd...`
- Regex: `^(\d{4})[-.](\d{2})[-.](\d{2})`
- If prefix date is missing, skip file.

## Scan Boundary Rules

1. In year mode (`yyyy`), scan only direct files in `yyyy`.
2. If year mode falls back to month scanning, scan only direct files in each `yyyy/MM`.
3. In month mode (`yyyy/MM`), scan only direct files in that month directory.
4. Any subdirectory under `yyyy` or `yyyy/MM` is excluded from scanning and must be reported in `skipped_scan_folders`.
5. Example excluded paths:
   - `2025/2025.12海邊玩/2021.11.11.jpg`
   - `2025/12/很好玩/2022.01.01.heic`

## Organization Rules

### A) Month mode (`yyyy/MM`)

- Create/use day folder named from file date as `yyyy.MM.dd`.
- Move file to:
  - `yyyy/MM/yyyy.MM.dd/<original-filename>`
- If folder already exists, move directly into it.
- Only process files whose parsed year/month match current `yyyy/MM`.

### B) Year mode (`yyyy`)

1. Check whether there are supported photos directly under `yyyy`.
2. If yes:
   - For each photo, parse date and move to:
     - `yyyy/MM/yyyy.MM.dd/<original-filename>`
   - Create month folder first, then date folder.
3. If no photos exist directly under `yyyy`:
   - Inspect `yyyy/MM` directories.
   - Apply month-mode logic on direct files of each month directory only.

## Execution Pattern

1. Preview first (dry-run style summary):
   - number to move
   - number skipped (non-photo / no date / mismatched year-month)
   - sample move paths
2. Execute actual move after user confirms (unless user explicitly asks to run immediately).
3. Report final counts:
   - moved
   - already_ok
   - skipped_non_photo
   - skipped_no_date
   - skipped_year_month_mismatch
   - name_collisions
   - skipped_scan_folders
   - unsupported_files
4. If `unsupported_files > 0`, create markdown report in scan target directory:
   - `unsupported_file_formats.md`
   - include extension summary and file list.

## Suggested Python Approach

- Use `pathlib.Path` and `re`.
- Use direct child iteration (`Path.iterdir()`) instead of recursive traversal.
- Compare extensions with `suffix.lower()`.
- Use `Path.rename()` for moves within same filesystem.
