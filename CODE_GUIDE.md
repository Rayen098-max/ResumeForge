# ResumeForge Coding Standards and Guidelines

This document outlines the coding standards, patterns, and style conventions used across the ResumeForge codebase.

---

## Coding Style & Conventions

### 1. Python Style
- **Indentation:** Use 4 spaces for Python scripts.
- **Naming Conventions:**
  - **Functions and Variables:** `snake_case` (e.g., `apply_json_to_docx`, `session_id`, `out_path`).
  - **Global Constants:** `UPPER_SNAKE_CASE` (e.g., `BASE_DIR`, `KNOWN_TEMPLATES`, `W`).
  - **Classes (if any):** `PascalCase`.
- **Imports:** Group standard library imports first, followed by third-party libraries, and then internal modules.
  ```python
  import os
  import sys
  import json
  
  from flask import Flask
  
  from resume_engine import apply_json_to_docx
  ```

### 2. Frontend / HTML / CSS / JavaScript
- **Vanilla Setup:** Do not introduce UI frameworks or Tailwind CSS unless explicitly requested. Rely on semantic HTML5 and Vanilla CSS using the established design system variables.
- **Aesthetic Guidelines:** Use the dark cyberpunk styling defined in [index.html](file:///c:/Users/win%2010/Desktop/ResumeForge/ResumeForge/templates_html/index.html) (e.g., `#0d0d0d` background, `#161616` surface cards, `#c8f060` lime green accent).
- **Naming Conventions:**
  - **CSS Classes:** `kebab-case` (e.g., `.btn-primary`, `.warning-list`, `.preview-panel`).
  - **JS Functions / Variables:** `camelCase` (e.g., `processResume()`, `goToSection()`, `currentSession`).

---

## Key Patterns & Best Practices

### 1. Directly Manipulating DOCX XML
- **Formatting Preservation:** Never write text directly to paragraphs using high-level methods that strip inline style runs. Instead, utilize `set_para_text_preserve_format` or `update_extracurricular_in_place`. These functions modify the inner text node (`w:t`) while preserving the formatting properties (`w:rPr`) of the first run.
- **Index Safety:** When removing elements from the document XML tree, always iterate and remove indices in **reverse order** (descending) to avoid offset shifting.

### 2. Error Handling
- Wrap core engine processes in `try/except` blocks inside routes to return JSON error responses rather than letting Flask throw a 500 HTML stack trace.
  ```python
  try:
      apply_json_to_docx(template_path, out_path, resume_data)
  except Exception as e:
      return jsonify({"error": f"Engine error: {str(e)}"}), 500
  ```

### 3. File Operations
- Keep clean workspace habits. Use `shutil.copy2` to duplicate templates before running edits, and delete session files using the `/api/reset/<session_id>` endpoint.

---

## Do's and Don'ts

- **DO** verify that modifications do not break the single-page limit constraint.
- **DO** preserve Microsoft Word's complex run schemas (e.g. bookmarks, proofing errors, formatting runs) to prevent docx corruption.
- **DON'T** use regex for parsing complex XML. Use the `lxml.etree` module and search with namespaces (`{http://schemas.openxmlformats.org/wordprocessingml/2006/main}`).
- **DON'T** change the order of fields in the `Master Prompt` template, as the backend structure mapping is strictly order-dependent.
