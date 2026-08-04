from pathlib import Path

# Dossier "results" (où se trouve ce script)
ROOT = Path(__file__).resolve().parent

deleted = 0

for extension in ("*.html", "*.json"):
    for file in ROOT.rglob(extension):
        file.unlink()
        print(f"Deleted: {file.relative_to(ROOT)}")
        deleted += 1

