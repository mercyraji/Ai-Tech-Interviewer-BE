from flask import Flask, request, jsonify
from flask_cors import CORS
from database.models import User, UserHistory
import openai
import os

# Function Imports
from APIs.getLeetCode import getLeetCodeInfo
from APIs.generateProblems import generate_problem
from APIs.evaluateResponse import evaluate_response, evaluate_speech, parse_evaluation
from messaging.emailing import send_email

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

openai.api_key = os.getenv("OPEN_AI_API_KEY")


def get_ai_response(prompt, problem):
    system_prompt = (
        f"""
        You are an interview assistant. You are presenting a coding problem to the user and helping them through the problem. 

        You must not give away the solution directly. If the user asks for hints, provide only subtle hints that guide them in the right direction. Only give hints if the user provides context about their current progress or what they have tried so far. Also, don't answer more than what is needed. If a user asks something that can be answered in a yes or no response, return just yes or no

        Make your answers short and concise. No more than 2 sentences

        Here is the problem: \n\n"
        {problem}\n\n"
        User: {prompt}\n\n"
        Remember, do not give the solution directly.
        """
    )

    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message["content"].strip()


@app.route("/api/message", methods=["GET"])
def get_message():
    return jsonify({"message": "Hello from Flask!"})


@app.route("/api/createUser", methods=["POST"])
def create_user():
    data = request.get_json()
    uid = data["uid"]
    username = data['username']
    email = data["email"]
    leetcode_username = None
    user_level_description = "N/A"

    User.add_user(uid, username, email, leetcode_username, user_level_description)
    """try:
        send_email(to_email=email,
                   subject="Welcome to Interviewer AI!",
                   body="Thank you for signing up. We're excited to apart of your technical interviewing journey!")
    except Exception as e:
        print(f"Failed to send email: {str(e)}")
"""
    return jsonify({"message": "User created successfully"}), 201


@app.route("/api/newUser", methods=["POST"])
def new_user():
    data = request.get_json()
    # print(f"Recieved data: {data}")
    uid = data["uid"]
    leetcode_username = data["leetcode_username"]
    coding_level = data["coding_level"]
    goal = data["goal"]
    upcoming_interview = data["upcoming_interview"]

    overall_ratio, easy_ratio, medium_ratio, hard_ratio = None, None, None, None

    if leetcode_username != "N/A":
        overall_ratio, easy_ratio, medium_ratio, hard_ratio = getLeetCodeInfo(
            leetcode_username
        )

    # print(f"Updating user: {uid}, {leetcode_username}, {coding_level}, {goal}, {upcoming_interview}, {overall_ratio}, {easy_ratio}, {medium_ratio}, {hard_ratio}")

    User.update_user(
        uid,
        leetcode_username,
        coding_level,
        goal,
        upcoming_interview,
        overall_ratio,
        easy_ratio,
        medium_ratio,
        hard_ratio,
    )

    return jsonify({"message": "New user info received"}), 201


@app.route('/api/login', methods=['POST'])
def log_user():
    data = request.get_json()
    username = data.get('username')
    email = User.get_email(username)

    if email is not None:
        return jsonify({'email': email[0]}), 201
    else:
        return jsonify({'error': 'Username not found'}), 404


@app.route("/api/generateProblem", methods=["POST"])
def generate_problem_endpoint():
    data = request.get_json()
    uid = data["uid"]
    language = data["language"]

    user = User.get_user_id(uid)

    if not user:
        return jsonify({"error": "User not found"}), 404

    user_level_description = user[4]
    easy_ratio = user[6]
    medium_ratio = user[7]
    hard_ratio = user[8]
    overall_ratio = user[5]

    problem = generate_problem(
        user_level_description,
        easy_ratio,
        medium_ratio,
        hard_ratio,
        overall_ratio,
        language,
    )
    return jsonify({"problem": problem})


@app.route("/api/evaluateResponse", methods=["POST"])
def evaluate_response_endpoint():
    data = request.get_json()
    problem = data["problem"]
    response = data["userResponse"]
    uid = data["uid"]
    speech_input = data.get('speechInput', 'N/A')

    if problem and response and uid:
        code_evaluation = evaluate_response(problem, response)
        code_evaluation2, feedback, final_grade = parse_evaluation(code_evaluation)

        speech_evaluation2 = speech_feedback = final_speech_grade = None
        if speech_input != "N/A":
            speech_evaluation = evaluate_speech(problem, response, speech_input)
            speech_evaluation2, speech_feedback, final_speech_grade = parse_evaluation(speech_evaluation)
            print(speech_evaluation2, speech_feedback, final_speech_grade)

        UserHistory.update_history(uid, problem, response, code_evaluation2, feedback, int(final_grade),
                                   speech_evaluation2, speech_feedback, final_speech_grade)

        response_data = {
            "code_evaluation": {
                "evaluation": code_evaluation2,
                "feedback": feedback,
                "final_grade": final_grade
            },
            "speech_evaluation": {
                "evaluation": speech_evaluation2,
                "feedback": speech_feedback,
                "final_grade": final_speech_grade
            } if speech_input != "N/A" else None
        }

        print(response_data)
        return jsonify(response_data)

    return jsonify({"evaluation": "error"})


@app.route('/api/deleteUser', methods=['POST'])
def delete_user():
    data = request.get_json()
    uid = data.get('uid')

    # user will already be logged into their account
    # so no need to check if user exists
    User.remove_user(uid)

    return jsonify({'message': 'User removed successfully'}), 201


@app.route('/api/updateGoal', methods=['POST'])
def update_goal():
    data = request.get_json()
    uid = data['uid']
    goal = data['current_goal']

    User.update_goal(uid, goal)

    return jsonify({'message': 'User\'s goal updated successfully'}), 201


@app.route('/api/updateInterview', methods=['POST'])
def update_interview():
    data = request.get_json()
    uid = data['uid']
    interview = data['upcoming_interview']

    User.update_interview(uid, interview)

    return jsonify({'message': 'User\'s interview updated successfully'}), 201


@app.route('/api/updateLevel', methods=['POST'])
def update_level():
    data = request.get_json()
    uid = data['uid']
    level_description = data['level_description']

    User.update_level(uid, level_description)

    return jsonify({'message': 'User\'s level updated successfully'}), 201


@app.route("/api/sendEmail", methods=["POST"])
def send_email_endpoint():
    data = request.get_json()
    to_email = data["to_email"]
    subject = data["subject"]
    body = data["body"]
    result = send_email(to_email, subject, body)
    return jsonify({"message": result})


@app.route('/api/getUsers', methods=['GET'])
def get_user():
    uid = request.args.get('uid')
    user = User.get_user_id(uid)
    code_grades = UserHistory.get_code_grades(uid)  # gets final grades & corresponding saved dates
    speech_grades = UserHistory.get_speech_grades(uid)
    attempts = UserHistory.count_history(uid)  # gets the number of attempts for each saved date

    # user should exist
    return jsonify({
        'user':
            {'username': user[2],
             'level_description': user[4],
             'current_goal': user[9],
             'upcoming_interview': user[10],
             'signup_date': user[11]
             },
        'code_grades': code_grades,
        'speech_grades': speech_grades,
        'attempts': attempts
    })


@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json()
    user_message = data.get('message')
    problem = data.get('problem')
    ai_response = get_ai_response(user_message, problem)
    return jsonify({"ai_response": ai_response})


@app.route("/api/sendSignInEmail", methods=["POST"])
def send_sign_in_email():
    data = request.get_json()
    to_email = data["to_email"]
    try:
        send_email(
            to_email=to_email,
            subject="Successful Sign-In",
            body="You have successfully signed in to your account. You are one step closer to mastering the technicual interview!"
        )
        return jsonify({"message": "Sign-in email sent successfully"}), 200
    except Exception as e:
        return jsonify({"message": f"Failed to send sign-in email: {str(e)}"}), 500


@app.route("/api/getUserHistory", methods=["GET"])
def get_user_history():
    try:
        uid = request.args.get("uid")
        user = User.get_user_id(uid)
        if not user:
            return jsonify({"error": "User not found"}), 404

        history = UserHistory.get_user_history(uid)

        return jsonify({"history": history})
    except Exception as e:
        #logging.error(f"Failed to get user history: {str(e)}")
        return jsonify({"message": f"Failed to get user history: {str(e)}"}), 500



if __name__ == "__main__":
    from database.initialization import initialize_database

    initialize_database()
    app.run(debug=True, port=5000)
