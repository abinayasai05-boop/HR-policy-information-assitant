
import os
import uuid
import time
import re

from dotenv import load_dotenv
from google import genai
from google.genai import types
from app.database import get_connection


# ============================================================
# LOAD ENVIRONMENT VARIABLES
# ============================================================

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise ValueError(
        "GEMINI_API_KEY not found. "
        "Please check your .env file."
    )


# ============================================================
# CONNECT TO GEMINI
# ============================================================

client = genai.Client(
    api_key=GEMINI_API_KEY
)


# ============================================================
# GEMINI CONFIGURATION
# ============================================================

GEMINI_MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini-3.8-flash",
)

MAX_GEMINI_RETRIES = 2


# ============================================================
# GEMINI EMBEDDING CONFIGURATION
# ============================================================

EMBEDDING_MODEL = os.getenv(
    "GEMINI_EMBEDDING_MODEL",
    "gemini-embedding-2"
)

EMBEDDING_DIMENSION = int(
    os.getenv(
        "EMBEDDING_DIMENSION",
        "768"
    )
)


# ============================================================
# RAG CONFIGURATION
# ============================================================

TOP_K = 5
SIMILARITY_THRESHOLD = 0.45
MEMORY_LIMIT = 5


# ============================================================
# EMBEDDING INITIALIZATION
# ============================================================

print("\nInitializing Gemini Embedding 2...")

print(f"Embedding model: {EMBEDDING_MODEL}")

print(f"Embedding dimension: {EMBEDDING_DIMENSION}")

print("Gemini Embedding 2 initialized successfully!")


# ============================================================
# SIMPLE MESSAGE / GREETING HANDLER
# ============================================================

def handle_simple_message(question):
    """
    Handle greetings, thanks, and simple help messages
    without performing an HR policy search.
    """

    text = question.lower().strip()
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\s+", " ", text).strip()

    # --------------------------------------------------------
    # GREETINGS
    # --------------------------------------------------------

    greetings = {
        "hi", "hii", "hiii", "hello", "helo",
        "hey", "heyy", "hai",
    }

    help_questions = {
        "help",
        "who are you",
        "what can you do",
        "what can you help me with",
        "how can i access you",
        "how can i use you",
        "how do i use you",
        "what can i ask you",
        "how can you help me",
    }

    # Handle greetings, including greetings with questions
    words = text.split()

    if text in greetings:
        return (
            "Hello! 👋 I'm your HR Policy Assistant. "
            "I can help you understand company HR policies. "
            "What would you like to know?"
        )

    if words and words[0] in greetings:
        remaining_text = " ".join(words[1:])

        if (
            not remaining_text
            or any(question in remaining_text for question in help_questions)
            or "what can i ask" in remaining_text
            or "what can you do" in remaining_text
            or "how can you help" in remaining_text
        ):
            return (
                "Hello! 👋 I'm your HR Policy Assistant. 🤖\n\n"
                "You can ask me about annual leave, sick leave, "
                "working hours, work from home, resignation, salary, "
                "overtime, and other topics covered by your HR policies.\n\n"
                "For example:\n"
                "- Can I take sick leave for two days?\n"
                "- What is the annual leave policy?\n"
                "- Can I work from home?"
            )

    if text in help_questions:
        return (
            "I'm your HR Policy Assistant. 🤖\n\n"
            "You can ask me about annual leave, sick leave, "
            "working hours, work from home, resignation, salary, "
            "overtime, and other topics covered by your HR policies.\n\n"
            "For example:\n"
            "- Can I take sick leave for two days?\n"
            "- What is the annual leave policy?\n"
            "- Can I work from home?\n\n"
            "I'll answer using the available HR policy information."
        )

    # --------------------------------------------------------
    # TIME-BASED GREETINGS
    # --------------------------------------------------------

    if text in {"good morning", "morning", "gm"}:
        return (
            "Good morning! 👋 I'm your HR Policy Assistant. "
            "How can I help you with HR policies today?"
        )

    if text in {"good afternoon", "afternoon"}:
        return (
            "Good afternoon! 👋 I'm your HR Policy Assistant. "
            "How can I help you with HR policies today?"
        )

    if text in {"good evening", "evening"}:
        return (
            "Good evening! 👋 I'm your HR Policy Assistant. "
            "How can I help you with HR policies today?"
        )

    # --------------------------------------------------------
    # THANK YOU
    # --------------------------------------------------------

    if text in {
        "thanks",
        "thank you",
        "thankyou",
        "thx",
    }:
        return (
            "You're welcome! 😊 "
            "I'm happy to help with your HR policy questions."
        )

    # --------------------------------------------------------
    # GOODBYE
    # --------------------------------------------------------

    if text in {
        "goodbye",
        "see you",
        "see ya",
        "bye bye",
    }:
        return (
            "Goodbye! 👋 "
            "Feel free to come back if you have any HR policy questions."
        )

    return None


# ============================================================
# CREATE QUERY EMBEDDING
# ============================================================

def create_query_embedding(query):
    """
    Create a Gemini embedding for the user's search query.
    """

    result = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=query,
        config=types.EmbedContentConfig(
            output_dimensionality=EMBEDDING_DIMENSION
        )
    )

    embedding = result.embeddings[0].values

    return embedding


# ============================================================
# GEMINI RESPONSE FUNCTION
# ============================================================

def generate_gemini_response(prompt):
    """
    Generate a response using Gemini.
    Retry temporary errors with limited waiting time.
    """

    for attempt in range(MAX_GEMINI_RETRIES):
        try:
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
                config={
                    "http_options": {
                        "timeout": 20000
                    }
                }
            )

            if (
                not response
                or not response.text
                or not response.text.strip()
            ):
                print("Gemini returned an empty response.")
                return None

            return response.text.strip()

        except Exception as e:
            error_text = str(e).upper()

            is_temporary_error = any(
                message in error_text
                for message in (
                    "503",
                    "UNAVAILABLE",
                    "SERVICE UNAVAILABLE",
                    "DEADLINE EXCEEDED",
                    "TIMEOUT",
                    "RESOURCE EXHAUSTED",
                    "429",
                    "504",
                )
            )

            print(f"Gemini attempt {attempt + 1} failed: {e}")

            if not is_temporary_error:
                raise

            if attempt == MAX_GEMINI_RETRIES - 1:
                print("Gemini is unavailable after retries.")
                return None

            time.sleep(1)

    return None

# ============================================================
# SAVE CONVERSATION TO POSTGRESQL
# ============================================================

def save_conversation(
    user_message,
    assistant_message,
    session_id
):
    """
    Save the conversation to PostgreSQL.
    """

    conn = get_connection()

    try:
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO conversation_memory
            (
                session_id,
                user_message,
                assistant_message
            )
            VALUES (%s, %s, %s);
            """,
            (
                session_id,
                user_message,
                assistant_message
            )
        )

        conn.commit()
        cursor.close()

    finally:
        conn.close()


# ============================================================
# GET CONVERSATION HISTORY
# ============================================================

def get_conversation_history(
    session_id,
    limit=MEMORY_LIMIT
):
    """
    Retrieve previous messages from the current session.
    """

    conn = get_connection()

    try:
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT
                user_message,
                assistant_message
            FROM conversation_memory
            WHERE session_id = %s
            ORDER BY created_at DESC
            LIMIT %s;
            """,
            (
                session_id,
                limit
            )
        )

        results = cursor.fetchall()
        cursor.close()

    finally:
        conn.close()

    results.reverse()

    history = ""

    for user_message, assistant_message in results:
        history += (
            f"\nUser: {user_message}\n"
            f"Assistant: {assistant_message}\n"
        )

    return history


# ============================================================
# CREATE SEARCH QUERY USING CONVERSATION MEMORY
# ============================================================

def create_search_query(question, session_id):
    """
    Expand HR policy queries with related terminology
    while preserving the user's original question.
    """

    history = get_conversation_history(
        session_id,
        limit=MEMORY_LIMIT
    )

    text = question.lower()

    synonym_groups = [
        (
            [
                "annual leave",
                "yearly leave",
                "vacation",
                "annual vacation",
                "yearly vacation",
                "paid time off",
                "pto",
            ],
            "annual leave entitlement vacation allowance "
            "leave application leave approval"
        ),
        (
            [
                "sick leave",
                "medical leave",
                "sick day",
                "leave due to illness",
            ],
            "sick leave illness medical certificate "
            "eligibility duration leave approval"
        ),
        (
            [
                "casual leave",
                "personal leave",
            ],
            "casual leave personal leave eligibility "
            "leave application approval"
        ),
        (
            [
                "maternity leave",
                "paternity leave",
                "parental leave",
            ],
            "parental leave maternity paternity "
            "eligibility duration"
        ),
        (
            [
                "work from home",
                "working remotely",
                "remote work",
                "wfh",
            ],
            "remote work work from home eligibility "
            "approval procedure"
        ),
        (
            [
                "resign",
                "resignation",
                "quit my job",
                "leaving the company",
            ],
            "resignation notice period exit procedure"
        ),
    ]

    extra_terms = []

    for phrases, expansion in synonym_groups:
        if any(phrase in text for phrase in phrases):
            extra_terms.append(expansion)

    expanded_query = question

    if extra_terms:
        expanded_query += " " + " ".join(extra_terms)

    # Resolve follow-up questions using conversation history.
    if history:
        prompt = f"""
You rewrite search queries for an HR policy chatbot.

Rewrite the current question as a standalone HR search query.
Use conversation history only to resolve references.
Preserve the user's original intent, leave type, numbers,
durations, dates, and conditions.
Do not answer the question or invent policy facts.
Include relevant HR terminology where appropriate.
Return only the search query.

PREVIOUS CONVERSATION:
{history}

CURRENT QUESTION:
{expanded_query}

SEARCH QUERY:
"""

        rewritten = generate_gemini_response(prompt)

        if rewritten:
            return expanded_query + " " + rewritten

    return expanded_query


# ============================================================
# SEARCH HR POLICIES USING PGVECTOR
# ============================================================

def search_policies(
    query,
    top_k=TOP_K
):
    """
    Embed the query and search the HR policies table
    using PostgreSQL and pgvector.
    """

    query_embedding = create_query_embedding(query)

    if len(query_embedding) != EMBEDDING_DIMENSION:
        raise ValueError(
            f"Embedding dimension mismatch. "
            f"Expected {EMBEDDING_DIMENSION}, "
            f"got {len(query_embedding)}."
        )

    conn = get_connection()

    try:
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT
                policy_id,
                category,
                title,
                content,
                1 - (embedding <=> %s::vector) AS similarity
            FROM hr_policies
            ORDER BY embedding <=> %s::vector
            LIMIT %s;
            """,
            (
                query_embedding,
                query_embedding,
                top_k
            )
        )

        results = cursor.fetchall()
        cursor.close()

    finally:
        conn.close()

    policies = []

    for result in results:
        (
            policy_id,
            category,
            title,
            content,
            similarity
        ) = result

        policies.append(
            {
                "policy_id": policy_id,
                "category": category,
                "title": title,
                "content": content,
                "score": float(similarity)
            }
        )

    return policies


# ============================================================
# CREATE POLICY CONTEXT
# ============================================================

def create_policy_context(results):
    """
    Format retrieved HR policies for the Gemini prompt.
    """

    context = ""

    for result in results:
        context += f"""
Policy ID: {result['policy_id']}
Category: {result['category']}
Title: {result['title']}
Content: {result['content']}

"""

    return context


# ============================================================
# GENERATE RAG ANSWER
# ============================================================

def generate_answer(
    question,
    session_id
):
    """
    Complete RAG pipeline:

    1. Handle greetings and simple messages
    2. Expand the search query
    3. Retrieve HR policies
    4. Check similarity
    5. Create grounded prompt
    6. Generate and save the answer
    """

    # ========================================================
    # STEP 0: HANDLE SIMPLE MESSAGES
    # ========================================================

    simple_response = handle_simple_message(question)

    if simple_response:
        save_conversation(
            question,
            simple_response,
            session_id
        )

        return simple_response

    # ========================================================
    # STEP 1: CREATE SEARCH QUERY
    # ========================================================

    search_query = create_search_query(
        question,
        session_id
    )

    # ========================================================
    # STEP 2: SEARCH HR POLICIES
    # ========================================================

    results = search_policies(
        search_query,
        top_k=TOP_K
    )

    # ========================================================
    # STEP 3: DEBUG SEARCH RESULTS
    # ========================================================
    
    print("\nDEBUG: User question:", question)
    print("DEBUG: Search query:", search_query)

    for row in results:
        print(
            f"Policy ID: {row['policy_id']} | "
            f"Title: {row['title']} | "
            f"Category: {row['category']} | "
            f"Similarity: {float(row['score']):.3f}"

        )
        # STEP 4: CHECK RETRIEVAL RESULTS
    if not results:
        print("FAILURE REASON: NO POLICIES RETRIEVED")

        answer = (
            "I couldn't find this information "
            "in the HR policies."
        )

        save_conversation(question, answer, session_id)
        return answer

    # STEP 5: CHECK SIMILARITY THRESHOLD

    top_score = float(results[0]["score"])

    print("DEBUG: Best similarity:", top_score)
    print("DEBUG: Required threshold:", SIMILARITY_THRESHOLD)
     
    if top_score < SIMILARITY_THRESHOLD:
        print("FAILURE REASON: SIMILARITY BELOW THRESHOLD")

        answer = (
            "I couldn't find this information "
            "in the HR policies."
        )

        save_conversation(question, answer, session_id)
        return answer


    # ========================================================
    # STEP 6: CREATE POLICY CONTEXT
    # ========================================================

    context = create_policy_context(results)

    # ========================================================
    # STEP 7: GET CONVERSATION HISTORY
    # ========================================================

    history = get_conversation_history(
        session_id,
        limit=MEMORY_LIMIT
    )

    # ========================================================
    # STEP 8: CREATE GROUNDED RAG PROMPT
    # ========================================================

    prompt = f"""
You are an intelligent HR Policy Assistant powered by Gemini
and a Retrieval-Augmented Generation (RAG) system.

YOUR MAIN OBJECTIVE
Understand the employee's intended question, regardless of
their English proficiency, grammar, spelling, or phrasing.
Answer accurately using the retrieved HR policy documents.

1. UNDERSTAND THE USER
- Understand natural, informal, incomplete, and grammatically
  incorrect English.
- Identify the user's intent rather than relying on exact
  keyword matches.
- Use conversation history to resolve references such as
  "it", "that", "how many days", and "what about this".
- Preserve leave types, numbers, durations, dates, conditions,
  and other important details.
- Answer the current question, not an unrelated earlier one.

2. USE RETRIEVED POLICIES
- Identify which retrieved policies are relevant to the
  user's actual question.
- Match different phrasings when they express the same intent.
- Use only retrieved policy evidence for HR policy facts.
- Do not assume a policy permits or prohibits something
  unless the retrieved evidence supports that conclusion.

3. HANDLE PARTIAL INFORMATION
- If a policy answers part of the question, explain the
  supported information instead of rejecting the entire
  question.
- Explicitly address requested numbers and durations.
- Distinguish permission to request leave from confirmed
  entitlement or approval.
- If the policy does not specify a requested detail, say
  that the available policy does not specify it.
- Never invent leave limits, eligibility rules, approval
  requirements, or other policy facts.
- If no retrieved policy is relevant, respond:
  "I couldn't find this information in the HR policies."

4. CONVERSATION MEMORY
- Use previous messages to interpret follow-up questions.
- Previous assistant responses are conversational context,
  not authoritative evidence of company policy.
- Use the retrieved policy documents as the source of
  policy facts.
- Do not confuse different leave types or policy topics.

5. RESPONSE STYLE
- Use simple, natural English.
- Answer directly and politely.
- Explain what the policy confirms and what remains unknown.
- Do not mention similarity scores, embeddings, or internal
  retrieval processes.
- Do not return an empty answer when relevant policy
  information is available.

EXAMPLES

Example A:
Question: Can I take sick leave for two days?
Retrieved policy:
Employees can request sick leave when they are unable
to work due to illness.

Answer:
Employees can request sick leave when they are unable
to work due to illness. However, the available policy
does not specify whether a two-day request has any
additional conditions or approval requirements.
Please confirm those details with HR.

Example B:
Question: I am not feeling well. Need leave for 2 days.
Retrieved policy:
Employees can request sick leave when they are unable
to work due to illness.

Answer:
You can request sick leave if you are unable to work
due to illness. The available policy does not specify
the conditions for a two-day request, so please confirm
the applicable requirements with HR.

Example C:
Question: What about casual leave?
Retrieved policies:
Annual Leave: Employees are entitled to 20 days per year.
Casual Leave: Employees are entitled to 12 days per year.

Answer:
Employees are entitled to 12 days of casual leave per year.

PREVIOUS CONVERSATION:
{history}

RETRIEVED HR POLICY INFORMATION:
{context}

CURRENT EMPLOYEE QUESTION:
{question}

Answer the current question using relevant retrieved
policy evidence and the instructions above.
"""

    # ========================================================
    # STEP 9: GENERATE FINAL ANSWER
    # ========================================================

    answer = generate_gemini_response(prompt)

    # ========================================================
    # STEP 10: GEMINI FAILURE FALLBACK
    # ========================================================

    if not answer:
        answer = (
            "Sorry, I couldn't generate an answer right now. "
            "Please try again in a moment."
        )
    # ========================================================
    # STEP 11: SAVE CONVERSATION
    # ========================================================

    save_conversation(
        question,
        answer,
        session_id
    )

    # ========================================================
    # STEP 12: RETURN ANSWER
    # ========================================================

    return answer


# ============================================================
# CHAT LOOP
# ============================================================

if __name__ == "__main__":

    print("\n==========================================")
    print("          HR POLICY RAG CHATBOT")
    print("==========================================")

    print("\nEmbedding Model:")
    print(EMBEDDING_MODEL)

    print("\nEmbedding Dimension:")
    print(EMBEDDING_DIMENSION)

    print("\nVector Database:")
    print("PostgreSQL + pgvector")

    print("\nLLM:")
    print(GEMINI_MODEL)

    print("\nConversation Memory:")
    print("PostgreSQL")

    print("\nHallucination Protection:")
    print("Enabled")

    print("\nGreeting Handling:")
    print("Enabled")

    print("\nType 'exit', 'quit', or 'bye' to stop.")

    # ========================================================
    # CREATE CHAT SESSION
    # ========================================================

    cli_session_id = str(uuid.uuid4())

    print("\nSession ID:", cli_session_id)

    # ========================================================
    # START CHAT
    # ========================================================

    while True:
        try:
            question = input("\nYou: ").strip()

        except (KeyboardInterrupt, EOFError):
            print("\n\nChatbot: Goodbye!")
            break

        # ====================================================
        # EMPTY QUESTION
        # ====================================================

        if not question:
            print(
                "\nChatbot: "
                "Please enter an HR policy question."
            )
            continue

        # ====================================================
        # EXIT COMMAND
        # ====================================================

        if question.lower() in {"exit", "quit", "bye"}:
            print("\nChatbot: Goodbye!")
            break

        # ====================================================
        # GENERATE ANSWER
        # ====================================================

        try:
            answer = generate_answer(
                question,
                cli_session_id
            )

            print("\nChatbot:")
            print(answer)

        except Exception as e:
            print("\nError:")
            print(str(e))
