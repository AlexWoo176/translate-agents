import os
import json
from datetime import datetime, timezone
from pathlib import Path
from src.core.paths import get_book_root, get_chapter_root, get_chapter_folder_name

def normalize_chapter_key(chapter) -> str:
    """
    Ensure chapter key is in 'chapter-N' format (keeping _book-level as is).
    """
    return get_chapter_folder_name(chapter)

def update_status(book_slug: str, chapter=None, phase: str = None, status_str: str = "completed", error_msg: str = None, extra_metadata: dict = None):
    """
    Safely update status.json and chapter.json for a book and chapter pipeline phase.
    """
    book_root = get_book_root(book_slug)
    status_file = book_root / "status.json"
    
    # 1. Update status at book level (with or without chapter)
    status_data = {}
    if status_file.is_file():
        try:
            with open(status_file, "r", encoding="utf-8") as f:
                status_data = json.load(f)
        except Exception:
            pass

    if "book" not in status_data:
        status_data["book"] = book_slug
    if "chapters" not in status_data:
        status_data["chapters"] = {}

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    if chapter is not None:
        chapter_key = normalize_chapter_key(chapter)
        chapter_root = get_chapter_root(book_slug, chapter)
        chapter_json = chapter_root / "chapter.json"

        # Update chapter.json
        chapter_data = {}
        if chapter_json.is_file():
            try:
                with open(chapter_json, "r", encoding="utf-8") as f:
                    chapter_data = json.load(f)
            except Exception:
                pass

        if "book" not in chapter_data:
            chapter_data["book"] = book_slug
        if "chapter" not in chapter_data:
            try:
                chapter_data["chapter"] = int(str(chapter).replace("chapter-", ""))
            except ValueError:
                chapter_data["chapter"] = str(chapter).replace("chapter-", "")

        # Set phase details
        if phase:
            if "phases" not in chapter_data:
                chapter_data["phases"] = {}
            if phase not in chapter_data["phases"]:
                chapter_data["phases"][phase] = {}

            chapter_data["phases"][phase]["status"] = status_str
            chapter_data["phases"][phase]["timestamp"] = timestamp
            
            if error_msg:
                chapter_data["phases"][phase]["error"] = error_msg
            else:
                chapter_data["phases"][phase].pop("error", None)

            if extra_metadata:
                chapter_data["phases"][phase].update(extra_metadata)

            # Consolidate chapter status based on this phase
            if phase == "translate":
                if status_str == "translating":
                    chapter_data["status"] = "translating"
                elif status_str == "completed":
                    chapter_data["status"] = "translated"
                elif status_str == "ready":
                    chapter_data["status"] = "translation_ready"
                elif status_str in ["failed", "blocked"]:
                    chapter_data["status"] = "translation_blocked"
                else:
                    chapter_data["status"] = f"{phase}_{status_str}"
            else:
                chapter_data["status"] = f"{phase}_{status_str}"

        # Write chapter.json
        try:
            with open(chapter_json, "w", encoding="utf-8") as f:
                json.dump(chapter_data, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not write chapter.json: {e}")

        # Update book level chapters dict
        status_data["chapters"][chapter_key] = {
            "status": chapter_data.get("status", "unknown"),
            "last_updated": timestamp
        }
    
    elif phase == "build":
        # Book-level build preview phase status
        if "build" not in status_data:
            status_data["build"] = {}
        status_data["build"]["status"] = status_str
        status_data["build"]["timestamp"] = timestamp
        
        if error_msg:
            status_data["build"]["error"] = error_msg
        else:
            status_data["build"].pop("error", None)
            
        if extra_metadata:
            status_data["build"].update(extra_metadata)
            
        status_data["status"] = f"build_{status_str}"

    # Write status.json
    try:
        with open(status_file, "w", encoding="utf-8") as f:
            json.dump(status_data, f, indent=2)
    except Exception as e:
        print(f"Warning: Could not write status.json: {e}")
        
    sync_tasks_markdown(book_slug)
    return True


def sync_tasks_markdown(book_slug: str):
    """
    Automatically synchronize tasks.md checklist based on status.json and folder content.
    """
    try:
        book_root = get_book_root(book_slug)
        status_file = book_root / "status.json"
        tasks_file = book_root / "tasks.md"
        
        # Load book status.json
        status_data = {}
        if status_file.is_file():
            with open(status_file, "r", encoding="utf-8") as f:
                status_data = json.load(f)
                
        # Find all chapters
        chapters = []
        for d in os.listdir(book_root):
            if d.startswith("chapter-") and (book_root / d).is_dir():
                chap_id = d.replace("chapter-", "")
                chapters.append((d, chap_id))
                
        # Sort chapters numerically
        def get_sort_key(item):
            try:
                return int(item[1])
            except ValueError:
                return 999
        chapters.sort(key=get_sort_key)
        
        lines = [
            f"# Project Tasks: {book_slug}",
            "",
            "This file tracks the translation progress of each chapter in the textbook.",
            "",
            "## Book Summary Progress",
        ]
        
        workspace_init = "x"
        baseline_ver = "x" if all(
            status_data.get("chapters", {}).get(f"chapter-{i}", {}).get("status") == "archive_completed"
            for i in range(1, 9)
        ) else " "
        
        total_chaps = len(chapters)
        completed_chaps = sum(
            1 for c_dir, _ in chapters
            if status_data.get("chapters", {}).get(c_dir, {}).get("status") == "archive_completed"
        )
        
        trans_prog = "/" if (completed_chaps > 0 and completed_chaps < total_chaps) else ("x" if completed_chaps == total_chaps else " ")
        
        lines.append(f"- [{workspace_init}] Initialize workspace")
        lines.append(f"- [{baseline_ver}] Complete chapters 1–8 baseline verification")
        lines.append(f"- [{trans_prog}] Complete chapters translation ({completed_chaps}/{total_chaps} chapters archived)")
        lines.append("")
        lines.append("## Chapter Progress Checklist")
        lines.append("")
        
        for c_dir, chap_id in chapters:
            chapter_root = book_root / c_dir
            chapter_json = chapter_root / "chapter.json"
            
            chapter_data = {}
            if chapter_json.is_file():
                try:
                    with open(chapter_json, "r", encoding="utf-8") as f:
                        chapter_data = json.load(f)
                except Exception:
                    pass
            
            # Scraped check: if 01-raw contains at least one HTML file
            raw_dir = chapter_root / "01-raw"
            has_raw = "x" if (raw_dir.is_dir() and any(f.endswith(".html") for f in os.listdir(raw_dir))) else " "
            
            # Cleaned check: if 02-clean contains at least one HTML file
            clean_dir = chapter_root / "02-clean"
            has_clean = "x" if (clean_dir.is_dir() and any(f.endswith(".html") for f in os.listdir(clean_dir))) else " "
            
            # Prep check
            prep_ok = "x" if chapter_data.get("phases", {}).get("prep", {}).get("status") == "completed" else " "
            
            # Translate check
            trans_ok = "x" if chapter_data.get("phases", {}).get("translate", {}).get("status") == "completed" else " "
            
            # QA check
            qa_ok = " "
            review_status = chapter_data.get("phases", {}).get("review", {})
            if chapter_data.get("qa", {}).get("integrity") == "passed" and chapter_data.get("qa", {}).get("review_gate") == "passed":
                qa_ok = "x"
            elif chapter_data.get("qa", {}).get("review_gate_forced") is True:
                qa_ok = "x"
            elif chapter_data.get("status") == "archive_completed":
                qa_ok = "x"
            elif review_status.get("status") == "failed":
                qa_ok = "/"
                
            # Archive check
            archive_ok = "x" if chapter_data.get("phases", {}).get("archive", {}).get("status") == "completed" else " "
            
            # Build check: book status build completed
            build_ok = "x" if status_data.get("build", {}).get("status") == "completed" else " "
            
            # Resolve chapter title
            title_en = chapter_data.get("title_en") or ""
            title_suffix = f": {title_en}" if title_en else ""
            
            lines.append(f"### Chapter {chap_id}{title_suffix}")
            lines.append(f"- [{has_raw}] Scrape raw HTML")
            lines.append(f"- [{has_clean}] Cleanup HTML and download assets")
            lines.append(f"- [{prep_ok}] Prepare bilingual templates")
            lines.append(f"- [{trans_ok}] Execute translation")
            lines.append(f"- [{qa_ok}] Run QA verification")
            lines.append(f"- [{archive_ok}] Archive translated files")
            lines.append(f"- [{build_ok}] Build preview")
            lines.append("")
            
        with open(tasks_file, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
            
    except Exception as e:
        print(f"Warning: Could not sync tasks.md: {e}")
