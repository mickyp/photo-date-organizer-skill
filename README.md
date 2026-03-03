# Photo Date Organizer Skill

This repository packages the `photo-date-organizer` skill for OpenCode and is ready to publish on GitHub.

Supported filename date prefixes:

- `yyyy-MM-dd`
- `yyyy.MM.dd`
- `yyyyMMdd`

Supported scan roots in year mode:

- `yyyy`
- `yyyy/MM`
- `yyyy/yyyyMM` (auto-normalized to `yyyy/MM`)

## Included Files

- `.well-known/skills/index.json`: skill discovery index.
- `.well-known/skills/photo-date-organizer/SKILL.md`: skill instructions.
- `.well-known/skills/photo-date-organizer/scripts/organize_photos_by_date.py`: helper script.

## Local Use

You can load this repo path as an extra skill path in OpenCode config:

```json
{
  "skills": {
    "paths": ["/absolute/path/to/photo-date-organizer-skill/.well-known/skills"]
  }
}
```

## Publish on GitHub

1. Create a new GitHub repository.
2. Push this folder.
3. (Optional) Enable GitHub Pages for branch `main` and root `/`.
4. Use this URL as an OpenCode skill URL:

```text
https://<your-username>.github.io/<your-repo>/.well-known/skills/
```

OpenCode will read `index.json` from that URL and discover the skill files.

## Script Quick Start

Preview only (no move):

```bash
python3 .well-known/skills/photo-date-organizer/scripts/organize_photos_by_date.py "/path/to/2025/12" --mode month
```

Apply changes:

```bash
python3 .well-known/skills/photo-date-organizer/scripts/organize_photos_by_date.py "/path/to/2025/12" --mode month --apply
```

If unsupported file formats are found in the scanned scope, the script writes:

- `unsupported_file_formats.md` in the scan target directory
