#!/usr/bin/env python3
"""
Smart File Organizer
--------------------
Sorts files in a folder into category subfolders (Images, Documents, ...),
optionally by date, with dry-run, duplicate handling, and undo.

Usage:
    python smart_organizer.py ~/Downloads --dry-run
    python smart_organizer.py ~/Downloads
    python smart_organizer.py ~/Downloads --by-date
    python smart_organizer.py ~/Downloads --undo
"""

import argparse
import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path

# --- BEAUTIFICATION SETUP ---
class C:
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    MAGENTA = '\033[95m'

ICONS = {
    "Images": "🖼️ ",
    "Documents": "📄",
    "Spreadsheets": "📊",
    "Presentations": "📽️ ",
    "Videos": "🎬",
    "Audio": "🎵",
    "Archives": "📦",
    "Code": "💻",
    "Installers": "⚙️ ",
    "Others": "📁"
}
# ----------------------------

CATEGORIES = {
    "Images":      {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg"},
    "Documents":   {".pdf", ".doc", ".docx", ".txt", ".odt", ".rtf", ".md",".ipynb"},
    "Spreadsheets": {".xls", ".xlsx", ".csv", ".ods"},
    "Presentations": {".ppt", ".pptx", ".odp"},
    "Videos":      {".mp4", ".mkv", ".avi", ".mov", ".wmv"},
    "Audio":       {".mp3", ".wav", ".flac", ".aac", ".m4a"},
    "Archives":    {".zip", ".rar", ".7z", ".tar", ".gz"},
    "Code":        {".py", ".js", ".html", ".css", ".java", ".cpp", ".cs", ".json"},
    "Installers":  {".exe", ".msi", ".dmg", ".apk"},
}
LOG_NAME = ".organizer_log.json"


def get_category(path: Path) -> str:
    ext = path.suffix.lower()
    for category, extensions in CATEGORIES.items():
        if ext in extensions:
            return category
    return "Others"


def file_hash(path: Path, chunk: int = 65536) -> str:
    """SHA-256 of file contents, used to detect true duplicates."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while block := f.read(chunk):
            h.update(block)
    return h.hexdigest()


def unique_destination(dest: Path) -> Path:
    """If dest exists, return 'name (1).ext', 'name (2).ext', ..."""
    if not dest.exists():
        return dest
    counter = 1
    while True:
        candidate = dest.with_name(f"{dest.stem} ({counter}){dest.suffix}")
        if not candidate.exists():
            return candidate
        counter += 1


def truncate(string: str, length: int) -> str:
    """Truncates long filenames so they don't break the CLI table alignment."""
    return string if len(string) <= length else string[:length-3] + '...'


def organize(folder: Path, dry_run: bool, by_date: bool, skip_dupes: bool):
    moves = []
    skipped = 0

    # 1. Pre-fetch files so we can calculate formatting lengths
    items = [i for i in folder.iterdir() if i.is_file() and not i.name.startswith(".") and i.name != LOG_NAME]
    
    if not items:
        print(f"\n{C.YELLOW}✨ Folder is already clean! Nothing to organize.{C.RESET}\n")
        return

    # Calculate dynamic padding based on the longest filename (capped at 40 chars)
    max_len = max([len(i.name) for i in items])
    pad = min(max_len, 40)

    # 2. Print Header
    title = f"{C.BOLD}{C.CYAN}🔍 DRY RUN PREVIEW{C.RESET}" if dry_run else f"{C.BOLD}{C.GREEN}🚀 ORGANIZING FILES{C.RESET}"
    print(f"\n{title}\n{C.DIM}{'-'*65}{C.RESET}")

    # 3. Process Files
    for item in sorted(items):
        cat = get_category(item)
        icon = ICONS.get(cat, "📁")
        target_dir = folder / cat

        if by_date:
            modified = datetime.fromtimestamp(item.stat().st_mtime)
            target_dir = target_dir / f"{modified:%Y}" / f"{modified:%m-%B}"

        dest = target_dir / item.name
        
        # Format the filename to be perfectly aligned
        fname_display = truncate(item.name, pad).ljust(pad)

        # Duplicate check
        if dest.exists() and skip_dupes and file_hash(item) == file_hash(dest):
            skipped += 1
            print(f"{C.RED} 🚫 {C.RESET} {fname_display} {C.DIM}➔ Already in {cat}{C.RESET}")
            continue

        dest = unique_destination(dest)
        
        # Determine status icon and color
        status = f"{C.CYAN} ⏳ {C.RESET}" if dry_run else f"{C.GREEN} ✔️ {C.RESET}"
        rel_dest = dest.relative_to(folder)
        
        # Print aligned row
        print(f"{status} {fname_display} {C.YELLOW}➔{C.RESET} {icon} {rel_dest}")

        if not dry_run:
            target_dir.mkdir(parents=True, exist_ok=True)
            shutil.move(str(item), str(dest))
            moves.append({"from": str(item), "to": str(dest)})

    # 4. Print Summary Footer
    print(f"{C.DIM}{'-'*65}{C.RESET}")
    if dry_run:
        print(f"{C.BOLD}{C.CYAN}📊 Summary: {len(items) - skipped} files to move, {skipped} duplicates skipped.{C.RESET}\n")
    else:
        if moves:
            (folder / LOG_NAME).write_text(json.dumps(moves, indent=2))
            print(f"{C.BOLD}{C.GREEN}✨ Success! Moved {len(moves)} file(s). Skipped {skipped}.{C.RESET}")
            print(f"{C.DIM}💡 Tip: Use '--undo' if you want to reverse this.{C.RESET}\n")
        else:
            print(f"{C.YELLOW}✨ No files were moved.{C.RESET}\n")


def undo(folder: Path):
    log = folder / LOG_NAME
    if not log.exists():
        print(f"\n{C.RED}❌ No undo log found in {folder}.{C.RESET}\n")
        return
    
    moves = json.loads(log.read_text())
    print(f"\n{C.BOLD}{C.MAGENTA}⏪ UNDOING CHANGES{C.RESET}\n{C.DIM}{'-'*65}{C.RESET}")

    restored = 0
    for m in reversed(moves):
        src, dst = Path(m["to"]), Path(m["from"])
        if src.exists():
            shutil.move(str(src), str(unique_destination(dst)))
            print(f"{C.MAGENTA} ↩️  {C.RESET} Restored {dst.name}")
            restored += 1

    # Clean up empty category folders
    for sub in sorted(folder.rglob("*"), reverse=True):
        if sub.is_dir() and not any(sub.iterdir()):
            sub.rmdir()
            
    log.unlink()
    print(f"{C.DIM}{'-'*65}{C.RESET}")
    print(f"{C.BOLD}{C.GREEN}✨ Undo complete! Restored {restored} file(s).{C.RESET}\n")


def main():
    parser = argparse.ArgumentParser(description="Smart File Organizer")
    parser.add_argument("folder", type=Path, help="Folder to organize")
    parser.add_argument("--dry-run", action="store_true", help="Preview without moving")
    parser.add_argument("--by-date", action="store_true", help="Add Year/Month subfolders")
    parser.add_argument("--keep-dupes", action="store_true", help="Rename duplicates instead of skipping")
    parser.add_argument("--undo", action="store_true", help="Reverse the last run")
    args = parser.parse_args()

    folder = args.folder.expanduser().resolve()
    if not folder.is_dir():
        parser.error(f"{folder} is not a valid folder")

    if args.undo:
        undo(folder)
    else:
        organize(folder, args.dry_run, args.by_date, skip_dupes=not args.keep_dupes)


if __name__ == "__main__":
    main()