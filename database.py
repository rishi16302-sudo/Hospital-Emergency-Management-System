"""SQLite data layer for the Hospital Emergency Management System."""
import os
import sqlite3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get("DATABASE_PATH", os.path.join(BASE_DIR, "hospital.db"))

STATUSES = ["Waiting", "In Treatment", "Admitted", "Discharged"]
ACTIVE_STATUSES = ("Waiting", "In Treatment")


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Create tables and seed beds + a few demo patients on first run."""
    conn = get_conn()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS beds (
            id    INTEGER PRIMARY KEY AUTOINCREMENT,
            label TEXT NOT NULL UNIQUE,
            type  TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS patients (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            name       TEXT NOT NULL,
            age        INTEGER,
            gender     TEXT,
            complaint  TEXT NOT NULL,
            triage     INTEGER NOT NULL CHECK (triage BETWEEN 1 AND 5),
            notes      TEXT,
            status     TEXT NOT NULL DEFAULT 'Waiting',
            bed_id     INTEGER REFERENCES beds(id),
            arrived_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
        );
        """
    )
    if conn.execute("SELECT COUNT(*) FROM beds").fetchone()[0] == 0:
        beds = (
            [(f"ER-{i}", "Emergency") for i in range(1, 9)]
            + [(f"TR-{i}", "Trauma") for i in range(1, 5)]
            + [(f"ICU-{i}", "ICU") for i in range(1, 5)]
        )
        conn.executemany("INSERT INTO beds (label, type) VALUES (?, ?)", beds)
    if conn.execute("SELECT COUNT(*) FROM patients").fetchone()[0] == 0:
        demo = [
            ("Ramesh Kumar", 58, "Male", "Chest pain radiating to left arm", 2, "History of hypertension"),
            ("Anita Sharma", 34, "Female", "Fracture of right forearm after fall", 3, ""),
            ("Baby Aarav", 2, "Male", "High fever and seizure", 1, "Febrile seizure, needs immediate care"),
            ("Mohit Verma", 27, "Male", "Minor cut on hand", 5, ""),
        ]
        conn.executemany(
            "INSERT INTO patients (name, age, gender, complaint, triage, notes) VALUES (?,?,?,?,?,?)",
            demo,
        )
    conn.commit()
    conn.close()


# ---------- patients ----------
def add_patient(name, age, gender, complaint, triage, notes):
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO patients (name, age, gender, complaint, triage, notes) VALUES (?,?,?,?,?,?)",
        (name, age, gender, complaint, triage, notes),
    )
    conn.commit()
    pid = cur.lastrowid
    conn.close()
    return pid


_PATIENT_SELECT = """
    SELECT p.*, b.label AS bed_label,
           CAST((julianday('now','localtime') - julianday(p.arrived_at)) * 24 * 60 AS INTEGER) AS minutes_since_arrival
    FROM patients p LEFT JOIN beds b ON b.id = p.bed_id
"""


def get_queue():
    """Active patients, most critical first, then longest waiting."""
    conn = get_conn()
    rows = conn.execute(
        _PATIENT_SELECT
        + " WHERE p.status IN ('Waiting','In Treatment') ORDER BY p.triage ASC, p.arrived_at ASC"
    ).fetchall()
    conn.close()
    return rows


def get_patients(search="", status=""):
    conn = get_conn()
    sql = _PATIENT_SELECT + " WHERE 1=1"
    params = []
    if search:
        sql += " AND (p.name LIKE ? OR p.complaint LIKE ?)"
        params += [f"%{search}%", f"%{search}%"]
    if status in STATUSES:
        sql += " AND p.status = ?"
        params.append(status)
    sql += " ORDER BY p.arrived_at DESC"
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return rows


def get_patient(pid):
    conn = get_conn()
    row = conn.execute(_PATIENT_SELECT + " WHERE p.id = ?", (pid,)).fetchone()
    conn.close()
    return row


def update_notes(pid, notes):
    conn = get_conn()
    conn.execute(
        "UPDATE patients SET notes = ?, updated_at = datetime('now','localtime') WHERE id = ?",
        (notes, pid),
    )
    conn.commit()
    conn.close()


def set_status(pid, status):
    """Change status. Admitted/Discharged patients release their bed."""
    if status not in STATUSES:
        return False
    conn = get_conn()
    if status in ("Admitted", "Discharged", "Waiting"):
        conn.execute(
            "UPDATE patients SET status=?, bed_id=NULL, updated_at=datetime('now','localtime') WHERE id=?",
            (status, pid),
        )
    else:
        conn.execute(
            "UPDATE patients SET status=?, updated_at=datetime('now','localtime') WHERE id=?",
            (status, pid),
        )
    conn.commit()
    conn.close()
    return True


def assign_bed(pid, bed_id):
    """Assign a free bed to an active patient and start treatment."""
    conn = get_conn()
    busy = conn.execute(
        "SELECT 1 FROM patients WHERE bed_id = ? AND status = 'In Treatment'", (bed_id,)
    ).fetchone()
    if busy:
        conn.close()
        return False
    conn.execute(
        "UPDATE patients SET bed_id=?, status='In Treatment', updated_at=datetime('now','localtime') WHERE id=?",
        (bed_id, pid),
    )
    conn.commit()
    conn.close()
    return True


def delete_patient(pid):
    conn = get_conn()
    conn.execute("DELETE FROM patients WHERE id = ?", (pid,))
    conn.commit()
    conn.close()


# ---------- beds & stats ----------
def get_beds():
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT b.*, p.id AS patient_id, p.name AS patient_name, p.triage AS patient_triage
        FROM beds b
        LEFT JOIN patients p ON p.bed_id = b.id AND p.status = 'In Treatment'
        ORDER BY b.type, b.id
        """
    ).fetchall()
    conn.close()
    return rows


def get_stats():
    conn = get_conn()
    q = lambda sql: conn.execute(sql).fetchone()[0]
    stats = {
        "waiting": q("SELECT COUNT(*) FROM patients WHERE status='Waiting'"),
        "in_treatment": q("SELECT COUNT(*) FROM patients WHERE status='In Treatment'"),
        "critical": q("SELECT COUNT(*) FROM patients WHERE status IN ('Waiting','In Treatment') AND triage <= 2"),
        "total_beds": q("SELECT COUNT(*) FROM beds"),
        "occupied_beds": q("SELECT COUNT(*) FROM patients WHERE status='In Treatment' AND bed_id IS NOT NULL"),
        "today": q("SELECT COUNT(*) FROM patients WHERE date(arrived_at) = date('now','localtime')"),
    }
    stats["free_beds"] = stats["total_beds"] - stats["occupied_beds"]
    conn.close()
    return stats
