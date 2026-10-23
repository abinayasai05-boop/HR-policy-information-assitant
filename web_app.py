import os
import uuid

from flask import Flask, render_template, request, jsonify, session
from app.chatbot import generate_answer


# ============================================================
# FLASK APP
# ============================================================

app = Flask(__name__)


# ============================================================
# FLASK SECRET KEY
# ============================================================
# Local:
# Add FLASK_SECRET_KEY to your .env file
#
# Render:
# Add FLASK_SECRET_KEY in Render Environment Variables

app.secret_key = os.getenv("FLASK_SECRET_KEY")

if not app.secret_key:
    raise ValueError(
        "FLASK_SECRET_KEY is not set. "
        "Add it to your .env file locally or Render Environment Variables."
    )


# ============================================================
# HOME PAGE
# ============================================================

@app.route("/")
def home():

    # Create ONE unique session ID for this browser session.
    #
    # This ID is stored inside Flask's session cookie.
    # Every /chat request from the same browser will
    # use the same session ID.

    if "session_id" not in session:

        session["session_id"] = str(uuid.uuid4())

        print(
            "New browser session created:",
            session["session_id"]
        )

    else:

        print(
            "Existing browser session:",
            session["session_id"]
        )

    return render_template("index.html")


# ============================================================
# CHAT API
# ============================================================

@app.route("/chat", methods=["POST"])
def chat():

    try:

        # ----------------------------------------------------
        # Read JSON request
        # ----------------------------------------------------

        data = request.get_json(silent=True)

        if not data:

            return jsonify({
                "answer": "Invalid request."
            }), 400

        # ----------------------------------------------------
        # Get user question
        # ----------------------------------------------------

        question = data.get("question", "").strip()

        if not question:

            return jsonify({
                "answer": "Please enter an HR policy question."
            }), 400

        # ----------------------------------------------------
        # Get the SAME browser session ID
        # ----------------------------------------------------
        #
        # IMPORTANT:
        # Do NOT create a new UUID here.
        #
        # The same session ID must be used for all questions
        # so that conversation memory can be retrieved.

        session_id = session.get("session_id")

        # ----------------------------------------------------
        # Safety check
        # ----------------------------------------------------

        if not session_id:

            session_id = str(uuid.uuid4())

            session["session_id"] = session_id

            print(
                "Session was missing. Created new session:",
                session_id
            )

        # ----------------------------------------------------
        # Debug information
        # ----------------------------------------------------

        print("----------------------------------------")
        print("Session ID:", session_id)
        print("User Question:", question)
        print("----------------------------------------")

        # ----------------------------------------------------
        # Generate answer using RAG + conversation memory
        # ----------------------------------------------------

        answer = generate_answer(
            question,
            session_id
        )

        # ----------------------------------------------------
        # Return answer to frontend
        # ----------------------------------------------------

        return jsonify({
            "answer": answer
        })

    
    except Exception as e:

        print("CHAT ERROR:", repr(e))

        import traceback
        traceback.print_exc()

        return jsonify({
            "answer": "Sorry, something went wrong. Please try again."
        }), 500

# ============================================================
# HEALTH CHECK
# ============================================================

@app.route("/health")
def health():

    return jsonify({
        "status": "healthy",
        "service": "HR Policy RAG Chatbot"
    })


# ============================================================
# LOCAL DEVELOPMENT
# ============================================================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=int(os.getenv("PORT", 5000)),
        debug=False
    )