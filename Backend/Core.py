import openai
from openai import OpenAI
from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit
import os

app = Flask(__name__)
socketio = SocketIO(app)

# Initialize the OpenAI client
client = OpenAI()

# Global Variables
turn = 1
conversation_history = []
initial_questions = {
    "plaintiff": [
        "What kind of dispute is this?",
        "How much are you seeking in damages?",
        "How much do you earn per hour?",
        "What's the lowest payout you would take?"
    ],
    "defendant": [
        "How much are you seeking in damages?",
        "Do you confirm that the plaintiff is seeking $xxxx in damages?",
        "How much do you earn per hour?",
        "How much would you pay to avoid this?",
        "What's the max you would pay to the plaintiff?"
    ]
}
plaintiff_profile = {}
defendant_profile = {}
plaintiff_question_index = 0
defendant_question_index = 0

# Initial Directions for the AI Mediator
directions = "\nYou are an AI mediator facilitating a dispute resolution between two parties. Your primary goal is to guide both parties toward a fair and mutually agreeable solution. You will only address one user at a time based on whose turn it is. Always respond to the current user and ensure the other user's concerns are considered in your mediation. Here are your key responsibilities and objectives: Tone and Language: - Maintain a **professional**, **neutral**, and **inviting** tone throughout the conversation. - Be **calm**, **polite**, and **understanding** in your responses to ensure that both parties feel heard. - Use **clear**, **concise**, and **neutral language** when summarizing each party's input. - Avoid taking sides or showing bias toward one party. Always remain impartial. Output Guidelines: 1. **Summarize** the current user's input, highlighting their concerns, arguments, or requests. 2. After summarizing, offer **balanced suggestions** or potential solutions that consider the concerns of both parties. 3. Ensure the current user understands how the other party might respond and encourage them to work toward a compromise. 4. Use your responses to **de-escalate** tensions if necessary and focus on finding common ground.\n"


# WebSocket to handle communication between both parties
@socketio.on('connect')
def handle_connect():
    emit('response', {'message': 'Connected to the Mediation Server'})

# WebSocket to ask initial questions and collect responses
@socketio.on('initial_questions')
def handle_initial_questions(data):
    global plaintiff_question_index, defendant_question_index, plaintiff_profile, defendant_profile

    user_type = data['user_type']  # 'plaintiff' or 'defendant'
    answer = data['answer']  # Answer to the last question

    if user_type == "plaintiff":
        question_index = plaintiff_question_index
        if question_index < len(initial_questions["plaintiff"]):
            if question_index == 1:  # Update question with actual damages
                initial_questions["defendant"][1] = f"Do you confirm that the plaintiff is seeking {plaintiff_profile['damages_seeking']} in damages?"

            if question_index == 0:
                plaintiff_profile['dispute_type'] = answer
            elif question_index == 1:
                plaintiff_profile['damages_seeking'] = answer
            elif question_index == 2:
                plaintiff_profile['earnings_per_hour'] = answer
            elif question_index == 3:
                plaintiff_profile['lowest_payout'] = answer

            plaintiff_question_index += 1
            if plaintiff_question_index < len(initial_questions["plaintiff"]):
                next_question = initial_questions["plaintiff"][plaintiff_question_index]
                emit('next_question', {'next_question': next_question})
            else:
                emit('message', {'message': "Plaintiff questions completed."})

    elif user_type == "defendant":
        question_index = defendant_question_index
        if question_index < len(initial_questions["defendant"]):

            if question_index == 0:
                defendant_profile['damages_seeking'] = answer
            elif question_index == 1:
                defendant_profile['confirm_damages'] = answer
            elif question_index == 2:
                defendant_profile['earnings_per_hour'] = answer
            elif question_index == 3:
                defendant_profile['pay_to_avoid'] = answer
            elif question_index == 4:
                defendant_profile['max_payment'] = answer

            defendant_question_index += 1
            if defendant_question_index < len(initial_questions["defendant"]):
                next_question = initial_questions["defendant"][defendant_question_index]
                emit('next_question', {'next_question': next_question})
            else:
                plaintiff_history = f"\nPlaintiff Profile: {plaintiff_profile}\n"
                defendant_history = f"\nDefendant Profile: {defendant_profile}\n"
                conversation_history.append(plaintiff_history)
                conversation_history.append(defendant_history)

                conversation_history.append(directions)
                emit('message', {'message': "Defendant questions completed. Mediation ready to start."})

# WebSocket to handle turn-based mediation
@socketio.on('mediate')
def handle_mediate(data):
    global turn, conversation_history

    plaintiff_name = data['plaintiff_name']
    defendant_name = data['defendant_name']

    if turn == 1:
        current_user = plaintiff_name
        other_user = defendant_name
    else:
        current_user = defendant_name
        other_user = plaintiff_name

    user_input = data['user_input']
    conversation_history.append(f"{current_user}: {user_input}")

    history = "\n".join(conversation_history)
    prompt = f"\n{current_user} has raised the following points: {user_input}. As a mediator, please suggest a fair resolution to {other_user}, addressing {current_user}'s concerns."

    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": history},
            {"role": "user", "content": prompt}
        ]
    )

    ai_response = completion.choices[0].message.content
    conversation_history.append(f"AI Mediator to {other_user}: {ai_response}")

    turn = 1 if turn == 2 else 2

    emit('ai_response', {'ai_response': ai_response, 'next_user': other_user})


# Flask root to confirm Flask is running
@app.route('/')
def index():
    return "Mediation API with WebSocket is running."


if __name__ == '__main__':
    socketio.run(app, debug=True)
