from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from getLeetCode import getLeetCodeInfo
from generateProblems import generate_problem 
# from evaluateProblems import evaluate_response

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class Users(db.Model):
    uid = db.Column(db.String(120), primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    leetcode_username = db.Column(db.String(80), unique=True, nullable=True) # make sure this follows PEP8 naming conventions later
    user_level_description = db.Column(db.String(500), nullable=False) # find a better name, essentially the initial user input describing their goal
    
    # Ratio based on submissions
    overall_ratio = db.Column(db.Float, nullable=True)
    easy_ratio = db.Column(db.Float, nullable=True)
    medium_ratio = db.Column(db.Float, nullable=True)
    hard_ratio = db.Column(db.Float, nullable=True)
    
    # Input their goal
    current_goal = db.Column(db.String(200), nullable=True)
    
    def __repr__(self):
        return f'<User {self.name}>'

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
    print("*****************\n",easy_ratio, "", medium_ratio,"",hard_ratio, "", overall_ratio, "\n*****************")

    new_user = Users(
        uid=uid,
        email=email,
        leetcode_username=leetcode_username,
        user_level_description=user_level_description,
        overall_ratio=overall_ratio,
        easy_ratio=easy_ratio,
        medium_ratio=medium_ratio,
        hard_ratio=hard_ratio
    )
    db.session.add(new_user)
    db.session.commit()

    return jsonify({'message': 'User created successfully'}), 201

@app.route('/api/generateProblem', methods=['POST'])
def generate_problem_endpoint():
    data = request.get_json()
    uid = data['uid']
    
    user = Users.query.filter_by(uid=uid).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    user_level_description = user.user_level_description 
    easy_ratio = user.easy_ratio 
    medium_ratio = user.medium_ratio 
    hard_ratio = user.hard_ratio 
    overall_ratio = user.overall_ratio 
    
    problem = generate_problem(user_level_description, easy_ratio, medium_ratio, hard_ratio, overall_ratio)
    return jsonify({'problem': problem}) 

if __name__ == '__main__': 
    with app.app_context(): 
        db.create_all() 
    app.run(debug=True) 
