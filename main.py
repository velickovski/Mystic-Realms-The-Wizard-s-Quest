import os
import random
import openai
from flask import Flask, render_template, request, session, jsonify, stream_with_context, Response
from flask_session import Session
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure Flask app
app = Flask(__name__)

# Set a secret key for session management
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-fallback-secret-key')

# Configure session to use filesystem (for development)
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

# Set your OpenAI API key
openai.api_key = os.getenv('OPENAI_API_KEY')

def generate_random_wizard():
    """
    Generate a wizard with random attributes.
    """
    names = ['Alaric', 'Brynne', 'Cedric', 'Daphne', 'Eldrin',
             'Fiona', 'Gareth', 'Helena', 'Isolde', 'Lysander']
    abilities = ['flight', 'telekinesis', 'elemental control',
                 'invisibility', 'shape-shifting', 'time manipulation']
    backstories = [
        'a young apprentice who discovered ancient spells in the forbidden library.',
        'a seasoned sorcerer who has traveled through numerous realms.',
        'a recluse who communicates with mystical creatures.',
        'a guardian of sacred artifacts with unparalleled wisdom.',
        'a wanderer seeking redemption for past misdeeds.',
        'a prodigy who mastered magic at an unprecedented age.'
    ]
    alignments = ['Good', 'Neutral', 'Evil']
    magic_types = ['Dark', 'Light', 'Nature', 'Arcane']

    wizard = {
        'name': random.choice(names),
        'age': random.randint(20, 100),
        'ability': random.choice(abilities),
        'backstory': random.choice(backstories),
        'alignment': random.choice(alignments),
        'magic_type': random.choice(magic_types),
        'health': 100,
        'inventory': []
    }
    return wizard

def load_knowledge(wizard, game_history):
    """
    Generate a knowledge base based on the wizard's attributes and game history. Make sure that the game history is max 50 words and catchy for the users to play.
    """
    history = "\n".join(game_history[-10:])  # Include the last 10 events for context

    knowledge = f"""
You are an AI assistant in a text-based adventure game.
The player controls a wizard with the following attributes:

- **Name**: {wizard['name']}
- **Age**: {wizard['age']}
- **Special Ability**: {wizard['ability']}
- **Backstory**: {wizard['backstory']}
- **Alignment**: {wizard['alignment']}
- **Magic Type**: {wizard['magic_type']}
- **Health**: {wizard['health']}
- **Inventory**: {', '.join(wizard['inventory']) if wizard['inventory'] else 'None'}

The wizard is on a long journey filled with adventures and challenges.
The following is the history of the game so far:
{history}

Based on the wizard's attributes and history, generate the next part of the story without including any choices and make sure to be below 75 words.
"""
    return knowledge

def get_model_response(prompt, knowledge):
    """
    Get a response from the GPT-4o-mini model using OpenAI's API.
    """
    try:
        response = openai.ChatCompletion.create(
            model='gpt-4o-mini',
            messages=[
                {"role": "system", "content": knowledge},
                {"role": "user", "content": prompt}
            ],
            max_tokens=200,
            temperature=0.7,
            stream=True  # Enable streaming
        )

        for chunk in response:
            if 'choices' in chunk:
                if 'delta' in chunk['choices'][0]:
                    delta = chunk['choices'][0]['delta']
                    if 'content' in delta:
                        content = delta['content']
                        yield content

    except Exception as e:
        print(f"Error generating response: {e}")
        yield "An error occurred while generating the story."

def get_choices_response(prompt, knowledge):
    """
    Get choices from the GPT-4o-mini model using OpenAI's API.
    """
    try:
        response = openai.ChatCompletion.create(
            model='gpt-4o-mini',
            messages=[
                {"role": "system", "content": knowledge},
                {"role": "user", "content": prompt}
            ],
            max_tokens=50,
            temperature=0.7
        )

        choices_text = response['choices'][0]['message']['content'].strip()
        choices = [choice.strip() for choice in choices_text.split('\n') if choice.strip()]
        return choices

    except Exception as e:
        print(f"Error generating choices: {e}")
        return ["Continue your journey."]

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/start_game', methods=['POST'])
def start_game():
    wizard = generate_random_wizard()
    game_history = [f"{wizard['name']} begins their journey."]
    session['wizard'] = wizard
    session['game_history'] = game_history
    session['choices'] = []
    return jsonify(success=True)

@app.route('/get_story', methods=['POST'])
def get_story():
    wizard = session.get('wizard')
    game_history = session.get('game_history', [])
    choice_index = int(request.form.get('choice', -1))

    if choice_index >= 0:
        choices = session.get('choices', [])
        if choice_index < len(choices):
            chosen_option = choices[choice_index]
        else:
            chosen_option = "Continue your journey."
        game_history.append(f"Player chose to: {chosen_option}")

        # Adjust wizard's health based on the choice
        health_change = calculate_health_change(chosen_option)
        wizard['health'] += health_change  # health_change can be negative
        wizard['health'] = max(0, min(wizard['health'], 100))  # Clamp health between 0 and 100

        session['wizard'] = wizard  # Update wizard in session

        # Check for game over
        if wizard['health'] <= 0:
            game_history.append("The wizard has perished.")
            session['game_over'] = True
    else:
        # Starting the game
        chosen_option = ""
        session['game_over'] = False  # Reset game over flag

    session['game_history'] = game_history
    knowledge = load_knowledge(wizard, game_history)
    if chosen_option:
        prompt = f"The player chose to {chosen_option}. Continue the story without including any choices."
    else:
        prompt = "Start the story without including any choices."

    # Generate the next part of the story with streaming
    return Response(stream_with_context(get_model_response(prompt, knowledge)), mimetype='text/plain')

def calculate_health_change(choice_text):
    """
    Determine the health change based on the player's choice.
    """
    # Simple logic: certain keywords in choices affect health
    damage_keywords = ['fight', 'battle', 'confront', 'attack', 'enter the dark cave']
    heal_keywords = ['rest', 'heal', 'meditate', 'use a potion']

    for keyword in damage_keywords:
        if keyword in choice_text.lower():
            return -random.randint(5, 20)  # Random damage between 5 and 20

    for keyword in heal_keywords:
        if keyword in choice_text.lower():
            return random.randint(5, 15)  # Random healing between 5 and 15

    return 0  # No change in health

@app.route('/get_choices', methods=['GET'])
def get_choices():
    wizard = session.get('wizard')
    game_history = session.get('game_history', [])
    knowledge = load_knowledge(wizard, game_history)
    prompt = "Based on the current situation, provide 2 choices for the player without any additional text. List each choice on a separate line and make sure at least 1 of them causes damage to the wizard."

    choices = get_choices_response(prompt, knowledge)
    session['choices'] = choices
    return jsonify(choices=choices)

@app.route('/get_wizard_status', methods=['GET'])
def get_wizard_status():
    wizard = session.get('wizard', {})
    game_over = session.get('game_over', False)
    if wizard:
        return jsonify({
            'name': wizard.get('name', 'Unknown Wizard'),
            'health': wizard.get('health', 100),
            'game_over': game_over
        })
    else:
        return jsonify({'error': 'Wizard not found'}), 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
