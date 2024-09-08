import openai
from openai import OpenAI
from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit
import os
from datetime import datetime

app = Flask(__name__)
socketio = SocketIO(app)

# Initialize the OpenAI client
client = OpenAI()

# Global Variables
turn = 1
conversation_history = []
clients = {'plaintiff': None, 'defendant': None}  # Store socket connections
plaintiff_last_prices = []  # Track last 3 responses for plaintiff
defendant_last_prices = []  # Track last 3 responses for defendant
common_price_reached = False  # Track whether a common price has been agreed
plaintiff_agrees = False  # Track if plaintiff agrees to common price
defendant_agrees = False  # Track if defendant agrees to common price
plaintiff_name = ""
defendant_name = ""
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
courtCostTotal = 20 * 380 + 1500  # Court cost calculation: 20 hours * $380 + $1500

# Updated Directions for the AI Mediator
directions = """
You are an AI mediator facilitating a dispute resolution between two parties. Your primary goal is to guide both parties toward a fair and mutually agreeable solution. You will only address one user at a time based on whose turn it is. Always respond to the current user and ensure the other user's concerns are considered in your mediation.

Tone and Language:
- Maintain a **professional**, **neutral**, and **inviting** tone throughout the conversation.
- Be **calm**, **polite**, and **understanding** in your responses to ensure that both parties feel heard.
- Use **clear**, **concise**, and **neutral language** when summarizing each party's input.
- Avoid taking sides or showing bias toward one party. Always remain impartial.

Output Guidelines:
1. **Summarize** the current user's input, highlighting their concerns, arguments, or requests.
2. After summarizing, offer **balanced suggestions** or potential solutions that consider the concerns of both parties.
3. Ensure the current user understands how the other party might respond and encourage them to work toward a compromise.
4. Use your responses to **de-escalate** tensions if necessary and focus on finding common ground.
5. **When either party refuses to budge on their price or offer for three consecutive responses**, you should mention the potential costs they might face by going to court.
   - Inform them about the **courtCostTotal** (average court costs: $7600) and the **opportunityCost** (based on their hourly wage and the 20 hours spent in court).
   - Also remind them of the time commitment: **It may take up to a year to go to trial in California**.
6. **When a common price is reached**, prompt both parties to confirm that they agree to this price. If both confirm, the mediation ends successfully. If either party disagrees, continue with mediation.
"""

# Helper function to calculate court costs and opportunity cost
def calculate_costs(user_type):
    global courtCostTotal

    if user_type == "plaintiff":
        wage = float(plaintiff_profile['earnings_per_hour'])
        lowest_payout = float(plaintiff_profile['lowest_payout'])
        opportunityCost = wage * 20  # Time they won't be able to work
        adjusted_lowest_payout = lowest_payout - courtCostTotal
        return {"courtCostTotal": courtCostTotal, "opportunityCost": opportunityCost, "adjusted_lowest_payout": adjusted_lowest_payout}

    elif user_type == "defendant":
        wage = float(defendant_profile['earnings_per_hour'])
        max_payment = float(defendant_profile['max_payment'])
        opportunityCost = wage * 20  # Time they won't be able to work
        adjusted_max_payment = max_payment - courtCostTotal
        return {"courtCostTotal": courtCostTotal, "opportunityCost": opportunityCost, "adjusted_max_payment": adjusted_max_payment}


# Helper function to check if the last 3 prices are the same
def check_same_last_three(prices):
    return len(prices) >= 3 and prices[-1] == prices[-2] == prices[-3]


# Function to check if a common price has been reached
def check_common_price():
    global plaintiff_profile, defendant_profile
    plaintiff_price = float(plaintiff_profile['lowest_payout'])
    defendant_price = float(defendant_profile['max_payment'])

    # If the plaintiff's lowest payout is less than or equal to the defendant's max payment, a common price is reached
    return plaintiff_price <= defendant_price


# Function to confirm the common price with both users
@socketio.on('confirm_common_price')
def confirm_common_price(data):
    global common_price_reached, plaintiff_agrees, defendant_agrees, turn

    user_type = data['user_type']  # 'plaintiff' or 'defendant'
    user_agrees = data['agrees']  # True or False

    if user_type == 'plaintiff':
        plaintiff_agrees = user_agrees
    elif user_type == 'defendant':
        defendant_agrees = user_agrees

    # Check if both parties agree to the common price
    if plaintiff_agrees and defendant_agrees:
        # Both agreed, mediation ends
        common_price_reached = True
        generate_log("Mediation successfully concluded.")
        emit('ai_response', {'ai_response': "Both parties have agreed to the common price. Mediation successfully concluded."}, broadcast=True)
        return
    elif plaintiff_agrees or defendant_agrees:
        # One party agreed, continue to wait for the other party's response
        emit('ai_response', {'ai_response': f"Waiting for the other party to confirm the common price."})
        return
    else:
        # If one or both disagree, continue mediation
        common_price_reached = False
        emit('ai_response', {'ai_response': "One or both parties have disagreed. Continuing mediation."}, broadcast=True)
        return


# Function to generate and print the formatted text log
def generate_log(conclusion_message):
    global conversation_history, plaintiff_name, defendant_name

    log = []

    # Add date and names at the top
    log.append(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log.append(f"Plaintiff: {plaintiff_name}")
    log.append(f"Defendant: {defendant_name}")
    log.append("\n--- Conversation Log ---")

    # Append each entry in the conversation history
    for entry in conversation_history:
        log.append(f"{entry['author']}: {entry['message']}")

    # Add conclusion message
    log.append("\n--- Conclusion ---")
    log.append(conclusion_message)

    # Print the formatted log
    print("\n".join(log))


# WebSocket to handle communication between both parties
@socketio.on('connect')
def handle_connect():
    emit('response', {'message': 'Connected to the Mediation Server'})


# WebSocket to register the user (plaintiff or defendant)
@socketio.on('register_user')
def register_user(data):
    global clients, plaintiff_name, defendant_name
    user_type = data['user_type']  # 'plaintiff' or 'defendant'
    name = data['name']  # User's name

    # Register the connection for the specific user
    if user_type in clients:
        clients[user_type] = request.sid
        emit('response', {'message': f'{user_type} connected with SID {request.sid}'})

        # Store the user's name
        if user_type == 'plaintiff':
            plaintiff_name = name
        elif user_type == 'defendant':
            defendant_name = name


@socketio.on('disconnect')
def handle_disconnect():
    global clients
    for user_type, sid in clients.items():
        if sid == request.sid:
            clients[user_type] = None
            break


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
                emit('next_question', {'next_question': next_question}, to=clients['plaintiff'])
            else:
                emit('message', {'message': "Plaintiff questions completed."}, to=clients['plaintiff'])

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
                emit('next_question', {'next_question': next_question}, to=clients['defendant'])
            else:
                plaintiff_history = f"\nPlaintiff Profile: {plaintiff_profile}\n"
                defendant_history = f"\nDefendant Profile: {defendant_profile}\n"
                conversation_history.append({"author": "mediator", "message": plaintiff_history})
                conversation_history.append({"author": "mediator", "message": defendant_history})

                conversation_history.append({"author": "mediator", "message": directions})
                emit('message', {'message': "Defendant questions completed. Mediation ready to start."}, to=clients['defendant'])


# WebSocket to handle turn-based mediation and check for refusal to change price
@socketio.on('mediate')
def handle_mediate(data):
    global turn, conversation_history, clients, plaintiff_last_prices, defendant_last_prices, common_price_reached

    plaintiff_name = data['plaintiff_name']
    defendant_name = data['defendant_name']
    user_input = data['user_input']

    # Track which user is currently responding and whose turn it is
    if turn == 1:
        current_user = plaintiff_name
        other_user = defendant_name
        current_user_sid = clients['plaintiff']
        current_last_prices = plaintiff_last_prices
    else:
        current_user = defendant_name
        other_user = plaintiff_name
        current_user_sid = clients['defendant']
        current_last_prices = defendant_last_prices

    # Add the current user's input to the conversation history with author tracking
    conversation_history.append({"author": current_user, "message": user_input})

    # Store the user's latest price (we assume 'price' means damages or offer mentioned)
    current_last_prices.append(user_input)

    # Check if the user's last 3 responses were the same
    if check_same_last_three(current_last_prices):
        costs = calculate_costs("plaintiff" if current_user == plaintiff_name else "defendant")
        message = f"{current_user} has not changed their asking price for three turns. We appreciate both parties' participation, but we will now end the mediation.\n" \
                  f"Court costs total: ${costs['courtCostTotal']}. Estimated opportunity cost for {current_user}: ${costs['opportunityCost']}. Time commitment: 1 year."
        conversation_history.append({"author": "mediator", "message": message})
        generate_log(message)
        emit('ai_response', {'ai_response': message}, broadcast=True)
        return

    # Check if a common price has been reached
    if check_common_price():
        # If a common price is reached, prompt both users to confirm
        emit('ai_response', {'ai_response': "A common price has been reached. Both parties must confirm this price to conclude the mediation. Please respond with either 'agree' or 'disagree'."}, broadcast=True)
        return

    # Prepare the prompt for GPT-4 based on the conversation history and costs
    history = "\n".join([f"{entry['author']}: {entry['message']}" for entry in conversation_history])
    costs = calculate_costs("plaintiff" if current_user == plaintiff_name else "defendant")
    prompt = f"\n{current_user} has raised the following points: {user_input}. As a mediator, please suggest a fair resolution to {other_user}, addressing {current_user}'s concerns. You should also remind {current_user} of the potential costs they face if they go to court, including court costs (${costs['courtCostTotal']}) and opportunity cost (${costs['opportunityCost']})."

    # Step 1: Feed input to the LLM for mediation
    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": history},
            {"role": "user", "content": prompt}
        ]
    )

    # Step 2: Get response from the LLM
    ai_response = completion.choices[0].message.content
    conversation_history.append({"author": "mediator", "message": f"AI Mediator to {other_user}: {ai_response}"})

    # Alternate the turn for the next user
    turn = 1 if turn == 2 else 2

    # Emit the response to the current user and their opportunity cost
    emit('ai_response', {'ai_response': ai_response, 'next_user': other_user, 'opportunityCost': costs['opportunityCost']}, to=current_user_sid)


# Flask root to confirm Flask is running
@app.route('/')
def index():
    return "Mediation API with WebSocket is running."


if __name__ == '__main__':
    socketio.run(app, debug=True)
