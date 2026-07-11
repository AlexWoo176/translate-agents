$ErrorActionPreference = "Stop"
$env:PYTHONPATH = "d:\OPENSTAX\translate-agents"

8..11 | ForEach-Object {
    $ch = $_
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "PROCESSING CHAPTER $ch" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    
    # 1. Prep chapter
    python -m src.cli.main prep --book introductory-statistics-2e --chapter $ch --force
    
    # 2. Translate key-terms file specifically
    python -m src.cli.main translate --book introductory-statistics-2e --chapter $ch --file "${ch}-key-terms.html" --force --provider gemini-api --model gemma-4-31b-it
    
    # 3. Run English residue repair script on chapter
    python scripts/repair_english_residue.py --book introductory-statistics-2e --chapter $ch --model gemma-4-31b-it
    
    # 4. Archive chapter
    python -m src.cli.main archive --book introductory-statistics-2e --chapter $ch --force
}
