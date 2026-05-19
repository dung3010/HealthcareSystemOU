from flask import Flask, render_template
app = Flask(__name__)

@app.route('/')
def index():
    return render_template('dashboard.html')

@app.route('/patient/book')
def book():
    return render_template('patient/book.html')

@app.route('/patient/dashboard')
def dashboard():
    return render_template('patient/dashboard.html')