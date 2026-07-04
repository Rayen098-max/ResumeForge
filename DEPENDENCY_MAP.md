# ResumeForge Dependency Map

This document tracks all external, internal, and system-level dependencies required by ResumeForge.

---

## 1. External Python Libraries

These libraries are defined in [requirements.txt](file:///c:/Users/win%2010/Desktop/ResumeForge/ResumeForge/requirements.txt) or installed during setup:

| Dependency | Purpose | Criticality |
|---|---|---|
| **`Flask`** (3.1.0) | Provides the web server routing, API endpoints, static assets serving, and page rendering. | **High** (Core Framework) |
| **`python-docx`** (1.1.2) | Standard library for handling DOCX structure (used primarily for template validation). | **Medium** |
| **`lxml`** (5.3.0) | Performs high-performance parsing and manipulation of the XML files extracted from the DOCX container. | **High** (Core XML Engine) |
| **`docx2pdf`** | Handles programmatic conversion of DOCX files to PDF using native OS APIs. | **Medium** (Optional PDF/Page-count check) |

---

## 2. System & Environment Dependencies

| Dependency | Purpose | Scope / Platform |
|---|---|---|
| **Microsoft Word** | Required by the `docx2pdf` library and the PowerShell COM automation script. | Windows & macOS (Optional, fallback only) |
| **PowerShell** | Executed as a subprocess fallback on Windows to automate Microsoft Word COM operations if `docx2pdf` encounters issues. | Windows (Optional, fallback only) |
| **LibreOffice** | Executed headlessly via CLI to count pages in environments where Microsoft Word is not installed. | Cross-platform / Linux / Headless (Optional, fallback only) |

---

## 3. Internal Modules

| Module Name | Path | Responsibilities | Consumers |
|---|---|---|---|
| **`master_prompt`** | [master_prompt.py](file:///c:/Users/win%2010/Desktop/ResumeForge/ResumeForge/engine/master_prompt.py) | Generates the static instructions/guidelines for ChatGPT/Claude prompting. | `app.py` |
| **`resume_engine`** | [resume_engine.py](file:///c:/Users/win%2010/Desktop/ResumeForge/ResumeForge/engine/resume_engine.py) | Performs XML replacements, structure mapping, page verification, and cut plans. | `app.py` |

---

## 4. Key Artifacts & Data Stores

- **Templates Storage:** [templates_docx/](file:///c:/Users/win%2010/Desktop/ResumeForge/ResumeForge/templates_docx) contains the master templates.
- **Generated Outputs:** [outputs/](file:///c:/Users/win%2010/Desktop/ResumeForge/ResumeForge/outputs) acts as a local cache for custom resumes and PDF generation.
- **In-Memory Store:** The `sessions` dictionary in `app.py` stores the state of active sessions (input JSON, output paths, and warning structures).
