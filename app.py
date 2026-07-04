"""
ResumeForge - Flask Backend
Run this file. Opens automatically in your browser.
"""

import os
import sys
import json
import uuid
import threading
import webbrowser
import shutil
import subprocess
from flask import Flask, render_template, request, jsonify, send_file

# Add engine folder to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "engine"))
from resume_engine import apply_json_to_docx, apply_confirmed_deletions, check_page_count, get_cut_plan, convert_docx_to_pdf
from master_prompt import get_master_prompt

app = Flask(__name__, template_folder="templates_html")

@app.errorhandler(Exception)
def handle_exception(e):
    from werkzeug.exceptions import HTTPException
    if isinstance(e, HTTPException):
        return jsonify({"error": e.description}), e.code
    import traceback
    tb = traceback.format_exc()
    print("=== UNHANDLED SERVER EXCEPTION ===")
    print(tb)
    print("==================================")
    return jsonify({"error": f"Internal Server Error: {str(e)}"}), 500

# ─────────────────────────────────────────────
# PATHS
# ─────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates_docx")
OUTPUTS_DIR = os.path.join(BASE_DIR, "outputs")
os.makedirs(OUTPUTS_DIR, exist_ok=True)

# Load .env file manually if exists
env_path = os.path.join(BASE_DIR, ".env")
if os.path.exists(env_path):
    try:
        with open(env_path, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ[k.strip()] = v.strip()
    except Exception:
        pass

# In-memory session store (simple dict, single user)
sessions = {}

def sanitize_filename(name):
    """Sanitizes filename to prevent path traversal and invalid characters under Windows."""
    import re
    cleaned = re.sub(r'[\\/:*?"<>|]', '_', name)
    cleaned = cleaned.strip(". ")
    cleaned = re.sub(r'\.+', '.', cleaned)
    cleaned = re.sub(r'\s+', '_', cleaned)
    if not cleaned:
        cleaned = "tailored_role"
    return cleaned

def cleanup_outputs_dir():
    """Clean up files in outputs/ folder that are older than 1 hour."""
    import time
    now = time.time()
    try:
        for filename in os.listdir(OUTPUTS_DIR):
            file_path = os.path.join(OUTPUTS_DIR, filename)
            if os.path.isfile(file_path):
                stat = os.stat(file_path)
                if now - stat.st_mtime > 3600:
                    os.remove(file_path)
    except Exception:
        pass

# ─────────────────────────────────────────────
# TEMPLATE REGISTRY
# ─────────────────────────────────────────────
KNOWN_TEMPLATES = [
    {"id": "Business_Analyst",  "label": "Business Analyst"},
    {"id": "Data_Analyst",      "label": "Data Analyst"},
    {"id": "Data_Scientist",    "label": "Data Scientist"},
    {"id": "Slot_4",            "label": "Slot 4 (Upload Template)"},
    {"id": "Slot_5",            "label": "Slot 5 (Upload Template)"},
    {"id": "Slot_6",            "label": "Slot 6 (Upload Template)"},
]

def get_available_templates():
    available = []
    # Read custom labels from custom_labels.json if it exists
    labels_file = os.path.join(TEMPLATES_DIR, "custom_labels.json")
    custom_labels = {}
    if os.path.exists(labels_file):
        try:
            with open(labels_file, "r") as f:
                custom_labels = json.load(f)
        except Exception:
            pass

    for t in KNOWN_TEMPLATES:
        path = os.path.join(TEMPLATES_DIR, t["id"] + ".docx")
        label = custom_labels.get(t["id"], t["label"])
        available.append({
            "id": t["id"],
            "label": label,
            "available": os.path.exists(path),
        })
    return available


# ─────────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────────

@app.route("/")
def index():
    # Load .env file dynamically on initial page load as well
    env_path = os.path.join(BASE_DIR, ".env")
    if os.path.exists(env_path):
        try:
            with open(env_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        os.environ[k.strip()] = v.strip()
        except Exception:
            pass

    templates = get_available_templates()
    keys_raw = os.environ.get("GEMINI_API_KEY")
    has_server_key = bool(keys_raw and keys_raw != "paste_your_keys_comma_separated_here")
    return render_template("index.html", templates=templates, has_server_key=has_server_key)


@app.route("/api/master-prompt")
def api_master_prompt():
    return jsonify({"prompt": get_master_prompt()})


@app.route("/api/templates")
def api_templates():
    return jsonify(get_available_templates())


@app.route("/api/process", methods=["POST"])
def api_process():
    """
    Receives: template_id + raw JSON string from user.
    Runs the engine. Returns warnings for user to confirm.
    """
    # Clean up old output files first
    cleanup_outputs_dir()

    data = request.json
    template_id = data.get("template_id")
    raw_json = data.get("json_data")
    role_name = data.get("role_name", template_id.replace("_", " "))

    if not template_id or not raw_json:
        return jsonify({"error": "Missing template_id or json_data"}), 400

    # Parse JSON
    try:
        resume_data = json.loads(raw_json)
    except Exception as e:
        return jsonify({"error": f"Invalid JSON: {str(e)}"}), 400

    # Template path
    template_path = os.path.join(TEMPLATES_DIR, template_id + ".docx")
    if not os.path.exists(template_path):
        return jsonify({"error": f"Template not found: {template_id}"}), 404

    # Output path (session-based temp file)
    session_id = str(uuid.uuid4())[:8]
    role_clean = sanitize_filename(role_name)
    out_filename = f"Rayen_{role_clean}_{session_id}.docx"
    out_path = os.path.join(OUTPUTS_DIR, out_filename)

    # Run engine — apply all text edits
    try:
        apply_json_to_docx(template_path, out_path, resume_data)
    except Exception as e:
        return jsonify({"error": f"Engine error: {str(e)}"}), 500

    # Check if it fits in one page
    try:
        page_count = check_page_count(out_path)
    except Exception:
        page_count = 1

    if page_count <= 1:
        sessions[session_id] = {
            "out_path": out_path,
            "out_filename": out_filename,
            "warnings": [],
            "resume_data": resume_data,
            "template_id": template_id,
            "role_name": role_name,
        }
        return jsonify({
            "session_id": session_id,
            "warnings": [],
            "has_warnings": False,
            "overflow": None,
        })
    else:
        try:
            warnings = get_cut_plan(out_path, resume_data)
        except Exception:
            warnings = []
        overflow_msg = (
            f"Resume is overflowing onto page {page_count}. "
            f"Suggested minimum cuts shown below — irrelevant items first."
        )
        sessions[session_id] = {
            "out_path": out_path,
            "out_filename": out_filename,
            "warnings": warnings,
            "resume_data": resume_data,
            "template_id": template_id,
            "role_name": role_name,
        }
        return jsonify({
            "session_id": session_id,
            "warnings": warnings,
            "has_warnings": len(warnings) > 0,
            "overflow": overflow_msg,
        })


@app.route("/api/confirm", methods=["POST"])
def api_confirm():
    """
    User has reviewed warnings and confirmed which deletions to apply.
    confirmed_warnings: list of warning indices the user approved.
    """
    data = request.json
    session_id = data.get("session_id")
    confirmed = data.get("confirmed_warnings", [])  # list of warning indices

    sess = sessions.get(session_id)
    if not sess:
        return jsonify({"error": "Session not found"}), 404

    # Collect indices to delete
    all_deletions = []
    for wi in confirmed:
        w = sess["warnings"][wi]
        if "indices" in w:
            all_deletions.extend(w["indices"])
        elif "idx" in w:
            all_deletions.append(w["idx"])

    # Apply deletions
    try:
        if all_deletions:
            apply_confirmed_deletions(sess["out_path"], all_deletions)
    except Exception as e:
        return jsonify({"error": f"Deletion error: {str(e)}"}), 500

    return jsonify({
        "success": True,
        "session_id": session_id,
        "filename": sess["out_filename"],
    })


@app.route("/api/tailor", methods=["POST"])
def api_tailor():
    """
    Directly triggers the AI tailoring flow.
    Receives template_id + job_description + optional custom_instructions.
    Calls Gemini API with fallback rotation on multi-keys, reframes content, and returns data.
    """
    cleanup_outputs_dir()

    data = request.json
    template_id = data.get("template_id")
    job_description = data.get("job_description")
    custom_instructions = data.get("custom_instructions", "")

    if not template_id or not job_description:
        return jsonify({"error": "Missing template_id or job_description"}), 400

    # Load .env file dynamically to pick up real-time key modifications without restarts
    env_path = os.path.join(BASE_DIR, ".env")
    if os.path.exists(env_path):
        try:
            with open(env_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        os.environ[k.strip()] = v.strip()
        except Exception:
            pass

    # Retrieve API keys (prioritizing server-side env keys over client-side header keys)
    keys_raw = os.environ.get("GEMINI_API_KEY") or request.headers.get("X-Gemini-Key")
    if not keys_raw or keys_raw.strip() == "paste_your_keys_comma_separated_here":
        return jsonify({"error": "Missing Gemini API Key. Please paste your valid keys inside the .env file in the project root."}), 401

    api_keys = [k.strip() for k in keys_raw.split(",") if k.strip()]
    if not api_keys:
        return jsonify({"error": "No valid Gemini API keys found. Check your keys list."}), 401

    # Template path
    template_path = os.path.join(TEMPLATES_DIR, template_id + ".docx")
    if not os.path.exists(template_path):
        return jsonify({"error": f"Template not found: {template_id}"}), 404

    # Build AI Prompt
    full_prompt = get_master_prompt() + "\n\nJob Description:\n" + job_description
    if custom_instructions:
        full_prompt += "\n\nAdditional Requirements / Focus Areas:\n" + custom_instructions

    # Call Gemini REST API with key rotation
    import requests
    res_data = None
    successful_key_idx = -1
    last_error_msg = "Unknown error"

    for idx, api_key in enumerate(api_keys):
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [{"parts": [{"text": full_prompt}]}],
            "generationConfig": {"responseMimeType": "application/json"}
        }

        try:
            res = requests.post(url, json=payload, headers=headers, timeout=60)
            status_code = res.status_code
            try:
                data_json = res.json()
            except Exception:
                data_json = {}
        except Exception as e:
            last_error_msg = f"Network connection failed on key #{idx+1}: {str(e)}"
            continue

        # Check if rate-limited (429) or resource exhaustion error is in response body
        is_quota_error = False
        if status_code == 429:
            is_quota_error = True
        elif "error" in data_json:
            err = data_json["error"]
            err_code = err.get("code")
            err_status = err.get("status", "")
            err_msg = err.get("message", "")
            if err_code == 429 or err_status == "RESOURCE_EXHAUSTED" or "quota" in err_msg.lower():
                is_quota_error = True
            else:
                last_error_msg = f"API Error on key #{idx+1}: {err_msg}"

        if is_quota_error:
            last_error_msg = f"Rate limit / Quota hit on key #{idx+1}"
            continue

        # Verify candidates are returned
        if "candidates" in data_json and data_json["candidates"]:
            res_data = data_json
            successful_key_idx = idx
            break
        else:
            if "error" in data_json:
                last_error_msg = data_json["error"].get("message", "No content candidates found")
            else:
                last_error_msg = f"Empty response on key #{idx+1}"

    if res_data is None:
        return jsonify({"error": f"All Gemini API keys failed or hit limits. Last message: {last_error_msg}"}), 400

    # Parse candidate text
    try:
        json_text = res_data["candidates"][0]["content"]["parts"][0]["text"].strip()
        # Clean potential markdown block wrappers
        if json_text.startswith("```"):
            lines = json_text.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines[-1].startswith("```"):
                lines = lines[:-1]
            json_text = "\n".join(lines).strip()
        
        resume_data = json.loads(json_text)
    except Exception as e:
        return jsonify({"error": f"Failed to parse AI output as JSON: {str(e)}"}), 500

    # Create session and custom files
    session_id = str(uuid.uuid4())[:8]
    role_name = resume_data.get("title_line", "tailored_role").split("|")[0].strip()
    role_clean = sanitize_filename(role_name)
    out_filename = f"Rayen_{role_clean}_{session_id}.docx"
    out_path = os.path.join(OUTPUTS_DIR, out_filename)

    # Run engine to apply text reframing
    try:
        apply_json_to_docx(template_path, out_path, resume_data)
    except Exception as e:
        return jsonify({"error": f"XML Engine rendering error: {str(e)}"}), 500

    # Length fit check
    try:
        page_count = check_page_count(out_path)
    except Exception:
        page_count = 1

    warnings = []
    if page_count > 1:
        try:
            warnings = get_cut_plan(out_path, resume_data)
        except Exception:
            pass

    sessions[session_id] = {
        "out_path": out_path,
        "out_filename": out_filename,
        "warnings": warnings,
        "resume_data": resume_data,
        "template_id": template_id,
        "role_name": role_name,
    }

    return jsonify({
        "session_id": session_id,
        "resume_data": resume_data,
        "warnings": warnings,
        "has_warnings": len(warnings) > 0,
        "overflow": f"Resume is overflowing onto page {page_count}. Suggested minimum cuts shown below." if page_count > 1 else None,
        "key_index_used": successful_key_idx
    })



@app.route("/api/compile", methods=["POST"])
def api_compile():
    """
    Compiles user manual edits.
    Receives session_id + updated resume_data JSON + confirmed_warnings index list.
    Re-compiles from clean template, applies approved warning cuts, and returns status.
    """
    data = request.json
    session_id = data.get("session_id")
    resume_data = data.get("resume_data")
    confirmed = data.get("confirmed_warnings", [])

    if not session_id or not resume_data:
        return jsonify({"error": "Missing session_id or resume_data"}), 400

    sess = sessions.get(session_id)
    if not sess:
        return jsonify({"error": "Session not found"}), 404

    # Update in-memory data
    sess["resume_data"] = resume_data

    # Apply confirmed trims to the JSON data directly before compilation
    for wi in confirmed:
        if wi < len(sess["warnings"]):
            w = sess["warnings"][wi]
            w_type = w.get("type")
            w_name = w.get("name")
            if w_type == "bullet_trim":
                for proj in resume_data.get("projects", []):
                    if proj.get("name") == w_name:
                        bullets = proj.get("bullets", [])
                        if bullets:
                            bullets.pop()
            elif w_type == "project_remove":
                for proj in resume_data.get("projects", []):
                    if proj.get("name") == w_name:
                        proj["include"] = False

    # Always re-compile from clean template to prevent compounding edits on top of old files
    template_path = os.path.join(TEMPLATES_DIR, sess["template_id"] + ".docx")
    try:
        apply_json_to_docx(template_path, sess["out_path"], resume_data)
    except Exception as e:
        return jsonify({"error": f"Compilation error: {str(e)}"}), 500

    # Check new page count
    try:
        page_count = check_page_count(sess["out_path"])
    except Exception:
        page_count = 1

    # Regenerate cuts if still overflowing
    warnings = []
    if page_count > 1:
        try:
            warnings = get_cut_plan(sess["out_path"], resume_data)
        except Exception:
            pass
    sess["warnings"] = warnings

    # Update filename in case role title changed
    role_name = resume_data.get("title_line", "tailored_role").split("|")[0].strip()
    role_clean = sanitize_filename(role_name)
    new_filename = f"Rayen_{role_clean}_{session_id}.docx"
    new_path = os.path.join(OUTPUTS_DIR, new_filename)

    if sess["out_path"] != new_path:
        try:
            # Clean up old DOCX
            if os.path.exists(sess["out_path"]):
                os.remove(sess["out_path"])
            # Clean up old PDF
            old_pdf = sess["out_path"].replace(".docx", ".pdf")
            if os.path.exists(old_pdf):
                os.remove(old_pdf)
        except Exception:
            pass
        sess["out_path"] = new_path
        sess["out_filename"] = new_filename
        # Compile directly to the new path
        try:
            apply_json_to_docx(template_path, new_path, resume_data)
        except Exception:
            pass

    sess["role_name"] = role_name

    return jsonify({
        "success": True,
        "session_id": session_id,
        "warnings": warnings,
        "has_warnings": len(warnings) > 0,
        "overflow": f"Resume is overflowing onto page {page_count}. Trim items further or shorten sections." if page_count > 1 else None
    })



@app.route("/api/preview/<session_id>")
def api_preview(session_id):
    """Returns resume content as structured JSON for preview rendering."""
    sess = sessions.get(session_id)
    if not sess:
        return jsonify({"error": "Session not found"}), 404

    resume_data = sess["resume_data"]
    return jsonify({
        "title_line": resume_data.get("title_line", ""),
        "profile_summary": resume_data.get("profile_summary", ""),
        "core_competencies": resume_data.get("core_competencies", {}),
        "certifications": resume_data.get("certifications", []),
        "projects": resume_data.get("projects", []),
        "extracurriculars": resume_data.get("extracurriculars", []),
    })


@app.route("/api/download/<session_id>/<format>")
def api_download(session_id, format):
    """Download the final resume as DOCX or PDF."""
    sess = sessions.get(session_id)
    if not sess:
        return jsonify({"error": "Session not found"}), 404

    docx_path = sess["out_path"]
    role_name = sanitize_filename(sess["role_name"])

    if format == "docx":
        response = send_file(
            docx_path,
            as_attachment=True,
            mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        response.headers["Content-Disposition"] = f'attachment; filename="Rayen_{role_name}.docx"'
        return response
    elif format == "pdf":
        pdf_path = docx_path.replace(".docx", ".pdf")

        if not convert_docx_to_pdf(docx_path, pdf_path):
            return jsonify({
                "error": "PDF conversion failed. As a workaround: open the downloaded DOCX in Word → File → Save As → PDF."
            }), 500

        response = send_file(
            pdf_path,
            as_attachment=True,
            mimetype="application/pdf"
        )
        response.headers["Content-Disposition"] = f'attachment; filename="Rayen_{role_name}.pdf"'
        return response
    else:
        return jsonify({"error": "Invalid format"}), 400


@app.route("/api/reset/<session_id>", methods=["POST"])
def api_reset(session_id):
    """Delete session and output file — reset to start."""
    sess = sessions.pop(session_id, None)
    if sess and os.path.exists(sess["out_path"]):
        os.remove(sess["out_path"])
    return jsonify({"success": True})


@app.route("/api/upload-template", methods=["POST"])
def api_upload_template():
    """Upload a new template into one of the empty slots."""
    slot_id = request.form.get("slot_id")
    file = request.files.get("file")

    if not slot_id or not file:
        return jsonify({"error": "Missing slot_id or file"}), 400

    valid_slots = ["Slot_4", "Slot_5", "Slot_6"]
    if slot_id not in valid_slots:
        return jsonify({"error": "Invalid slot"}), 400

    save_path = os.path.join(TEMPLATES_DIR, slot_id + ".docx")
    file.save(save_path)

    # Ask user to rename the slot
    label = request.form.get("label", slot_id.replace("_", " "))
    # Store custom label in a simple JSON file
    labels_file = os.path.join(TEMPLATES_DIR, "custom_labels.json")
    labels = {}
    if os.path.exists(labels_file):
        with open(labels_file) as f:
            labels = json.load(f)
    labels[slot_id] = label
    with open(labels_file, "w") as f:
        json.dump(labels, f)

    return jsonify({"success": True, "slot_id": slot_id, "label": label})


# ─────────────────────────────────────────────
# LAUNCH
# ─────────────────────────────────────────────

def open_browser(port):
    import time
    time.sleep(1.2)
    webbrowser.open(f"http://localhost:{port}")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print("=" * 50)
    print("  ResumeForge is starting...")
    print(f"  Running on port {port}...")
    print("=" * 50)
    if os.environ.get("FLASK_ENV") != "production":
        threading.Thread(target=open_browser, args=(port,), daemon=True).start()
    app.run(debug=False, port=port, use_reloader=False)

