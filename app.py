"""Hospital Emergency Management System - Flask app."""
import os

from flask import (
    Flask, render_template, request, redirect, url_for, flash,
    send_from_directory, jsonify,
)

import database as db

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Flat project layout: templates and CSS live next to app.py
app = Flask(__name__, template_folder=BASE_DIR, static_folder=None)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-me")

TRIAGE_LEVELS = {
    1: "Resuscitation",
    2: "Emergent",
    3: "Urgent",
    4: "Less Urgent",
    5: "Non-Urgent",
}

db.init_db()


@app.context_processor
def inject_globals():
    return {"TRIAGE_LEVELS": TRIAGE_LEVELS, "STATUSES": db.STATUSES}


@app.route("/style.css")
def stylesheet():
    return send_from_directory(BASE_DIR, "style.css", mimetype="text/css")


@app.route("/")
def index():
    beds = db.get_beds()
    return render_template(
        "index.html",
        stats=db.get_stats(),
        queue=db.get_queue(),
        beds=beds,
        free_beds=[b for b in beds if not b["patient_id"]],
    )


@app.route("/patients")
def patients():
    search = request.args.get("q", "").strip()
    status = request.args.get("status", "").strip()
    return render_template(
        "patients.html",
        patients=db.get_patients(search, status),
        search=search,
        status=status,
    )


@app.route("/register", methods=["POST"])
def register():
    name = request.form.get("name", "").strip()
    complaint = request.form.get("complaint", "").strip()
    try:
        triage = int(request.form.get("triage", ""))
        age = int(request.form.get("age") or 0)
    except ValueError:
        flash("Age and triage level must be numbers.", "error")
        return redirect(url_for("index"))
    if not name or not complaint or triage not in TRIAGE_LEVELS or age < 0 or age > 120:
        flash("Please provide a name, complaint, valid age and triage level (1-5).", "error")
        return redirect(url_for("index"))
    db.add_patient(
        name, age, request.form.get("gender", ""), complaint, triage,
        request.form.get("notes", "").strip(),
    )
    flash(f"{name} registered with triage level {triage} ({TRIAGE_LEVELS[triage]}).", "success")
    return redirect(url_for("index"))


@app.route("/patient/<int:pid>/assign", methods=["POST"])
def assign(pid):
    patient = db.get_patient(pid)
    if not patient:
        flash("Patient not found.", "error")
        return redirect(url_for("index"))
    try:
        bed_id = int(request.form.get("bed_id", ""))
    except ValueError:
        flash("Select a bed first.", "error")
        return redirect(url_for("index"))
    if db.assign_bed(pid, bed_id):
        flash(f"Bed assigned to {patient['name']}. Treatment started.", "success")
    else:
        flash("That bed is already occupied.", "error")
    return redirect(url_for("index"))


@app.route("/patient/<int:pid>/status", methods=["POST"])
def change_status(pid):
    patient = db.get_patient(pid)
    status = request.form.get("status", "")
    if not patient or not db.set_status(pid, status):
        flash("Could not update status.", "error")
    else:
        flash(f"{patient['name']} marked as {status}.", "success")
    return redirect(request.form.get("next") or url_for("index"))


@app.route("/patient/<int:pid>/notes", methods=["POST"])
def notes(pid):
    db.update_notes(pid, request.form.get("notes", "").strip())
    flash("Notes updated.", "success")
    return redirect(url_for("patients"))


@app.route("/patient/<int:pid>/delete", methods=["POST"])
def delete(pid):
    db.delete_patient(pid)
    flash("Record deleted.", "success")
    return redirect(url_for("patients"))


@app.route("/api/stats")
def api_stats():
    return jsonify(db.get_stats())


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
