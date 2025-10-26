from flask import Flask, jsonify, request, render_template_string
from datetime import datetime
import re

app = Flask(__name__)

# In-memory "database"
students = [
    {"id": 1, "name": "John Doe", "grade": 10, "section": "Zechariah"},
    {"id": 2, "name": "Jane Smith", "grade": 10, "section": "Zechariah"}
]

# Helpers
def now_iso():
    return datetime.utcnow().isoformat() + "Z"

def make_response(payload=None, status='success', code=200, message=None):
    body = {
        "status": status,
        "timestamp": now_iso()
    }
    if message:
        body["message"] = message
    if payload is not None:
        body.update(payload)
    return jsonify(body), code

def find_student(student_id):
    return next((s for s in students if s["id"] == student_id), None)

# Frontend: single route with inline CSS + JS
@app.route('/')
@app.route('/dashboard')
def dashboard():
    return render_template_string("""
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>Student Dashboard</title>
  <style>
    :root{
      --bg:#f7fbff;
      --card:#ffffff;
      --accent:#375aeb;
      --muted:#6b7280;
    }
    body{font-family:Inter, system-ui, -apple-system, 'Segoe UI', Roboto, Arial; background:var(--bg); margin:0; padding:24px}
    .container{max-width:1000px;margin:0 auto}
    header h1{margin:0 0 4px}
    .muted{color:var(--muted)}
    .card{background:var(--card);padding:16px;border-radius:12px;box-shadow:0 6px 18px rgba(16,24,40,0.06);margin-top:16px}
    .controls{display:flex;gap:8px;margin-top:12px}
    .controls input{flex:1;padding:8px;border-radius:8px;border:1px solid #e6eef8}
    button{background:var(--accent);color:white;border:none;padding:8px 12px;border-radius:8px;cursor:pointer}
    table{width:100%;border-collapse:collapse;margin-top:8px}
    thead th{text-align:left;padding:8px;border-bottom:1px solid #eee}
    tbody td{padding:8px;border-bottom:1px solid #f3f4f6}
    .row{display:flex;gap:8px;align-items:center;margin-top:8px}
    .row label{width:80px}
    .row input{flex:1;padding:8px;border-radius:8px;border:1px solid #e6eef8}
    .actions{margin-top:12px;display:flex;gap:8px}
    footer{margin-top:12px;color:var(--muted)}
    .small-btn{background:#e5e7eb;color:#111;padding:6px 8px;border-radius:8px}
    @media (max-width:600px){
      .row{flex-direction:column;align-items:flex-start}
      .row label{width:auto}
    }
  </style>
</head>
<body>
  <div class="container">
    <header>
      <h1>Student Dashboard</h1>
      <p class="muted">Manage students — create, update, delete, and search.</p>
    </header>

    <section class="controls">
      <input id="search" placeholder="Search by name..." />
      <button id="btnRefresh" class="small-btn">Refresh</button>
      <button id="btnClearSearch" class="small-btn">Clear</button>
    </section>

    <section class="card">
      <h2>Students</h2>
      <table id="studentsTable">
        <thead>
          <tr><th>ID</th><th>Name</th><th>Grade</th><th>Section</th><th>Actions</th></tr>
        </thead>
        <tbody></tbody>
      </table>
    </section>

    <section class="card">
      <h2>Add / Edit Student</h2>
      <form id="studentForm">
        <input type="hidden" id="studentId" />
        <div class="row"><label>Name</label><input id="name" required /></div>
        <div class="row"><label>Grade</label><input id="grade" type="number" required min="1" /></div>
        <div class="row"><label>Section</label><input id="section" required /></div>
        <div class="actions">
          <button type="submit">Save</button>
          <button type="button" id="formClear" class="small-btn">Clear</button>
        </div>
      </form>
    </section>

    <footer>
      <small>API timestamped responses • Built with Flask • Single-file app</small>
    </footer>
  </div>

  <script>
    const apiBase = '/api';

    async function fetchStudents(q = '') {
      const params = new URLSearchParams();
      if (q) params.set('q', q);
      const res = await fetch(apiBase + '/students' + (q ? ('?' + params.toString()) : ''));
      return await res.json();
    }

    function renderStudents(list) {
      const tbody = document.querySelector('#studentsTable tbody');
      tbody.innerHTML = '';
      (list || []).forEach(s => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
          <td>${s.id}</td>
          <td>${s.name}</td>
          <td>${s.grade}</td>
          <td>${s.section}</td>
          <td>
            <button data-id="${s.id}" class="editBtn small-btn">Edit</button>
            <button data-id="${s.id}" class="delBtn small-btn">Delete</button>
          </td>
        `;
        tbody.appendChild(tr);
      });
    }

    async function refresh() {
      const q = document.getElementById('search').value.trim();
      const resp = await fetchStudents(q);
      if (resp.status === 'success') {
        renderStudents(resp.students || []);
      } else {
        alert(resp.message || 'Failed to load students');
      }
    }

    async function saveStudent(e) {
      e.preventDefault();
      const id = document.getElementById('studentId').value;
      const payload = {
        name: document.getElementById('name').value.trim(),
        grade: parseInt(document.getElementById('grade').value, 10),
        section: document.getElementById('section').value.trim()
      };
      if (!payload.name || !payload.section || Number.isNaN(payload.grade)) {
        alert('Please fill all fields correctly');
        return;
      }

      if (id) {
        const res = await fetch(apiBase + '/students/' + id, {
          method: 'PUT',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (data.status === 'success') {
          clearForm(); refresh();
        } else alert(data.message || 'Update failed');
      } else {
        const res = await fetch(apiBase + '/students', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (res.status === 201 || data.status === 'success') {
          clearForm(); refresh();
        } else alert(data.message || 'Create failed');
      }
    }

    function clearForm() {
      document.getElementById('studentId').value = '';
      document.getElementById('name').value = '';
      document.getElementById('grade').value = '';
      document.getElementById('section').value = '';
    }

    async function handleTableClick(e) {
      if (e.target.matches('.editBtn')) {
        const id = e.target.dataset.id;
        const res = await fetch(apiBase + '/students/' + id);
        const data = await res.json();
        if (data.status === 'success') {
          const s = data.student;
          document.getElementById('studentId').value = s.id;
          document.getElementById('name').value = s.name;
          document.getElementById('grade').value = s.grade;
          document.getElementById('section').value = s.section;
          window.scrollTo({top: document.body.scrollHeight, behavior: 'smooth'});
        } else alert(data.message || 'Could not load student');
      }

      if (e.target.matches('.delBtn')) {
        const id = e.target.dataset.id;
        if (!confirm('Delete student?')) return;
        const res = await fetch(apiBase + '/students/' + id, { method: 'DELETE' });
        const data = await res.json();
        if (data.status === 'success') refresh();
        else alert(data.message || 'Delete failed');
      }
    }

    // Bind events
    window.addEventListener('load', () => {
      refresh();
      document.getElementById('btnRefresh').addEventListener('click', refresh);
      document.getElementById('btnClearSearch').addEventListener('click', () => { document.getElementById('search').value = ''; refresh(); });
      document.getElementById('search').addEventListener('input', () => { refresh(); });
      document.getElementById('studentForm').addEventListener('submit', saveStudent);
      document.getElementById('formClear').addEventListener('click', clearForm);
      document.querySelector('#studentsTable tbody').addEventListener('click', handleTableClick);
    });
  </script>
</body>
</html>
    """)

# API routes
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
            return make_response(status='error', code=400, message='grade must be an integer')
    if section:
        results = [s for s in results if s.get('section', '').lower() == section.lower()]

    return make_response({'students': results})

@app.route('/api/students/<int:student_id>', methods=['GET'])
def api_get_student(student_id):
    student = find_student(student_id)
    if not student:
        return make_response(status='error', code=404, message='Student not found')
    return make_response({'student': student})

@app.route('/api/students', methods=['POST'])
def api_add_student():
    data = request.get_json() or {}
    name = data.get('name')
    grade = data.get('grade')
    section = data.get('section')

    if not name or grade is None or not section:
        return make_response(status='error', code=400, message='name, grade and section are required')
    try:
        grade = int(grade)
    except ValueError:
        return make_response(status='error', code=400, message='grade must be an integer')

    new_id = (students[-1]['id'] + 1) if students else 1
    student = {'id': new_id, 'name': name, 'grade': grade, 'section': section}
    students.append(student)
    return make_response({'student': student}, message='Student created'), 201

@app.route('/api/students/<int:student_id>', methods=['PUT'])
def api_update_student(student_id):
    student = find_student(student_id)
    if not student:
        return make_response(status='error', code=404, message='Student not found')

    data = request.get_json() or {}
    name = data.get('name', student['name'])
    grade = data.get('grade', student['grade'])
    section = data.get('section', student['section'])

    try:
        grade = int(grade)
    except ValueError:
        return make_response(status='error', code=400, message='grade must be an integer')

    student.update({'name': name, 'grade': grade, 'section': section})
    return make_response({'student': student}, message='Student updated')

@app.route('/api/students/<int:student_id>', methods=['DELETE'])
def api_delete_student(student_id):
    student = find_student(student_id)
    if not student:
        return make_response(status='error', code=404, message='Student not found')
    students.remove(student)
    return make_response(message='Student deleted')

@app.route('/api/health', methods=['GET'])
def api_health():
    return make_response({'uptime': 'ok'})

if __name__ == '__main__':
    app.run(debug=True)
