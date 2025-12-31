from flask import Flask, jsonify, send_file, request, Response, stream_with_context
import sqlite3
import os
import subprocess
import sys
import json
import common.city_code

app = Flask(__name__)

def get_db_data(db_path):
    if not os.path.exists(db_path):
        return []
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='air_info'")
        if not cursor.fetchone():
            conn.close()
            return []
        cursor.execute('SELECT departcity, arrivalcity, date, price, platform FROM air_info')
        rows = cursor.fetchall()
        conn.close()
        data = []
        for row in rows:
            data.append({
                "departcity": row["departcity"],
                "arrivalcity": row["arrivalcity"],
                "date": row["date"],
                "price": row["price"],
                "platform": row["platform"]
            })
        return data
    except Exception as e:
        print(f"Error reading {db_path}: {e}")
        return []

@app.route('/')
def index():
    return send_file('index.html')

@app.route('/api/cities')
def get_cities():
    return jsonify(common.city_code.all_cities)

@app.route('/api/run_script', methods=['POST'])
def run_script():
    data = request.json or {}
    script_type = data.get('type')
    cities = data.get('cities')
    cookie = data.get('cookie')

    if script_type == 'feizhu':
        script_name = 'feizhu.py'
    elif script_type == 'xiecheng':
        script_name = 'xiecheng.py'
    else:
        return jsonify({"error": "Invalid script type"}), 400

    def generate():
        cmd = [sys.executable, script_name]
        if cities:
            cmd.extend(['--cities', json.dumps(cities)])
        if cookie and script_type == 'feizhu':
            cmd.extend(['--cookie', cookie])

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            cwd=os.path.dirname(os.path.abspath(__file__)),
            bufsize=1
        )

        for line in process.stdout:
            yield f"data: {line}\n\n"

        process.wait()
        if process.returncode == 0:
            yield "data: [DONE]\n\n"
        else:
            yield f"data: [ERROR] Process exited with code {process.returncode}\n\n"

    return Response(stream_with_context(generate()), mimetype='text/event-stream')

@app.route('/api/data')
def get_data():
    feizhu_data = get_db_data('feizhu_info.sqlite')
    xiecheng_data = get_db_data('xiecheng_info.sqlite')
    return jsonify(feizhu_data + xiecheng_data)

if __name__ == '__main__':
    print("Starting server at http://localhost:5001")
    app.run(debug=True, port=5001)
