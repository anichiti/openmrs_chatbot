import os
import sys
import json
import markdown

from flask import Flask, render_template, request, session, redirect, url_for, jsonify

# Ensure the project root is on the path so all existing imports work
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import ClinicalChatbot
from utils.workflow_tracer import get_trace, get_all_traces, clear_traces

app = Flask(__name__)
app.secret_key = os.urandom(24)

# ── Singleton chatbot instance (initialized once at startup) ──────────────────
print("Initializing ClinicalChatbot for web UI...")
chatbot = ClinicalChatbot()
print("ClinicalChatbot ready.")


# ── Helpers ───────────────────────────────────────────────────────────────────

def calculate_age(birthdate_str):
    """Return a human-readable age string from a birthdate string."""
    if not birthdate_str:
        return "N/A"
    try:
        from datetime import date
        from dateutil.relativedelta import relativedelta
        from datetime import datetime
        if isinstance(birthdate_str, str):
            bd = datetime.strptime(birthdate_str[:10], "%Y-%m-%d").date()
        else:
            bd = birthdate_str
        delta = relativedelta(date.today(), bd)
        if delta.years >= 1:
            return f"{delta.years}y {delta.months}m"
        return f"{delta.months} months"
    except Exception:
        return str(birthdate_str)


def format_patient_for_api(patient_row):
    """Convert a DB patient row dict to a clean API-safe dict."""
    given = patient_row.get("given_name") or ""
    family = patient_row.get("family_name") or ""
    full_name = f"{given} {family}".strip() or "Unknown"
    return {
        "patient_id": patient_row.get("patient_id"),
        "patient_identifier": patient_row.get("patient_identifier") or patient_row.get("patient_id"),
        "full_name": full_name,
        "given_name": given,
        "family_name": family,
        "gender": patient_row.get("gender", "N/A"),
        "birthdate": str(patient_row.get("birthdate", "")) if patient_row.get("birthdate") else "N/A",
        "age": calculate_age(patient_row.get("birthdate")),
        "address1": patient_row.get("address1", ""),
        "address2": patient_row.get("address2", ""),
        "city_village": patient_row.get("city_village", ""),
        "state_province": patient_row.get("state_province", ""),
        "postal_code": patient_row.get("postal_code", ""),
        "dead": bool(patient_row.get("dead", False)),
        "death_date": str(patient_row.get("death_date", "")) if patient_row.get("death_date") else None,
    }


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    """Role selection landing page."""
    session.clear()
    return render_template("index.html")


@app.route("/set-role", methods=["POST"])
def set_role():
    """Store the chosen role in the session and go to the chat page."""
    role = request.form.get("role", "").lower()
    if role not in ("doctor", "patient"):
        return redirect(url_for("index"))
    session["user_role"] = role
    chatbot.user_role = role
    return redirect(url_for("chat"))


@app.route("/chat")
def chat():
    """Main chat interface."""
    if "user_role" not in session:
        return redirect(url_for("index"))
    return render_template("chat.html", role=session["user_role"])


@app.route("/reset", methods=["POST"])
def reset():
    """Clear session and return to landing page."""
    session.clear()
    chatbot.user_role = None
    return redirect(url_for("index"))


# ── Patient API ───────────────────────────────────────────────────────────────

@app.route("/api/patients/search")
def search_patients():
    """Search patients by name or ID (query param: q)."""
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify({"patients": [], "error": None})

    try:
        # Try as patient ID first (short numeric / alphanumeric)
        db = chatbot.sql_agent.db
        connected = db.connect()
        if not connected:
            return jsonify({"patients": [], "error": "Database connection failed"})

        # If it looks like an ID (no spaces, length < 12) try verify first
        patients = []
        if len(q) <= 12 and " " not in q:
            result = db.verify_patient_exists(q)
            if result and result is not False:
                patients = [format_patient_for_api(result)]

        # Fall back to name search
        if not patients:
            result = db.search_patients(q, limit=20)
            if result and not result.get("error") and result.get("data"):
                patients = [format_patient_for_api(row) for row in result["data"]]

        db.disconnect()
        return jsonify({"patients": patients, "error": None})

    except Exception as e:
        return jsonify({"patients": [], "error": str(e)})


@app.route("/api/patients/list")
def list_patients():
    """Return the first 20 patients."""
    try:
        db = chatbot.sql_agent.db
        connected = db.connect()
        if not connected:
            return jsonify({"patients": [], "error": "Database connection failed"})

        result = db.list_all_patients(20)
        db.disconnect()

        if result and not result.get("error") and result.get("data"):
            patients = [format_patient_for_api(row) for row in result["data"]]
            return jsonify({"patients": patients, "error": None})

        return jsonify({"patients": [], "error": result.get("error") if result else "No data"})

    except Exception as e:
        return jsonify({"patients": [], "error": str(e)})


@app.route("/api/patients/<patient_id>")
def get_patient(patient_id):
    """Get a single patient's details."""
    try:
        db = chatbot.sql_agent.db
        connected = db.connect()
        if not connected:
            return jsonify({"patient": None, "error": "Database connection failed"})

        result = db.verify_patient_exists(patient_id)
        db.disconnect()

        if result and result is not False:
            return jsonify({"patient": format_patient_for_api(result), "error": None})

        return jsonify({"patient": None, "error": f"Patient '{patient_id}' not found"})

    except Exception as e:
        return jsonify({"patient": None, "error": str(e)})


# ── Chat API ──────────────────────────────────────────────────────────────────

@app.route("/api/chat", methods=["POST"])
def api_chat():
    """
    Process a chat message.
    Body JSON: { "question": "...", "patient_id": "..." }
    """
    if "user_role" not in session:
        return jsonify({"error": "Session expired. Please select a role."}), 401

    data = request.get_json(force=True, silent=True) or {}
    question = (data.get("question") or "").strip()
    patient_id = (data.get("patient_id") or "").strip() or None

    if not question:
        return jsonify({"error": "Question cannot be empty."}), 400

    # Keep chatbot role in sync with session
    chatbot.user_role = session["user_role"]

    try:
        result = chatbot.process_query(question, selected_patient_id=patient_id)

        # Convert response text to HTML (markdown → HTML)
        html_response = markdown.markdown(
            result.get("response", ""),
            extensions=["nl2br", "tables"]
        )

        return jsonify({
            "response": result.get("response", ""),
            "response_html": html_response,
            "intent": result.get("intent", "GENERAL_MEDICAL_QUERY"),
            "user_type": result.get("user_type", session["user_role"].upper()),
            "sources": result.get("sources", []),
            "patient_id": result.get("patient_id", patient_id),
            "timestamp": result.get("timestamp", ""),
            "emergency_flag": result.get("emergency_flag", False),
            "is_hybrid_question": result.get("is_hybrid_question", False),
            "trace_id": result.get("trace_id"),
        })

    except Exception as e:
        return jsonify({"error": f"Error processing query: {str(e)}"}), 500


# ── Workflow Trace API ────────────────────────────────────────────────────────

@app.route("/api/trace/<trace_id>")
def get_workflow_trace(trace_id):
    """Retrieve a detailed workflow trace for a specific query."""
    trace = get_trace(trace_id)
    if not trace:
        return jsonify({"error": f"Trace '{trace_id}' not found"}), 404
    return jsonify({"trace": trace})


@app.route("/api/traces")
def list_workflow_traces():
    """List all recent workflow traces."""
    traces = get_all_traces()
    # Return sorted by start_time (newest first)
    sorted_traces = sorted(
        traces.items(),
        key=lambda x: x[1].get("metadata", {}).get("start_time", ""),
        reverse=True
    )
    return jsonify({
        "traces": [
            {
                "trace_id": k,
                "metadata": v.get("metadata", {}),
            }
            for k, v in sorted_traces
        ],
        "total": len(sorted_traces),
    })


@app.route("/api/traces/clear", methods=["POST"])
def clear_workflow_traces():
    """Clear all stored traces (development/testing only)."""
    clear_traces()
    return jsonify({"message": "All traces cleared"})


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
