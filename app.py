from flask import Flask, jsonify, request

app = Flask(__name__)

# Dummy database (list of students)
students = [
    {"id": 1, "name": "John Doe", "grade": 10, "section": "Zechariah"},
    {"id": 2, "name": "Jane Smith", "grade": 10, "section": "Zechariah"}
]

@app.route('/')
def home():
    return "Welcome to my Flask API!"

# GET all students
@app.route('/students', methods=['GET'])
def get_students():
    return jsonify(students), 200

# GET single student by ID
@app.route('/students/<int:student_id>', methods=['GET'])
def get_student(student_id):
    student = next((s for s in students if s["id"] == student_id), None)
    if student:
        return jsonify(student), 200
    return jsonify({"error": "Student not found"}), 404

# POST - Add new student
@app.route('/students', methods=['POST'])
def add_student():
    data = request.get_json()
    
    # Validate
    if not data or "name" not in data or "grade" not in data or "section" not in data:
        return jsonify({"error": "Invalid data"}), 400

    new_student = {
        "id": students[-1]["id"] + 1 if students else 1,
        "name": data["name"],
        "grade": data["grade"],
        "section": data["section"]
    }

    students.append(new_student)
    return jsonify(new_student), 201

# Run server
if __name__ == '__main__':
    app.run(debug=True)
