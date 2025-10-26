from flask import Flask, jsonify, request, render_template_string

app = Flask(__name__)

# Dummy Database
students = [
    {"id": 1, "name": "John Doe", "grade": 10, "section": "Zechariah"},
    {"id": 2, "name": "Jane Smith", "grade": 10, "section": "Zechariah"}
]

@app.route('/')
def home():
    return "Welcome to my Flask API!"

# === API ROUTES === #

@app.route('/api/students', methods=['GET'])
def get_students():
    query = request.args.get("q")
    if query:
        result = [s for s in students if query.lower() in s["name"].lower()]
        return jsonify({"status": "success", "students": result}), 200
    return jsonify({"status": "success", "students": students}), 200

@app.route('/api/students/<int:student_id>', methods=['GET'])
def get_student(student_id):
    student = next((s for s in students if s["id"] == student_id), None)
    if student:
        return jsonify({"status": "success", "student": student}), 200
    return jsonify({"status": "error", "message": "Student not found"}), 404

@app.route('/api/students', methods=['POST'])
def add_student():
    data = request.get_json()
    if not data or "name" not in data or "grade" not in data or "section" not in data:
        return jsonify({"status": "error", "message": "Invalid data"}), 400
    new_student = {
        "id": students[-1]["id"] + 1 if students else 1,
        "name": data["name"],
        "grade": data["grade"],
        "section": data["section"]
    }
    students.append(new_student)
    return jsonify({"status": "success", "student": new_student}), 201

@app.route('/api/students/<int:student_id>', methods=['PUT'])
def update_student(student_id):
    student = next((s for s in students if s["id"] == student_id), None)
    if not student:
        return jsonify({"status": "error", "message": "Student not found"}), 404

    data = request.get_json()
    student["name"] = data.get("name", student["name"])
    student["grade"] = data.get("grade", student["grade"])
    student["section"] = data.get("section", student["section"])
    return jsonify({"status": "success", "student": student}), 200

@app.route('/api/students/<int:student_id>', methods=['DELETE'])
def delete_student(student_id):
    global students
    students = [s for s in students if s["id"] != student_id]
    return jsonify({"status": "success", "message": "Student deleted"}), 200

# === DASHBOARD UI === #

@app.route('/dashboard')
def dashboard():
    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
<title>Student Dashboard</title>
<style>
body { font-family: Arial; background: #f4f4f4; padding: 20px; }
table { width: 100%; border-collapse: collapse; margin-top: 20px; }
th, td { border: 1px solid #ccc; padding: 8px; text-align: left; }
th { background: #333; color: white; }
button { padding: 5px 10px; }
input { padding: 6px; margin: 5px; }
</style>
</head>
<body>
<h2>Student Dashboard</h2>

<input id="name" type="text" placeholder="Name">
<input id="grade" type="number" placeholder="Grade">
<input id="section" type="text" placeholder="Section">
<button onclick="addStudent()">Add</button>

<table>
<thead>
<tr><th>ID</th><th>Name</th><th>Grade</th><th>Section</th><th>Action</th></tr>
</thead>
<tbody id="studentTable"></tbody>
</table>

<script>
async function loadStudents() {
    const res = await fetch('/api/students');
    const data = await res.json();
    const table = document.getElementById("studentTable");
    table.innerHTML = "";
    data.students.forEach(s => {
        table.innerHTML += `
        <tr>
            <td>${s.id}</td>
            <td>${s.name}</td>
            <td>${s.grade}</td>
            <td>${s.section}</td>
            <td><button onclick="deleteStudent(${s.id})">Delete</button></td>
        </tr>`;
    });
}

async function addStudent() {
    const name = document.getElementById("name").value;
    const grade = document.getElementById("grade").value;
    const section = document.getElementById("section").value;

    await fetch('/api/students', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({name, grade, section})
    });
    loadStudents();
}

async function deleteStudent(id) {
    await fetch('/api/students/' + id, { method: 'DELETE' });
    loadStudents();
}

loadStudents();
</script>

</body>
</html>
""")

if __name__ == '__main__':
    app.run(debug=True)
