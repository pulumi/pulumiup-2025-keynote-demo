import os
from openai import OpenAI
from flask import Flask, request, jsonify

app = Flask(__name__)

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
if not client.api_key:
    raise RuntimeError("OpenAI API key not found. Please set OPENAI_API_KEY environment variable.")

@app.route("/", methods=["GET"])
def health_check():
    """Simple health check endpoint for the load balancer."""
    return jsonify({"status": "healthy"}), 200

@app.route("/chat", methods=["POST"])
def chat():
    """Handle POST requests to /chat with JSON containing a 'prompt'."""
    data = request.get_json(force=True)
    prompt = data.get("prompt")
    model = data.get("model", "gpt-3.5-turbo")
    if model not in ["gpt-3.5-turbo", "gpt-4o"]:
        return jsonify({"error": "Unsupported model"}), 400
    if not prompt:
        return jsonify({"error": "No prompt provided"}), 400

    try:
        # Call the OpenAI ChatCompletion API with the prompt using the new client interface
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}]
        )
        # Extract the assistant's reply from the API response
        answer = response.choices[0].message.content
        return jsonify({"response": answer})
    except Exception as e:
        # Catch any errors (e.g., API errors) and return as JSON
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    # Run the Flask app on all interfaces, port 8080 (container will listen on port 8080)
    app.run(host="0.0.0.0", port=8080)
