from flask import Flask, jsonify, request
app = Flask(__name__)

@app.route('/')
def home():
return "Welcome to my Flask API!"

@app.route('/student')
def get_student():
return jsonify({
"name": "Your Name",
"grade": 10,
"section": "Zechariah"
})
