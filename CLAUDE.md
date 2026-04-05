# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Project Is

**TR_book_read_tool** is a PySide6 desktop application for academic PDF analysis. It orchestrates a multi-step pipeline:

1. Upload PDF → extract bookmarks → split into chapter PDFs (`pdf_processor.py`)
2. Submit chapter PDFs to the MinerU OCR/parsing API → poll until done → download ZIP results (`api_handler.py`)
3. Convert MinerU JSON output to Markdown (`json_to_markdown.py`)
4. Send Markdown chapters to a configurable LLM (DeepSeek or Gemini via Zenmux proxy) for analysis (`api_handler.py`)
5. Aggregate LLM results into a Word (.docx) report (`report_generator.py`)

## Running and Building

```bash
# Install dependencies (uses uv)
uv sync

# Run the application
python main.py

# Build standalone executable
python build.py
# Internally runs: uv run --group build pyinstaller --clean build_config.spec
# Post-build: copies config.ini and creates data/ directory next to the exe
```

Dependencies: `PySide6`, `pypdf`, `requests`, `python-docx` (see `pyproject.toml`).

## Architecture

### Data Layout (runtime)

```
data/
└── <Book Group>/
    └── <Book Title>/
        ├── original.pdf
        ├── metadata.json          # book status tracking
        ├── chapters_pdf/          # split chapter PDFs
        ├── MinerU_json/           # raw MinerU ZIP/JSON output
        ├── chapters_markdown/     # converted Markdown per chapter
        └── LLM_result/            # per-chapter LLM analysis Markdown
```

### Key Modules

| Module | Responsibility |
|---|---|
| `core/api_handler.py` | `ConfigManager` (config.ini), `LLMAPI` (DeepSeek/Gemini with retry), `MinerUAPI` (REST polling), `ContentExtractor` (ZIP download), `APIHandler` (pipeline orchestrator) |
| `core/book_manager.py` | Book group CRUD, PDF upload, metadata.json read/write |
| `core/pdf_processor.py` | Extract PDF bookmarks, split PDF by chapter page ranges |
| `core/json_to_markdown.py` | Convert MinerU JSON → Markdown with page annotations |
| `core/report_generator.py` | Aggregate LLM Markdown files → Word report |
| `ui/main_window.py` | Main window (1200+ lines); all worker threads live here |
| `ui/settings_dialog.py` | Settings dialog for API keys and prompts |
| `config.ini` | All configuration: API keys, base URLs, LLM system prompt, output path |

### Worker Threads (all in `ui/main_window.py`)

The UI uses QThread workers to keep the GUI responsive:
- `MinerUWorker` — submits chapters to MinerU, polls for completion
- `LLMAnalysisWorker` — sends Markdown chapters to LLM concurrently (respects `max_concurrent` from config)
- `ReportGenerationWorker` — generates Word report
- `FullProcessWorker` — full pipeline orchestrator, emits progress signals

### Configuration (`config.ini`)

Sections: `[MinerU]`, `[DeepSeek]`, `[Gemini]`, `[Zenmux]`, `[LLM]`, `[General]`.  
`[LLM]` contains `system_prompt` (multi-line), `max_concurrent`, and which provider to use.  
`[General]` has `report_output_path`.  
`ConfigManager` in `api_handler.py` is the single reader for this file.
