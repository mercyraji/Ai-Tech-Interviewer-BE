from flask import Flask, request, jsonify
import sqlitecloud
import os
from dotenv import load_dotenv

# Function Imports
from getLeetCode import getLeetCodeInfo
from generateProblems import generate_problem

load_dotenv()

app = Flask(__name__)

# Configure SQLiteCloud connection
DATABASE_URL = os.getenv('SQLITECLOUD_CONN_STRING')
DATABASE_NAME = os.getenv('SQLITECLOUD_DB_NAME')

def get_connection():
    conn = sqlitecloud.connect(DATABASE_URL)
    conn.execute(f"USE DATABASE {DATABASE_NAME}")
    return conn

# This function will create the necessary tables if they don't exist
def initialize_database():
    conn = get_connection()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            uid TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            leetcode_username TEXT UNIQUE,
            user_level_description TEXT NOT NULL,
            overall_ratio FLOAT,
            easy_ratio FLOAT,
            medium_ratio FLOAT,
            hard_ratio FLOAT,
            current_goal TEXT
        )
    ''')
    conn.close()

@app.route('/api/message', methods=['GET'])
def get_message():
    return jsonify({'message': 'Hello from Flask!'})

@app.route('/api/createUser', methods=['POST'])
def create_user():
    data = request.get_json()
    uid = data['uid']
    email = data['email']
    leetcode_username = data['leetcodeUsername']
    user_level_description = data['levelDescription']

    # Fetching LeetCode stats
    easy_ratio, medium_ratio, hard_ratio, overall_ratio = getLeetCodeInfo(leetcode_username)
    print("*****************\n", easy_ratio, "", medium_ratio, "", hard_ratio, "", overall_ratio, "\n*****************")

    conn = get_connection()
    conn.execute('''
        INSERT INTO users (uid, email, leetcode_username, user_level_description, overall_ratio, easy_ratio, medium_ratio, hard_ratio)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (uid, email, leetcode_username, user_level_description, overall_ratio, easy_ratio, medium_ratio, hard_ratio))
    conn.close()

    return jsonify({'message': 'User created successfully'}), 201

@app.route('/api/generateProblem', methods=['POST'])
def generate_problem_endpoint():
    data = request.get_json()
    uid = data['uid']

    conn = get_connection()
    cursor = conn.execute('SELECT * FROM users WHERE uid = ?', (uid,))
    user = cursor.fetchone()
    conn.close()
    
    print(user)
    
    print(user[0])

    if not user:
        return jsonify({'error': 'User not found'}), 404

    user_level_description = user[3]
    easy_ratio = user[4]
    medium_ratio = user[5]
    hard_ratio = user[6]
    overall_ratio = user[7]

    problem = generate_problem(user_level_description, easy_ratio, medium_ratio, hard_ratio, overall_ratio)
    return jsonify({'problem': problem})

if __name__ == '__main__':
    initialize_database()
    app.run(debug=True, port=5000)
