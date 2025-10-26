from flask import Flask, jsonify, request, render_template_string, redirect, url_for
from datetime import datetime, date
import re

app = Flask(__name__)

# --------------------
# In-memory "database"
# --------------------
students = [
    {"id": 1, "name": "John Doe", "grade": 10, "section": "Zechariah"},
    {"id": 2, "name": "Jane Smith", "grade": 10, "section": "Zechariah"}
]

# attendance entries: list of { student_id: int, status: "Present"/"Absent", timestamp: ISO, date: "YYYY-MM-DD" }
attendance = [
    # example: {"student_id": 1, "status": "Present", "timestamp": "2025-10-26T08:00:00Z", "date": "2025-10-26"}
]

# --------------------
# Helper functions
# --------------------
def now_iso():
    return datetime.utcnow().isoformat() + "Z"

def today_str():
    return date.today().isoformat()

def find_student(student_id):
    return next((s for s in students if s["id"] == student_id), None)

def next_student_id():
    return (students[-1]["id"] + 1) if students else 1

def get_attendance_for_student_and_date(student_id, date_str=None):
    d = date_str or today_str()
    return [a for a in attendance if a["student_id"] == student_id and a["date"] == d]

# --------------------
# Basic routes
# --------------------
@app.route('/')
def home():
    # simple landing: redirect to dashboard
    return redirect(url_for('dashboard'))

# --------------------
# API - Students CRUD
# --------------------
@app.route('/api/students', methods=['GET'])
def api_get_students():
    q = request.args.get('q')
    grade = request.args.get('grade')
    section = request.args.get('section')

    results = students
    if q:
        pattern = re.compile(re.escape(q), re.IGNORECASE)
        results = [s for s in results if pattern.search(s['name'])]
    if grade:
        try:
            g = int(grade)
            results = [s for s in results if s.get('grade') == g]
        except ValueError:
            return jsonify({"status": "error", "message": "grade must be integer"}), 400
    if section:
        results = [s for s in results if s.get('section', '').lower() == section.lower()]

    return jsonify({"status": "success", "students": results}), 200

@app.route('/api/students/<int:student_id>', methods=['GET'])
def api_get_student(student_id):
    s = find_student(student_id)
    if not s:
        return jsonify({"status": "error", "message": "Student not found"}), 404
    return jsonify({"status": "success", "student": s}), 200

@app.route('/api/students', methods=['POST'])
def api_add_student():
    data = request.get_json() or {}
    name = data.get('name')
    grade = data.get('grade')
    section = data.get('section')

    if not name or grade is None or not section:
        return jsonify({"status": "error", "message": "name, grade and section are required"}), 400
    try:
        grade = int(grade)
    except ValueError:
        return jsonify({"status": "error", "message": "grade must be integer"}), 400

    new = {"id": next_student_id(), "name": name.strip(), "grade": grade, "section": section.strip()}
    students.append(new)
    return jsonify({"status": "success", "student": new}), 201

@app.route('/api/students/<int:student_id>', methods=['PUT'])
def api_update_student(student_id):
    s = find_student(student_id)
    if not s:
        return jsonify({"status": "error", "message": "Student not found"}), 404
    data = request.get_json() or {}
    s['name'] = data.get('name', s['name']).strip()
    try:
        s['grade'] = int(data.get('grade', s['grade']))
    except ValueError:
        return jsonify({"status": "error", "message": "grade must be integer"}), 400
    s['section'] = data.get('section', s['section']).strip()
    return jsonify({"status": "success", "student": s}), 200

@app.route('/api/students/<int:student_id>', methods=['DELETE'])
def api_delete_student(student_id):
    global students
    s = find_student(student_id)
    if not s:
        return jsonify({"status": "error", "message": "Student not found"}), 404
    students = [x for x in students if x['id'] != student_id]
    # remove attendance entries for that student (optional)
    global attendance
    attendance = [a for a in attendance if a['student_id'] != student_id]
    return jsonify({"status": "success", "message": "Student deleted"}), 200

# --------------------
# API - Login (ID + Name) - students provide ID and name, server validates
# --------------------
@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json() or {}
    student_id = data.get('id')
    name = data.get('name', '').strip()

    if not student_id or not name:
        return jsonify({"status": "error", "message": "id and name are required"}), 400
    try:
        student_id = int(student_id)
    except ValueError:
        return jsonify({"status": "error", "message": "id must be integer"}), 400

    s = find_student(student_id)
    if not s:
        return jsonify({"status": "error", "message": "Student not found"}), 404

    # match name loosely (case-insensitive)
    if s['name'].strip().lower() != name.lower():
        return jsonify({"status": "error", "message": "Name does not match the provided ID"}), 401

    # success
    return jsonify({"status": "success", "student": s, "redirect": f"/attendance/{student_id}"}), 200

# --------------------
# API - Attendance
# --------------------
@app.route('/api/attendance', methods=['GET'])
def api_get_attendance():
    # optional filters: student_id, date
    sid = request.args.get('student_id')
    d = request.args.get('date') or today_str()
    results = [a for a in attendance if a['date'] == d]
    if sid:
        try:
            sid = int(sid)
            results = [a for a in results if a['student_id'] == sid]
        except ValueError:
            return jsonify({"status": "error", "message": "student_id must be integer"}), 400
    return jsonify({"status": "success", "attendance": results}), 200

@app.route('/api/attendance', methods=['POST'])
def api_post_attendance():
    data = request.get_json() or {}
    student_id = data.get('student_id')
    status = data.get('status', 'Present')
    timestamp = now_iso()
    d = today_str()

    if not student_id:
        return jsonify({"status": "error", "message": "student_id required"}), 400
    try:
        student_id = int(student_id)
    except ValueError:
        return jsonify({"status": "error", "message": "student_id must be integer"}), 400

    s = find_student(student_id)
    if not s:
        return jsonify({"status": "error", "message": "Student not found"}), 404

    # prevent duplicate marking for same day (you can allow multiple entries if you want)
    existing = get_attendance_for_student_and_date(student_id, d)
    if existing:
        return jsonify({"status": "error", "message": "Attendance already marked for today"}), 409

    entry = {"student_id": student_id, "status": status, "timestamp": timestamp, "date": d}
    attendance.append(entry)
    return jsonify({"status": "success", "attendance": entry}), 201

# --------------------
# Admin Dashboard UI, Student Login UI, Attendance UI (single-file, inline HTML/CSS/JS)
# --------------------
@app.route('/dashboard')
def dashboard():
    # admin dashboard: manage students and view today's attendance
    return render_template_string("""
<!doctype html>
<html>
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>Admin Dashboard - Students & Attendance</title>
  <style>
    :root{--bg:#f7fbff;--card:#fff;--accent:#2b6ef6;--muted:#6b7280}
    body{font-family:Inter, system-ui, -apple-system, 'Segoe UI', Roboto, Arial; background:var(--bg); margin:0; padding:24px}
    .wrap{max-width:1100px;margin:0 auto}
    header{display:flex;justify-content:space-between;align-items:center}
    h1{margin:0}
    .muted{color:var(--muted)}
    .grid{display:grid;grid-template-columns:1fr 380px;gap:16px;margin-top:16px}
    .card{background:var(--card);padding:12px;border-radius:10px;box-shadow:0 6px 18px rgba(16,24,40,0.06)}
    table{width:100%;border-collapse:collapse}
    th,td{padding:8px;border-bottom:1px solid #eee;text-align:left}
    th{background:#f3f4f6}
    input,select{padding:8px;border-radius:8px;border:1px solid #e6eef8;width:100%}
    .row{display:flex;gap:8px;margin-top:8px}
    button{background:var(--accent);color:white;border:none;padding:8px 10px;border-radius:8px;cursor:pointer}
    .ghost{background:#e5e7eb;color:#111}
    .small{padding:6px 8px;font-size:14px}
    .attendance-list{max-height:300px;overflow:auto}
    .footer{margin-top:12px;color:var(--muted);font-size:13px}
    @media(max-width:900px){.grid{grid-template-columns:1fr}}
  </style>
</head>
<body>
  <div class="wrap">
    <header>
      <div>
        <h1>Student Dashboard</h1>
        <div class="muted">Manage students & view attendance (today)</div>
      </div>
      <div>
        <a href="/login" style="text-decoration:none"><button class="small">Student Login</button></a>
      </div>
    </header>

    <div class="grid">
      <!-- left: students table -->
      <div class="card">
        <h3>Students</h3>
        <div style="display:flex;gap:8px;margin-bottom:8px">
          <input id="search" placeholder="Search name..." />
          <button id="btnSearch" class="ghost small">Search</button>
          <button id="btnRefresh" class="small">Refresh</button>
        </div>

        <table>
          <thead><tr><th>ID</th><th>Name</th><th>Grade</th><th>Section</th><th>Action</th></tr></thead>
          <tbody id="studentsTbody"></tbody>
        </table>

        <div style="margin-top:12px">
          <h4>Add / Edit Student</h4>
          <input type="hidden" id="editId" />
          <div style="margin-top:8px"><input id="sname" placeholder="Full name" /></div>
          <div class="row">
            <input id="sgrade" type="number" placeholder="Grade" />
            <input id="ssection" placeholder="Section" />
          </div>
          <div class="row" style="margin-top:8px">
            <button id="btnSave">Save</button>
            <button id="btnClear" class="ghost">Clear</button>
          </div>
        </div>
      </div>

      <!-- right: today's attendance -->
      <div class="card">
        <h3>Today's Attendance (<span id="today"></span>)</h3>
        <div class="attendance-list">
          <table style="width:100%">
            <thead><tr><th>Student</th><th>Time</th><th>Status</th></tr></thead>
            <tbody id="attendanceTbody"></tbody>
          </table>
        </div>

        <div style="margin-top:12px">
          <h4>Export / Quick Ops</h4>
          <button id="btnExport" class="ghost small">Export JSON</button>
          <button id="btnClearAll" class="ghost small">Clear Today (danger)</button>
        </div>

        <div class="footer">Note: Attendance is stored in-memory (server restart clears data). Use export before restart.</div>
      </div>
    </div>
  </div>

<script>
const apiBase = '/api';

async function fetchStudents(q='') {
  const url = q ? apiBase + '/students?q=' + encodeURIComponent(q) : apiBase + '/students';
  const res = await fetch(url);
  return await res.json();
}

function renderStudents(list) {
  const tbody = document.getElementById('studentsTbody');
  tbody.innerHTML = '';
  list.forEach(s => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${s.id}</td>
      <td>${s.name}</td>
      <td>${s.grade}</td>
      <td>${s.section}</td>
      <td>
        <button class="ghost small" data-id="${s.id}" data-action="edit">Edit</button>
        <button class="ghost small" data-id="${s.id}" data-action="delete">Delete</button>
      </td>
    `;
    tbody.appendChild(tr);
  });
}

async function refreshStudents() {
  const q = document.getElementById('search').value.trim();
  const res = await fetchStudents(q);
  if (res.status === 'success') renderStudents(res.students);
}

async function refreshAttendance() {
  const today = new Date().toISOString().slice(0,10);
  document.getElementById('today').innerText = today;
  const res = await fetch(apiBase + '/attendance?date=' + today);
  const data = await res.json();
  const tbody = document.getElementById('attendanceTbody');
  tbody.innerHTML = '';
  if (data.status === 'success') {
    data.attendance.forEach(a => {
      const tr = document.createElement('tr');
      const name = getStudentName(a.student_id) || ('#' + a.student_id);
      const time = new Date(a.timestamp).toLocaleTimeString();
      tr.innerHTML = `<td>${name}</td><td>${time}</td><td>${a.status}</td>`;
      tbody.appendChild(tr);
    });
  }
}

function getStudentName(id) {
  const rows = document.querySelectorAll('#studentsTbody tr');
  for (const r of rows) {
    if (r.querySelector('td')) {
      const sid = parseInt(r.querySelector('td').innerText, 10);
      if (sid === id) return r.querySelectorAll('td')[1].innerText;
    }
  }
  return null;
}

// event handlers for edit/delete/save
document.addEventListener('click', async (e) => {
  if (e.target.matches('button[data-action]')) {
    const id = parseInt(e.target.dataset.id, 10);
    const action = e.target.dataset.action;
    if (action === 'edit') {
      // populate form
      const res = await fetch(apiBase + '/students/' + id);
      const data = await res.json();
      if (data.status === 'success') {
        document.getElementById('editId').value = data.student.id;
        document.getElementById('sname').value = data.student.name;
        document.getElementById('sgrade').value = data.student.grade;
        document.getElementById('ssection').value = data.student.section;
        window.scrollTo({top:0, behavior:'smooth'});
      } else alert(data.message || 'Could not load student');
    } else if (action === 'delete') {
      if (!confirm('Delete student and their attendance?')) return;
      const res = await fetch(apiBase + '/students/' + id, { method: 'DELETE' });
      const data = await res.json();
      if (data.status === 'success') { refreshStudents(); refreshAttendance(); } else alert(data.message);
    }
  }
});

document.getElementById('btnSave').addEventListener('click', async () => {
  const id = document.getElementById('editId').value;
  const name = document.getElementById('sname').value.trim();
  const grade = document.getElementById('sgrade').value;
  const section = document.getElementById('ssection').value.trim();

  if (!name || !grade || !section) { alert('All fields required'); return; }

  const payload = { name, grade: parseInt(grade,10), section };

  if (id) {
    const res = await fetch(apiBase + '/students/' + id, { method: 'PUT', headers: {'Content-Type':'application/json'}, body: JSON.stringify(payload) });
    const data = await res.json();
    if (data.status === 'success') { clearForm(); refreshStudents(); refreshAttendance(); } else alert(data.message);
  } else {
    const res = await fetch(apiBase + '/students', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(payload) });
    const data = await res.json();
    if (data.status === 'success') { clearForm(); refreshStudents(); } else alert(data.message);
  }
});

document.getElementById('btnClear').addEventListener('click', clearForm);
document.getElementById('btnRefresh').addEventListener('click', () => { document.getElementById('search').value=''; refreshStudents(); });
document.getElementById('btnSearch').addEventListener('click', refreshStudents);
document.getElementById('btnExport').addEventListener('click', async () => {
  const today = new Date().toISOString().slice(0,10);
  const res = await fetch(apiBase + '/attendance?date=' + today);
  const data = await res.json();
  if (data.status === 'success') {
    const blob = new Blob([JSON.stringify(data.attendance, null, 2)], {type:'application/json'});
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a'); a.href = url; a.download = 'attendance-' + today + '.json'; a.click(); URL.revokeObjectURL(url);
  } else alert('No attendance to export');
});

document.getElementById('btnClearAll').addEventListener('click', async () => {
  if (!confirm('Clear today\\'s attendance? This cannot be undone in-memory.')) return;
  // call server endpoint to clear today's attendance
  const today = new Date().toISOString().slice(0,10);
  const res = await fetch(apiBase + '/attendance/clear?date=' + today, { method: 'POST' });
  const data = await res.json();
  if (data.status === 'success') refreshAttendance();
  else alert(data.message || 'Failed');
});

function clearForm() {
  document.getElementById('editId').value = '';
  document.getElementById('sname').value = '';
  document.getElementById('sgrade').value = '';
  document.getElementById('ssection').value = '';
}

window.addEventListener('load', () => {
  refreshStudents();
  refreshAttendance();
  setInterval(refreshAttendance, 30 * 1000); // update attendance list periodically
});
</script>
</body>
</html>
    """)

# --------------------
# Student Login Page (ID + Name)
# --------------------
@app.route('/login')
def login_page():
    return render_template_string("""
<!doctype html>
<html>
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>Student Login</title>
  <style>
    body{font-family:Arial;display:flex;align-items:center;justify-content:center;height:100vh;background:#f4f6fb;margin:0}
    .card{background:#fff;padding:20px;border-radius:10px;box-shadow:0 6px 20px rgba(16,24,40,0.08);width:360px}
    input{width:100%;padding:10px;margin:8px 0;border-radius:8px;border:1px solid #e6eef8}
    button{width:100%;padding:10px;background:#2563eb;color:#fff;border:none;border-radius:8px;cursor:pointer}
    .muted{font-size:13px;color:#6b7280;text-align:center;margin-top:8px}
    a{display:block;text-align:center;margin-top:8px;color:#2563eb;text-decoration:none}
  </style>
</head>
<body>
  <div class="card">
    <h3 style="margin:0 0 8px 0">Student Login</h3>
    <input id="sid" type="number" placeholder="Student ID" />
    <input id="sname" type="text" placeholder="Full name (case-insensitive match)" />
    <button id="btnLogin">Login</button>
    <div class="muted">Use your ID and full name to login and mark attendance.</div>
    <a href="/dashboard">Back to dashboard</a>
  </div>

<script>
document.getElementById('btnLogin').addEventListener('click', async () => {
  const id = document.getElementById('sid').value.trim();
  const name = document.getElementById('sname').value.trim();
  if (!id || !name) { alert('Both fields required'); return; }
  const res = await fetch('/api/login', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({id, name}) });
  const data = await res.json();
  if (res.status === 200 && data.status === 'success') {
    window.location.href = data.redirect;
  } else {
    alert(data.message || 'Login failed');
  }
});
</script>
</body>
</html>
    """)

# --------------------
# Attendance page for single student
# --------------------
@app.route('/attendance/<int:student_id>')
def attendance_page(student_id):
    s = find_student(student_id)
    if not s:
        return "<h3>Student not found</h3>", 404
    return render_template_string("""
<!doctype html>
<html>
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>Attendance - {{student.name}}</title>
  <style>
    body{font-family:Arial;background:#f7fbff;padding:20px}
    .card{max-width:600px;margin:40px auto;background:#fff;padding:20px;border-radius:10px;box-shadow:0 10px 30px rgba(16,24,40,0.06)}
    h2{margin:0 0 6px 0}
    .muted{color:#6b7280;margin-bottom:12px}
    button{padding:10px 14px;background:#059669;color:#fff;border:none;border-radius:8px;cursor:pointer}
    .info{margin-top:12px;padding:8px;background:#eefbf6;border-radius:8px}
    .danger{background:#fff1f2;color:#b91c1c;padding:8px;border-radius:8px;margin-top:10px}
    a{display:inline-block;margin-top:10px;color:#2563eb}
  </style>
</head>
<body>
  <div class="card">
    <h2>Welcome, {{student.name}}</h2>
    <div class="muted">Grade {{student.grade}} • Section {{student.section}}</div>

    <div>
      <button id="btnMark">Mark Present</button>
      <a href="/login" style="margin-left:12px">Back to login</a>
    </div>

    <div id="statusBox" class="info" style="display:none"></div>

    <div style="margin-top:12px">
      <h4>Today's attendance status</h4>
      <div id="todayStatus" class="muted">Loading...</div>
    </div>

    <div class="danger" style="display:none" id="already">You have already marked attendance for today.</div>
  </div>

<script>
const sid = {{student.id}};
async function checkStatus() {
  const today = new Date().toISOString().slice(0,10);
  const res = await fetch('/api/attendance?student_id=' + sid + '&date=' + today);
  const data = await res.json();
  if (data.status === 'success' && data.attendance.length) {
    const a = data.attendance[0];
    document.getElementById('todayStatus').innerText = a.status + ' at ' + new Date(a.timestamp).toLocaleTimeString();
    document.getElementById('already').style.display = 'block';
    document.getElementById('btnMark').disabled = true;
  } else {
    document.getElementById('todayStatus').innerText = 'Not marked yet';
    document.getElementById('already').style.display = 'none';
    document.getElementById('btnMark').disabled = false;
  }
}

document.getElementById('btnMark').addEventListener('click', async () => {
  const res = await fetch('/api/attendance', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({student_id: sid, status: 'Present'}) });
  const data = await res.json();
  if (res.status === 201 && data.status === 'success') {
    document.getElementById('statusBox').style.display = 'block';
    document.getElementById('statusBox').innerText = 'Attendance marked: ' + data.attendance.date + ' ' + new Date(data.attendance.timestamp).toLocaleTimeString();
    checkStatus();
  } else {
    alert(data.message || 'Could not mark attendance');
    checkStatus();
  }
});

window.addEventListener('load', checkStatus);
</script>
</body>
</html>
    """, student=s)

# --------------------
# Utility endpoint: clear today's attendance (admin)
# --------------------
@app.route('/api/attendance/clear', methods=['POST'])
def api_clear_attendance():
    d = request.args.get('date') or today_str()
    global attendance
    before = len(attendance)
    attendance = [a for a in attendance if a['date'] != d]
    cleared = before - len(attendance)
    return jsonify({"status": "success", "cleared": cleared}), 200

# --------------------
# small convenience route for AJAX path used by admin script (attendance fetch)
# --------------------
@app.route('/api/attendance', methods=['POST'])
def api_attendance_post_alias():
    # This route duplicates POST /api/attendance to ensure both GET and POST exist under same path.
    data = request.get_json() or {}
    # forward to api_post_attendance handler logic
    return api_post_attendance()

# --------------------
# Run
# --------------------
if __name__ == '__main__':
    app.run(debug=True)
