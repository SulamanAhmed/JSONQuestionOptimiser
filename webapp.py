from flask import Flask, request, jsonify, render_template
from openai import OpenAI
import os
import json
import re

# Load the OpenAI API key from an environment variable
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OpenAI API key is not set in the environment variable 'OPENAI_API_KEY'.")
client = OpenAI(api_key=api_key)

app = Flask(_name_)
app.secret_key = 'dev'
app.config['JSON_AS_ASCII'] = False


def fix_and_parse_json(malformed_json_str):
    json_str = malformed_json_str.strip()
    first_brace = json_str.find('{')
    last_brace = json_str.rfind('}')
    if first_brace == -1 or last_brace == -1:
        return None
    json_candidate = json_str[first_brace:last_brace + 1]
    json_candidate = re.sub(r'^[^{]*', '', json_candidate)
    json_candidate = re.sub(r'[^}]*$', '', json_candidate)
    try:
        parsed_json = json.loads(json_candidate)
        return parsed_json
    except json.JSONDecodeError:
        json_candidate = re.sub(r',\s*}', '}', json_candidate)
        json_candidate = re.sub(r',\s*]', ']', json_candidate)
        json_candidate = re.sub(r'\}\}+', '}', json_candidate)
        try:
            parsed_json = json.loads(json_candidate)
            return parsed_json
        except json.JSONDecodeError:
            return None


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/process', methods=['POST'])
def process_data():
    user_input = request.form.get('data_text', '').strip()
    if not user_input:
        return jsonify({'error': 'Data input is required.'}), 400

    try:
        with open('prompt.txt', 'r', encoding='utf-8') as prompt_file:
            prompt_template = prompt_file.read()

        prompt = prompt_template.replace("{{text}}", user_input)
        max_retries = 3
        attempt = 0
        response_data = None

        while attempt < max_retries:
            try:
                response = client.chat.completions.create(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": "You are an assistant."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=2000,
                    temperature=0
                )
                result_text = response.choices[0].message.content.strip()
                parsed_json = fix_and_parse_json(result_text)

                if parsed_json is not None:
                    response_data = {"response": parsed_json}
                    break
                else:
                    attempt += 1
            except Exception as e:
                response_data = {'error': str(e)}
                attempt += 1

        if response_data is None:
            response_data = {
                "error": "Failed to parse JSON from AI response.",
                "raw_response": result_text if 'result_text' in locals() else "No response available."
            }

        return jsonify(response_data)

    except Exception as e:
        return jsonify({'error': 'An unexpected error occurred', 'details': str(e)}), 500


if _name_ == '__main__':
    app.run(debug=True)