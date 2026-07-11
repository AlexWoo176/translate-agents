import os
import re
from pathlib import Path
from src.core.paths import get_book_root, get_chapter_root, get_phase_dir, get_web_output_root

# Centralized Repair Mapping
REPAIR_MAP = [
    ("Î¼", "μ"),
    ("Ïσ", "σ"),
    ("Ï", "σ"),
    ("Î±", "α"),
    ("â¤", "≤"),
    ("â‰¤", "≤"),
    ("\u00e2\u0089\u00a4", "≤"),
    ("â¥", "≥"),
    ("â‰¥", "≥"),
    ("\u00e2\u0089\u00a5", "≥"),
    ("â ", "≠"),
    ("â‰ ", "≠"),
    ("\u00e2\u0089\u00a0", "≠"),
    ("Â±", "±"),
    ("â€™", "’"),
    ("\u00e2\u0080\u0099", "’"),
    ("â€œ", "“"),
    ("\u00e2\u0080\u009c", "“"),
    ("â€ ", "”"),
    ("â€ ", "”"),
    ("â€\x9d", "”"),
    ("\u00e2\u0080\u009d", "”"),
    ("â€”", "—"),
    ("\u00e2\u0080\u0094", "—"),
    ("â€“", "–"),
    ("\u00e2\u0080\u0093", "–"),
    ("âˆ’", "−"),
    ("\u00e2\u0088\u0092", "−"),
    ("Â¯", "¯"),
    ("Â·", "·"),
    ("\u00c2\u00b7", "·"),
    ("Â¢", "¢"),
    ("\u00c2\u00a2", "¢"),
    ("Â°", "°"),
    ("\u00c2\u00b0", "°"),
    ("Â®", "®"),
    ("\u00c2\u00ae", "®"),
    ("â€²", "′"),
    ("\u00e2\u0080\u00b2", "′"),
    ("â€ƒ", " "),
    ("\u00e2\u0080\u0083", " "),
    ("Âµ", "μ"),
    ("\u00c2\u00b5", "μ"),
    ("âˆ¼", "∼"),
    ("\u00e2\u0088\u00bc", "∼"),
    ("âˆ‘", "∑"),
    ("\u00e2\u0088\u0091", "∑"),
]





def perform_repair(content: str) -> tuple[str, dict]:
    """
    Perform the repair mappings on the given text content.
    Returns (repaired_content, replacement_counts).
    """
    counts = {}
    modified = content
    
    # 1. Apply multi-character mappings
    for bad, good in REPAIR_MAP:
        count = len(re.findall(re.escape(bad), modified))
        if count > 0:
            modified = modified.replace(bad, good)
            counts[f"{bad} -> {good}"] = counts.get(f"{bad} -> {good}", 0) + count
            
    # 2. Context-aware standalone 'â' -> '’' replacement
    # Match 'â' only if not preceded or followed by any standard alphanumeric or Vietnamese character
    standalone_pattern = r'(?<![a-zA-Z0-9À-ỹ])â(?![a-zA-Z0-9À-ỹ])'
    standalone_matches = len(re.findall(standalone_pattern, modified))
    if standalone_matches > 0:
        modified = re.sub(standalone_pattern, '’', modified)
        counts["â -> ’ (standalone)"] = standalone_matches

    # 3. Inject meta charset if missing in HTML documents
    if "charset=" not in modified.lower():
        head_match = re.search(r'(<head[^>]*>)', modified, re.IGNORECASE)
        if head_match:
            pos = head_match.end()
            modified = modified[:pos] + '\n  <meta charset="utf-8">' + modified[pos:]
            counts["Injected <meta charset=\"utf-8\">"] = 1
        else:
            html_match = re.search(r'(<html[^>]*>)', modified, re.IGNORECASE)
            if html_match:
                pos = html_match.end()
                modified = modified[:pos] + '\n<head>\n  <meta charset="utf-8">\n</head>' + modified[pos:]
                counts["Injected <head> and <meta charset=\"utf-8\">"] = 1
        
    return modified, counts


def run(args):
    """
    Execute repair-encoding command.
    """
    book_slug = args.book
    chapter = args.chapter
    file_name = getattr(args, "file", None)
    stage = getattr(args, "stage", None)
    dry_run = getattr(args, "dry_run", False)

    book_root = get_book_root(book_slug)
    if not book_root.is_dir():
        print(f"Error: Book directory '{book_root}' does not exist.")
        return 1

    # Identify directories to search
    target_dirs = []
    if stage:
        target_dirs.append(get_phase_dir(book_slug, chapter, stage))
    else:
        # Standard generated stages
        stages_to_check = ["clean", "prep", "translated", "archive"]
        for stg in stages_to_check:
            dir_path = get_phase_dir(book_slug, chapter, stg)
            if dir_path.is_dir():
                target_dirs.append(dir_path)
        # Also check .html preview stage of that chapter if exists
        preview_chap_dir = book_root / ".html" / f"chapter-{chapter}"
        if preview_chap_dir.is_dir():
            target_dirs.append(preview_chap_dir)
        # Also check web-site folder of that chapter if exists
        web_chap_dir = get_web_output_root() / book_slug / f"chapter-{chapter}"
        if web_chap_dir.is_dir():
            target_dirs.append(web_chap_dir)

    print(f"\n============================================================")
    print(f"  REPAIR ENCODING: BOOK '{book_slug}' CHAPTER '{chapter}'")
    if dry_run:
        print("  (DRY RUN ONLY — NO CHANGES WILL BE WRITTEN)")
    print(f"============================================================\n")

    files_repaired = 0
    total_replacements = 0

    for directory in target_dirs:
        if not directory.is_dir():
            continue
            
        if file_name:
            files_in_dir = [file_name]
        else:
            # Recursively find all html files
            files_in_dir = []
            for root, _, filenames in os.walk(directory):
                for f in filenames:
                    if f.endswith(".html"):
                        files_in_dir.append(os.path.join(root, f))

        for f_path in files_in_dir:
            full_path = Path(f_path) if os.path.isabs(f_path) else directory / f_path
            if not full_path.is_file():
                continue

            try:
                with open(full_path, "r", encoding="utf-8") as f:
                    content = f.read()
            except Exception as e:
                print(f"Error reading {full_path}: {e}")
                continue

            repaired_content, counts = perform_repair(content)
            if counts:
                files_repaired += 1
                rel_path = os.path.relpath(full_path, book_root)
                print(f"File '{rel_path}':")
                for key, val in counts.items():
                    print(f"  - {key}: {val} occurrence(s)")
                    total_replacements += val
                
                if not dry_run:
                    try:
                        with open(full_path, "w", encoding="utf-8") as f:
                            f.write(repaired_content)
                    except Exception as e:
                        print(f"Error writing {full_path}: {e}")

    print("\nSummary:")
    if dry_run:
        print(f"  - [DRY RUN] Proposed repairing {files_repaired} file(s) with {total_replacements} total replacements.")
    else:
        print(f"  - Successfully repaired {files_repaired} file(s) with {total_replacements} total replacements.")

    return 0
