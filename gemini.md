# Agent Instructions for Morphoneme

This document contains critical constraints and instructions for AI agents (e.g. Gemini / Antigravity) working on the `morphoneme` project.

## Development & Publishing Constraints

1. **Do NOT automatically publish to PyPI**:
   - Do **NOT** build or upload package distributions (`twine upload`) to PyPI automatically upon modifying the code.
   - Publishing to PyPI should only be performed when the user explicitly requests it.

2. **Excluded Files**:
   - The following local files are excluded in `.gitignore` and must **never** be committed to Git or pushed to GitHub:
     - `scripts/fetch_frequencies.py`
     - `scripts/fetch_pronunciations.py`
     - `scripts/frequency_stats.py`
     - `词频分析阈值.txt`
     - `data/*.tmp_tsv` (temporary TSV files)
