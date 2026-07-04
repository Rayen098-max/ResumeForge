"""
ResumeForge Engine
Surgically edits resume DOCX files by manipulating XML directly.
Preserves all formatting — fonts, sizes, borders, spacing — untouched.
"""

import zipfile, shutil, os, copy, re, subprocess
from lxml import etree

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


# ─────────────────────────────────────────────────────────────
# LOW-LEVEL HELPERS
# ─────────────────────────────────────────────────────────────

def get_text(elem):
    return "".join(t.text or "" for t in elem.iter(f"{{{W}}}t"))

def _run_is_bold(run):
    rpr = run.find(f"{{{W}}}rPr")
    return rpr is not None and rpr.find(f"{{{W}}}b") is not None

def _get_style(para):
    pPr = para.find(f"{{{W}}}pPr")
    if pPr is not None:
        pStyle = pPr.find(f"{{{W}}}pStyle")
        if pStyle is not None:
            return pStyle.get(f"{{{W}}}val", "Normal")
    return "Normal"

def _get_bold_text(para):
    return "".join(get_text(r) for r in para.findall(f"{{{W}}}r") if _run_is_bold(r))

def _get_non_bold_text(para):
    return "".join(get_text(r) for r in para.findall(f"{{{W}}}r") if not _run_is_bold(r))

def set_para_text_preserve_format(para, new_text):
    """Replace all runs with one consolidated run. Keeps first run's rPr (format)."""
    runs = para.findall(f"{{{W}}}r")
    for tag in [f"{{{W}}}proofErr", f"{{{W}}}bookmarkStart", f"{{{W}}}bookmarkEnd"]:
        for elem in para.findall(tag):
            para.remove(elem)
    rpr = None
    if runs:
        rpr = runs[0].find(f"{{{W}}}rPr")
        for r in runs:
            para.remove(r)
    new_run = etree.SubElement(para, f"{{{W}}}r")
    if rpr is not None:
        new_run.insert(0, copy.deepcopy(rpr))
    t_elem = etree.SubElement(new_run, f"{{{W}}}t")
    t_elem.text = new_text
    if new_text and (new_text[0] == " " or new_text[-1] == " "):
        t_elem.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")

def set_para_text_force_normal(para, new_text):
    """Like set_para_text_preserve_format but strips bold — used for extracurriculars."""
    runs = para.findall(f"{{{W}}}r")
    if not runs:
        return
    rpr = runs[0].find(f"{{{W}}}rPr")
    rpr_copy = copy.deepcopy(rpr) if rpr is not None else None
    if rpr_copy is not None:
        for bold_tag in [f"{{{W}}}b", f"{{{W}}}bCs"]:
            b = rpr_copy.find(bold_tag)
            if b is not None:
                rpr_copy.remove(b)
    for r in runs:
        para.remove(r)
    for tag in [f"{{{W}}}proofErr", f"{{{W}}}bookmarkStart", f"{{{W}}}bookmarkEnd"]:
        for elem in para.findall(tag):
            para.remove(elem)
    new_run = etree.SubElement(para, f"{{{W}}}r")
    if rpr_copy is not None:
        new_run.insert(0, rpr_copy)
    t_elem = etree.SubElement(new_run, f"{{{W}}}t")
    t_elem.text = new_text
    if new_text and (new_text[0] == " " or new_text[-1] == " "):
        t_elem.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")

def update_extracurricular_in_place(para, new_text):
    """
    Updates extracurricular text while preserving ALL original run structure.
    Strips bold but keeps character borders and every other run element intact.
    Text goes into first run; remaining runs are emptied.
    """
    runs = para.findall(f"{{{W}}}r")
    if not runs:
        return
    for r in runs:
        rpr = r.find(f"{{{W}}}rPr")
        if rpr is not None:
            for bold_tag in [f"{{{W}}}b", f"{{{W}}}bCs"]:
                b = rpr.find(bold_tag)
                if b is not None:
                    rpr.remove(b)
    first_t = runs[0].find(f"{{{W}}}t")
    if first_t is None:
        first_t = etree.SubElement(runs[0], f"{{{W}}}t")
    first_t.text = new_text
    if new_text and (new_text[0] == " " or new_text[-1] == " "):
        first_t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    for r in runs[1:]:
        for t in r.findall(f"{{{W}}}t"):
            t.text = ""

def set_competency_row(para, label, skills_list):
    """Edit competency row: [BOLD: label + ': '] [NORMAL: skill1, skill2, ...]"""
    runs = para.findall(f"{{{W}}}r")
    if not runs:
        return
    bold_runs = [r for r in runs if _run_is_bold(r)]
    non_bold_runs = [r for r in runs if not _run_is_bold(r)]
    bold_rpr = copy.deepcopy(bold_runs[0].find(f"{{{W}}}rPr")) if bold_runs else None
    normal_rpr = copy.deepcopy(non_bold_runs[0].find(f"{{{W}}}rPr")) if non_bold_runs else None
    for r in runs:
        para.remove(r)
    for elem in para.findall(f"{{{W}}}proofErr"):
        para.remove(elem)
    br = etree.SubElement(para, f"{{{W}}}r")
    if bold_rpr is not None:
        br.insert(0, bold_rpr)
    bt = etree.SubElement(br, f"{{{W}}}t")
    bt.text = f"{label}: "
    bt.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    nr = etree.SubElement(para, f"{{{W}}}r")
    if normal_rpr is not None:
        nr.insert(0, normal_rpr)
    nt = etree.SubElement(nr, f"{{{W}}}t")
    nt.text = ", ".join(skills_list)

def update_cert_title_para(para, cert_json):
    """Update cert title para: [BOLD: name] [NORMAL: year]. Preserves run formatting."""
    runs = para.findall(f"{{{W}}}r")
    if not runs:
        return
    bold_runs = [r for r in runs if _run_is_bold(r)]
    non_bold_runs = [r for r in runs if not _run_is_bold(r)]
    bold_rpr = copy.deepcopy(bold_runs[0].find(f"{{{W}}}rPr")) if bold_runs else None
    non_bold_rpr = copy.deepcopy(non_bold_runs[0].find(f"{{{W}}}rPr")) if non_bold_runs else None
    for r in runs:
        para.remove(r)
    br = etree.SubElement(para, f"{{{W}}}r")
    if bold_rpr is not None:
        br.insert(0, bold_rpr)
    bt = etree.SubElement(br, f"{{{W}}}t")
    bt.text = cert_json.get("name", "")
    tab_r = etree.SubElement(para, f"{{{W}}}r")
    etree.SubElement(tab_r, f"{{{W}}}tab")
    nr = etree.SubElement(para, f"{{{W}}}r")
    if non_bold_rpr is not None:
        nr.insert(0, non_bold_rpr)
    nt = etree.SubElement(nr, f"{{{W}}}t")
    nt.text = cert_json.get("year", "")

def update_table_cert_row(body, cert_json):
    """Update cert slot 0 in the education table (table row 4): name, provider, year."""
    children = list(body)
    table = None
    for child in children:
        tag = child.tag.split("}")[1] if "}" in child.tag else child.tag
        if tag == "tbl":
            table = child
            break
    if table is None:
        return
    rows = table.findall(f"{{{W}}}tr")
    if len(rows) < 5:
        return
    cert_row = rows[4]
    cells = cert_row.findall(f"{{{W}}}tc")
    if not cells:
        return
    # Cell 0: cert name (para 0) + provider (para 1)
    cell0_paras = cells[0].findall(f"{{{W}}}p")
    if len(cell0_paras) >= 1:
        set_para_text_preserve_format(cell0_paras[0], cert_json.get("name", ""))
    if len(cell0_paras) >= 2:
        set_para_text_preserve_format(cell0_paras[1], cert_json.get("provider", ""))
    # Cell 1: year
    if len(cells) >= 2:
        cell1_paras = cells[1].findall(f"{{{W}}}p")
        if cell1_paras:
            set_para_text_preserve_format(cell1_paras[0], cert_json.get("year", ""))

def remove_body_children(body, indices):
    """Remove body children at given indices. Safe reverse-order removal."""
    children = list(body)
    for i in sorted(set(indices), reverse=True):
        if i < len(children):
            body.remove(children[i])


# ─────────────────────────────────────────────────────────────
# DOCUMENT STRUCTURE MAPPER
# ─────────────────────────────────────────────────────────────

def map_document_structure(body):
    """
    Maps indices of all editable sections in the document body.
    Works for all templates with same section order.
    """
    children = list(body)
    structure = {
        "title_line": None,
        "profile_summary": None,
        "competency_rows": [],
        "cert_blocks": [],
        "project_blocks": [],
        "extracurricular_start": None,
        "extracurricular_items": [],
        "languages_idx": None,
        "continuation_paragraphs": [],
    }
    in_projects = False
    in_extracurriculars = False
    current_project = None

    for i, child in enumerate(children):
        tag = child.tag.split("}")[1] if "}" in child.tag else child.tag
        text = get_text(child).strip() if tag == "p" else ""

        if i == 1:
            structure["title_line"] = i

        elif tag == "p" and _get_style(child) == "BodyText" and structure["profile_summary"] is None:
            if len(text) > 10:
                structure["profile_summary"] = i

        elif tag == "p" and _get_style(child) == "Normal" and _is_competency_row(child):
            structure["competency_rows"].append(i)

        elif tag == "p" and _get_style(child) == "Heading2" and "Project" in text:
            in_projects = True
            in_extracurriculars = False

        elif tag == "p" and _get_style(child) == "Heading2" and "Extracurricular" in text:
            in_projects = False
            in_extracurriculars = True
            structure["extracurricular_start"] = i

        elif tag == "p" and _get_style(child) == "Heading2" and "Language" in text:
            in_projects = False
            in_extracurriculars = False
            structure["languages_idx"] = i

        elif tag == "p" and not in_projects and not in_extracurriculars \
                and structure["extracurricular_start"] is None \
                and _is_cert_title(child):
            structure["cert_blocks"].append({
                "title_idx": i,
                "provider_idx": i + 1,
                "desc_idx": i + 2,
                "name": _get_bold_text(child).strip(),
                "year": _get_non_bold_text(child).strip(),
            })

        elif tag == "p" and in_projects and _is_project_title(child):
            current_project = {
                "title_idx": i,
                "bullet_indices": [],
                "name": _get_bold_text(child).strip(),
            }
            structure["project_blocks"].append(current_project)

        elif tag == "p" and in_projects and _get_style(child) == "ListParagraph":
            pPr = child.find(f"{{{W}}}pPr")
            has_num = False
            if pPr is not None and pPr.find(f"{{{W}}}numPr") is not None:
                has_num = True
            if has_num:
                if current_project is not None:
                    current_project["bullet_indices"].append(i)
            else:
                structure["continuation_paragraphs"].append(i)

        elif tag == "p" and in_extracurriculars and _get_style(child) != "Heading2":
            if len(text) > 20 and ("-" in text or "—" in text or "–" in text):
                structure["extracurricular_items"].append(i)

    return structure


def _is_competency_row(para):
    full_text = get_text(para)
    if ":" not in full_text:
        return False
    runs = para.findall(f"{{{W}}}r")
    return any(_run_is_bold(r) for r in runs) and len(full_text.strip()) > 5

def _is_cert_title(para):
    """Cert/project title: Normal style, has bold runs (name) + short non-bold (year)."""
    if _get_style(para) != "Normal":
        return False
    bold_text = _get_bold_text(para).strip()
    non_bold = _get_non_bold_text(para).strip()
    if len(bold_text) < 5:
        return False
    # Year can be "2024", "2024-2025", "2026" — at least 4 chars, at most 15
    return 4 <= len(non_bold) <= 15 and any(c.isdigit() for c in non_bold)

def _is_project_title(para):
    return _is_cert_title(para)

def find_table_cert_desc(body):
    """Find the ListParagraph description bullet for cert slot 0 (right after the table)."""
    children = list(body)
    for i, child in enumerate(children):
        tag = child.tag.split("}")[1] if "}" in child.tag else child.tag
        if tag == "tbl":
            for j in range(i + 1, min(i + 5, len(children))):
                if _get_style(children[j]) == "ListParagraph":
                    return j
            break
    return None


# ─────────────────────────────────────────────────────────────
# MAIN EDIT FUNCTION
# ─────────────────────────────────────────────────────────────

def apply_json_to_docx(template_path, output_path, json_data):
    """
    Apply all JSON edits to a copy of the template DOCX.
    - Unused cert slots are removed immediately (no warning needed).
    - No cuts applied here — cuts handled separately by get_cut_plan.
    Returns [] always.
    """
    shutil.copy2(template_path, output_path)

    with zipfile.ZipFile(output_path, "r") as z:
        doc_xml = z.read("word/document.xml")

    tree = etree.fromstring(doc_xml)
    body = tree.find(f"{{{W}}}body")
    children = list(body)
    structure = map_document_structure(body)
    immediate_remove = []

    # ── 1. TITLE LINE ────────────────────────────────────────
    if json_data.get("title_line") and structure["title_line"] is not None:
        set_para_text_preserve_format(children[structure["title_line"]], json_data["title_line"])

    # ── 2. PROFILE SUMMARY ───────────────────────────────────
    if json_data.get("profile_summary") and structure["profile_summary"] is not None:
        set_para_text_preserve_format(children[structure["profile_summary"]], json_data["profile_summary"])

    # ── 3. CORE COMPETENCIES ─────────────────────────────────
    comp = json_data.get("core_competencies", {})
    row_keys = [("row1_label", "row1_skills"), ("row2_label", "row2_skills"), ("row3_label", "row3_skills")]
    for idx, (lk, sk) in enumerate(row_keys):
        if idx < len(structure["competency_rows"]):
            label = comp.get(lk, "")
            skills = comp.get(sk, [])
            if label and skills:
                set_competency_row(children[structure["competency_rows"][idx]], label, skills)

    # ── 4. CERTIFICATIONS (fully dynamic) ────────────────────
    # AI picks exactly 4 from pool. Each cert has name, provider, year, description.
    # Unused slots or empty slots (manually cleared by user) are removed immediately.
    cert_data = json_data.get("certifications", [])
    cert_data = [c for c in cert_data if c.get("name", "").strip()]
    cert_blocks = structure["cert_blocks"]   # slots 1-3 outside table
    table_cert_desc_idx = find_table_cert_desc(body)

    # Slot 0 (lives in table + description outside)
    if len(cert_data) >= 1:
        update_table_cert_row(body, cert_data[0])
        if table_cert_desc_idx is not None and cert_data[0].get("description"):
            set_para_text_preserve_format(children[table_cert_desc_idx], cert_data[0]["description"])

    # Slots 1, 2, 3 (outside table)
    for slot_idx, block in enumerate(cert_blocks):
        cert_idx = slot_idx + 1
        if cert_idx < len(cert_data):
            c = cert_data[cert_idx]
            update_cert_title_para(children[block["title_idx"]], c)
            set_para_text_preserve_format(children[block["provider_idx"]], c.get("provider", ""))
            if c.get("description"):
                set_para_text_preserve_format(children[block["desc_idx"]], c["description"])
        else:
            # No cert for this slot → remove immediately
            immediate_remove.extend([block["title_idx"], block["provider_idx"], block["desc_idx"]])

    # ── 5. PROJECTS ───────────────────────────────────────────
    # Irrelevant projects (include: false) or empty projects (name cleared) are removed.
    # Any cleared/empty bullets are removed to fit on one page.
    proj_data = json_data.get("projects", [])
    for pi, proj_json in enumerate(proj_data):
        if pi >= len(structure["project_blocks"]):
            break
        block = structure["project_blocks"][pi]
        
        name = proj_json.get("name", "").strip()
        include = proj_json.get("include", True)
        
        if not name or not include:
            immediate_remove.append(block["title_idx"])
            immediate_remove.extend(block["bullet_indices"])
        else:
            new_bullets = proj_json.get("bullets", [])
            active_bullets = [b.strip() for b in new_bullets if b.strip()]
            for bi, bullet_idx in enumerate(block["bullet_indices"]):
                if bi < len(active_bullets):
                    set_para_text_preserve_format(children[bullet_idx], active_bullets[bi])
                else:
                    immediate_remove.append(bullet_idx)

    # ── Fix Extracurricular heading spacing (restores bottom line) ────
    if structure["extracurricular_start"] is not None:
        h_para = children[structure["extracurricular_start"]]
        h_pPr = h_para.find(f"{{{W}}}pPr")
        if h_pPr is not None and h_pPr.find(f"{{{W}}}spacing") is None:
            sp = etree.Element(f"{{{W}}}spacing")
            sp.set(f"{{{W}}}before", "123")
            pst = h_pPr.find(f"{{{W}}}pStyle")
            if pst is not None:
                pst.addnext(sp)
            else:
                h_pPr.insert(0, sp)

    # ── 6. EXTRACURRICULARS ───────────────────────────────────
    # Empty extracurricular lines are purged immediately.
    extrac_data = json_data.get("extracurriculars", [])[:3]
    extrac_data = [e for e in extrac_data if e.get("full_line", "").strip()]
    lang_boundary = structure.get("languages_idx", len(children))
    for ei, item_idx in enumerate(structure["extracurricular_items"]):
        if ei < len(extrac_data):
            line = extrac_data[ei].get("full_line", "").strip()
            if line:
                if ei == 0:
                    update_extracurricular_in_place(children[item_idx], line)
                else:
                    set_para_text_force_normal(children[item_idx], line)
        else:
            # Never remove a paragraph adjacent to Languages heading — protects border/spacer lines
            if item_idx < lang_boundary:
                immediate_remove.append(item_idx)

    # ── 7. REMOVE LIST CONTINUATION PARAGRAPHS ─────────────────
    if "continuation_paragraphs" in structure:
        immediate_remove.extend(structure["continuation_paragraphs"])

    # ── Apply immediate removals (unused/cleared/continuation slots) ──
    if immediate_remove:
        remove_body_children(body, immediate_remove)

    # ── Repack DOCX ───────────────────────────────────────────
    new_xml = etree.tostring(tree, xml_declaration=True, encoding="UTF-8", standalone=True)
    tmp = output_path + ".tmp"
    with zipfile.ZipFile(output_path, "r") as zin:
        with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                if item.filename == "word/document.xml":
                    zout.writestr(item, new_xml)
                else:
                    zout.writestr(item, zin.read(item.filename))
    os.replace(tmp, output_path)
    return []


# ─────────────────────────────────────────────────────────────
# CONFIRMED DELETIONS (after user approves warnings)
# ─────────────────────────────────────────────────────────────

def apply_confirmed_deletions(output_path, deletion_indices):
    """Remove specific body children that the user confirmed should be cut."""
    if not deletion_indices:
        return
    with zipfile.ZipFile(output_path, "r") as z:
        doc_xml = z.read("word/document.xml")
    tree = etree.fromstring(doc_xml)
    body = tree.find(f"{{{W}}}body")
    children = list(body)
    for idx in sorted(set(deletion_indices), reverse=True):
        if idx < len(children):
            body.remove(children[idx])
    new_xml = etree.tostring(tree, xml_declaration=True, encoding="UTF-8", standalone=True)
    tmp = output_path + ".tmp"
    with zipfile.ZipFile(output_path, "r") as zin:
        with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                if item.filename == "word/document.xml":
                    zout.writestr(item, new_xml)
                else:
                    zout.writestr(item, zin.read(item.filename))
    os.replace(tmp, output_path)


# ─────────────────────────────────────────────────────────────
# PDF CONVERSION & PAGE COUNT CHECK
# ─────────────────────────────────────────────────────────────

def convert_docx_to_pdf(docx_path, pdf_path):
    """
    Unified PDF converter. Tries docx2pdf, PowerShell + Word COM, and LibreOffice Headless.
    Returns True if successful, False otherwise.
    """
    if os.path.exists(pdf_path):
        try:
            os.remove(pdf_path)
        except Exception:
            pass

    # Method 1: docx2pdf
    try:
        from docx2pdf import convert
        convert(docx_path, pdf_path)
        if os.path.exists(pdf_path):
            return True
    except Exception:
        pass

    # Method 2: PowerShell + Word COM (reliable on Windows with Word installed)
    try:
        abs_docx = os.path.abspath(docx_path).replace("\\", "\\\\")
        abs_pdf  = os.path.abspath(pdf_path).replace("\\", "\\\\")
        ps_cmd = (
            f'$w = New-Object -ComObject Word.Application; '
            f'$w.Visible = $false; '
            f'$d = $w.Documents.Open("{abs_docx}"); '
            f'$d.SaveAs2("{abs_pdf}", 17); '
            f'$d.Close(); '
            f'$w.Quit()'
        )
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_cmd],
            check=True, timeout=60, capture_output=True
        )
        if os.path.exists(pdf_path):
            return True
    except Exception:
        pass

    # Method 3: LibreOffice headless
    try:
        outputs_dir = os.path.dirname(docx_path)
        # LibreOffice outputs to the same dir and matches docx file name with .pdf
        subprocess.run(
            ["libreoffice", "--headless", "--convert-to", "pdf",
             "--outdir", outputs_dir, docx_path],
            check=True, timeout=30, capture_output=True
        )
        expected_pdf = docx_path.replace(".docx", ".pdf")
        if os.path.exists(expected_pdf):
            if expected_pdf != pdf_path:
                shutil.move(expected_pdf, pdf_path)
            return True
    except Exception:
        pass

    return False


def check_page_count(docx_path):
    """
    Convert DOCX to PDF and return number of pages using pypdf.
    Returns 1 if conversion fails (safe default = assume it fits).
    """
    pdf_path = docx_path.replace(".docx", "_pagecheck.pdf")

    if not convert_docx_to_pdf(docx_path, pdf_path):
        return 1

    try:
        from pypdf import PdfReader
        reader = PdfReader(pdf_path)
        pages = len(reader.pages)
    except Exception:
        pages = 1

    try:
        os.remove(pdf_path)
    except Exception:
        pass

    return max(1, pages)



# ─────────────────────────────────────────────────────────────
# CUT PLAN BUILDER (only triggered if page overflows)
# ─────────────────────────────────────────────────────────────

def get_cut_plan(output_path, json_data):
    """
    Reads the already-edited DOCX and builds an ordered list of suggested cuts.
    Cuts are minimum necessary — irrelevant items cut first.
    Note: cert slot removal is already done in apply_json_to_docx (no cert cuts here).
    """
    with zipfile.ZipFile(output_path, "r") as z:
        doc_xml = z.read("word/document.xml")
    tree = etree.fromstring(doc_xml)
    body = tree.find(f"{{{W}}}body")
    structure = map_document_structure(body)
    cut_plan = []
    proj_data = json_data.get("projects", [])

    # ── Pass 1: Irrelevant projects (include:false) ───────────
    # Trim last bullet first, then offer full project removal
    for pi, proj_json in enumerate(proj_data):
        if proj_json.get("include", True):
            continue
        if pi >= len(structure["project_blocks"]):
            continue
        block = structure["project_blocks"][pi]
        if len(block["bullet_indices"]) > 1:
            cut_plan.append({
                "type": "bullet_trim",
                "priority": "irrelevant",
                "name": block["name"],
                "idx": block["bullet_indices"][-1],
                "msg": f"Trim last bullet from '{block['name']}' (irrelevant to role)"
            })
        cut_plan.append({
            "type": "project_remove",
            "priority": "irrelevant",
            "name": block["name"],
            "indices": [block["title_idx"]] + block["bullet_indices"],
            "msg": f"Remove entire project: '{block['name']}' (irrelevant to role)"
        })

    # ── Pass 2: Relevant projects — trim last bullet ──────────
    for pi, proj_json in enumerate(proj_data):
        if not proj_json.get("include", True):
            continue
        if pi >= len(structure["project_blocks"]):
            continue
        block = structure["project_blocks"][pi]
        if len(block["bullet_indices"]) > 1:
            cut_plan.append({
                "type": "bullet_trim",
                "priority": "relevant",
                "name": block["name"],
                "idx": block["bullet_indices"][-1],
                "msg": f"Trim last bullet from '{block['name']}'"
            })

    # ── Pass 3: Profile summary trim ─────────────────────────
    if structure["profile_summary"] is not None:
        cut_plan.append({
            "type": "summary_trim",
            "priority": "relevant",
            "name": "Profile Summary",
            "idx": structure["profile_summary"],
            "msg": "Shorten Profile Summary"
        })

    return cut_plan