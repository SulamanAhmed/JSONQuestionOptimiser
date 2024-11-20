from flask import Flask, request, jsonify, render_template, send_file, redirect, url_for, flash
from openai import OpenAI
import os
import json
import re

# Load the OpenAI API key from an environment variable
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OpenAI API key is not set in the environment variable 'OPENAI_API_KEY'.")
client = OpenAI(api_key=api_key)

app = Flask(__name__)
app.secret_key = 'dev'  # Required for flash messages
app.config['JSON_AS_ASCII'] = False  # Disable ASCII encoding for JSON responses


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
        # Read the contents of the pre-uploaded prompt.txt
        with open('prompt.txt', 'r', encoding='utf-8') as prompt_file:
            prompt_template = prompt_file.read()

        # Format the prompt with the user input
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

        # Save the response to a JSON file
        output_path = 'output.json'
        with open(output_path, 'w', encoding='utf-8') as output_file:
            json.dump(response_data, output_file, ensure_ascii=False, indent=4)

        # Return JSON with the download link
        return jsonify({
            'message': 'Processing complete',
            'download_url': '/download'
        })

    except Exception as e:
        return jsonify({'error': 'An unexpected error occurred', 'details': str(e)}), 500


@app.route('/download')
def download_file():
    # Serve the JSON file
    return send_file('output.json', as_attachment=True)


if __name__ == '__main__':
    app.run(debug=True)
