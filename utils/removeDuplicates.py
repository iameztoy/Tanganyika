# Detects and moves duplicates | It also creates a log file with all the pairings.
# Iban Ameztoy April 2026 - Started after the release of SWOT version D.

#E.g.
#SWOT_L2_HR_Raster_100m_UTM29Q_N_x_x_x_039_169_093F_20250927T024038_20250927T024059_PID0_01 and SWOT_L2_HR_Raster_100m_UTM29Q_N_x_x_x_039_169_093F_20250927T024038_20250927T024059_PID0_02
# _01 is moved to "moved" folder and _02 is kept. See SWOT naming convention.


from __future__ import annotations

import argparse
import re
import shutil
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

try:
    import tkinter as tk
    from tkinter import filedialog
except Exception:
    tk = None
    filedialog = None


# Detect names ending in _01, _02, _03, etc.
# Example:
# SWOT_..._PID0_01
VERSION_RE = re.compile(r"^(?P<core>.+)_(?P<version>\d{2})$")


@dataclass(frozen=True)
class CandidateFile:
    path: Path
    core: str
    version: int
    extension: str


def choose_folder_with_dialog() -> Optional[Path]:
    """Open a folder picker if no folder is passed by command line."""
    if tk is None or filedialog is None:
        return None

    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    folder = filedialog.askdirectory(title="Select the folder to process")
    root.destroy()

    if not folder:
        return None
    return Path(folder)


def split_filename(file_path: Path) -> Optional[CandidateFile]:
    """
    Return parsed file info if the filename ends with _NN before extension.
    Works with or without file extensions.
    """
    suffixes = "".join(file_path.suffixes)
    name_without_ext = file_path.name[:-len(suffixes)] if suffixes else file_path.name

    match = VERSION_RE.match(name_without_ext)
    if not match:
        return None

    version = int(match.group("version"))
    core = match.group("core")

    return CandidateFile(
        path=file_path,
        core=core,
        version=version,
        extension=suffixes,
    )


def build_unique_destination(destination: Path) -> Path:
    """
    Avoid overwriting if a file with the same name already exists in /moved.
    """
    if not destination.exists():
        return destination

    suffixes = "".join(destination.suffixes)
    base = destination.name[:-len(suffixes)] if suffixes else destination.name

    counter = 1
    while True:
        candidate = destination.parent / f"{base}__moved{counter}{suffixes}"
        if not candidate.exists():
            return candidate
        counter += 1


def process_folder(folder: Path, dry_run: bool = False) -> None:
    if not folder.exists():
        raise FileNotFoundError(f"Folder does not exist: {folder}")
    if not folder.is_dir():
        raise NotADirectoryError(f"Not a folder: {folder}")

    moved_folder = folder / "moved"

    # Group files by everything except the final _NN version
    groups: dict[tuple[str, str], list[CandidateFile]] = defaultdict(list)

    for item in folder.iterdir():
        if item.name == "moved" and item.is_dir():
            continue
        if not item.is_file():
            continue

        parsed = split_filename(item)
        if parsed is None:
            continue

        groups[(parsed.core, parsed.extension)].append(parsed)

    moved_records: list[tuple[str, str]] = []
    groups_found = 0

    for (_, _), files in groups.items():
        if len(files) < 2:
            continue

        groups_found += 1

        # Keep the file with the highest version number
        files_sorted = sorted(files, key=lambda x: x.version)
        file_to_keep = files_sorted[-1]
        files_to_move = files_sorted[:-1]

        for old_file in files_to_move:
            destination = moved_folder / old_file.path.name
            destination = build_unique_destination(destination)

            if dry_run:
                moved_records.append((old_file.path.name, file_to_keep.path.name))
            else:
                moved_folder.mkdir(exist_ok=True)
                shutil.move(str(old_file.path), str(destination))
                moved_records.append((old_file.path.name, file_to_keep.path.name))

    # Write log file
    if moved_records and not dry_run:
        log_path = moved_folder / f"moved_files_{datetime.now():%Y%m%d_%H%M%S}.txt"
        with log_path.open("w", encoding="utf-8") as f:
            f.write(f"Source folder: {folder}\n")
            f.write(f"Execution time: {datetime.now().isoformat(timespec='seconds')}\n")
            f.write(f"Duplicate groups found: {groups_found}\n")
            f.write(f"Files moved: {len(moved_records)}\n")
            f.write("\nMoved files:\n")
            f.write("-" * 80 + "\n")
            for moved_name, kept_name in moved_records:
                f.write(f"MOVED: {moved_name}\n")
                f.write(f"KEPT : {kept_name}\n")
                f.write("\n")

    # Console summary
    if dry_run:
        print(f"[DRY RUN] Folder checked: {folder}")
        print(f"[DRY RUN] Duplicate groups found: {groups_found}")
        print(f"[DRY RUN] Files that would be moved: {len(moved_records)}")
        for moved_name, kept_name in moved_records:
            print(f"Would move: {moved_name}  |  Keep: {kept_name}")
    else:
        print(f"Folder processed: {folder}")
        print(f"Duplicate groups found: {groups_found}")
        print(f"Files moved: {len(moved_records)}")
        if moved_records:
            print(f"Moved files folder: {moved_folder}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Detect duplicate SWOT files that differ only by the final _NN suffix, "
            "keep the highest version, and move the others into a 'moved' folder."
        )
    )
    parser.add_argument(
        "folder",
        nargs="?",
        help="Folder to process. Example: D:\\SWOT\\",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be moved without moving files.",
    )

    args = parser.parse_args()

    if args.folder:
        folder = Path(args.folder)
    else:
        folder = choose_folder_with_dialog()
        if folder is None:
            raise SystemExit(
                "No folder was provided and no folder was selected."
            )

    process_folder(folder, dry_run=args.dry_run)


if __name__ == "__main__":
    main()

# Iban Ameztoy April 2026
