from flask import Flask, render_template, request, redirect, url_for
import sqlite3
from agent import run_agent  
app = Flask(__name__)
# handles all user intaractions 
@app.route('/')
def index():
    conn = sqlite3.connect('reports.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT id, query, timestamp FROM reports ORDER BY timestamp DESC")
    reports = c.fetchall()
    conn.close()
    return render_template('index.html', reports=reports)

@app.route('/report/<int:report_id>')
def view_report(report_id):
    conn = sqlite3.connect('reports.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM reports WHERE id = ?", (report_id,))
    report = c.fetchone()
    conn.close()
    if report:
        return render_template('report.html', report=report)
    else:
        return "Report not found", 404

@app.route('/search', methods=['POST'])
def search():
    query = request.form['query']
    result = run_agent(query)
    # reloads the page to show new report
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)