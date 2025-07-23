# streamlit_ui.py (with Intent Recognition)

import streamlit as st
import ollama
import pandas as pd
import os
import json
import requests
from datetime import datetime

# --- CONFIGURATION ---
OLLAMA_BASE_URL = "https://moose-relieved-bison.ngrok-free.app"
OLLAMA_MODEL = "llama3"
CHAT_HISTORY_DIR = './Intermediate-Chats'
BACKEND_API_URL = "http://127.0.0.1:8000/query"

# --- INITIALIZATION ---
try:
    ollama_client = ollama.Client(host=OLLAMA_BASE_URL)
    ollama_client.ps()
except Exception as e:
    st.error(f"Failed to connect to Ollama at {OLLAMA_BASE_URL}. Error: {e}")
    st.stop()

if not os.path.exists(CHAT_HISTORY_DIR):
    os.makedirs(CHAT_HISTORY_DIR)


# --- (All chat management functions like display_messages, save_current_chat, etc. remain the same) ---
# ...
# --- Placeholder for the functions you will copy ---
def display_messages():
    # (implementation from previous file)
    pass


def save_current_chat():
    # (implementation from previous file)
    pass


def load_chat_from_file(filepath):
    # (implementation from previous file)
    pass


def display_saved_chats():
    # (implementation from previous file)
    pass


# Make sure to copy the actual functions into your file!


## --- NEW FUNCTION: INTENT RECOGNITION --- ##
def get_user_intent(user_prompt: str) -> str:
    """
    Uses Ollama to classify the user's prompt as either a database query or a general chat question.
    """
    # In streamlit_ui.py -> get_user_intent()

    system_prompt = f"""
    You are an expert routing agent. Your task is to classify the user's question into one of two categories:

    1.  `DATABASE_QUERY`: Choose this ONLY if the user is explicitly asking to retrieve, find, show, list, count, or query data about suppliers, products, inventory, stock levels, or business locations. The query MUST be answerable with a SQL SELECT statement.
        Examples:
        - "Show me all suppliers from the USA."
        - "How many units of 'Chai' are in stock?"
        - "List the companies in London."
        - "who is the supplier with the most products?"

    2.  `GENERAL_CHAT`: Choose this for ALL other questions. This includes greetings, follow-up pleasantries, general knowledge, math problems, requests to write code, or any question that is NOT a direct request for data from the supplier database.
        Examples:
        - "Hello, how are you?"
        - "That was very helpful, thank you!"
        - "What is the capital of France?"
        - "Can you write a poem about robots?"
        - "Why did the last query return no results?"

    Analyze the user's question below and respond with ONLY the category name (`DATABASE_QUERY` or `GENERAL_CHAT`) and nothing else.

    User Question: "{user_prompt}"
    """
    try:
        # We use ollama.generate for a simple, single-turn response
        response = ollama_client.generate(
            model=OLLAMA_MODEL,
            prompt=system_prompt
        )
        intent = response['response'].strip()

        # A fallback in case the model returns something unexpected
        if "DATABASE_QUERY" in intent:
            return "DATABASE_QUERY"
        else:
            return "GENERAL_CHAT"

    except Exception as e:
        st.error(f"Error in intent recognition: {e}")
        return "GENERAL_CHAT"  # Default to general chat on error


# --- MAIN STREAMLIT APP ---
def main():
    st.set_page_config(page_title="Aaroh's AI Assistant", layout="wide")
    st.title("Aaroh's AI Assistant 🤖")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    # --- SIDEBAR (we removed the checkbox) ---
    with st.sidebar:
        st.header("Controls")
        st.info("The assistant will automatically detect if you are asking a database question.")
        if st.button("Start New Chat / Save Current", use_container_width=True):
            save_current_chat()
        # ... rest of the sidebar code ...

    display_messages()

    if prompt := st.chat_input("What would you like to ask?"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            ## --- MODIFIED LOGIC: USE INTENT INSTEAD OF CHECKBOX --- ##
            with st.spinner("Analyzing your question..."):
                intent = get_user_intent(prompt)

            st.info(f"Intent detected: **{intent}**")  # Optional: show the user what the AI decided

            if intent == "DATABASE_QUERY":
                # --- Database Query Path ---
                with st.spinner("Connecting to database and executing query..."):
                    try:
                        api_response = requests.post(BACKEND_API_URL, json={"question": prompt})
                        if api_response.status_code == 200:
                            data = api_response.json()
                            sql_query = data.get("generated_query")
                            results = data.get("data")

                            response_text = f"Based on your request, I generated and executed a query:"
                            st.markdown(response_text)
                            st.code(sql_query, language="sql")

                            df = pd.DataFrame(results)
                            st.dataframe(df)

                            st.session_state.messages.append({"role": "assistant", "content": response_text})
                            st.session_state.messages.append({"role": "assistant", "content": ("SQL_QUERY", sql_query)})
                            st.session_state.messages.append({"role": "assistant", "content": df})
                        else:
                            error_detail = api_response.json().get("detail", "Unknown error")
                            st.error(f"API Error: {error_detail}")
                            st.session_state.messages.append(
                                {"role": "assistant", "content": f"API Error: {error_detail}"})

                    except requests.exceptions.RequestException as e:
                        st.error(f"Could not connect to the backend API. Is it running? Error: {e}")


            else:  # intent == "GENERAL_CHAT"

                # --- General Chat Path (Classic Method) ---

                with st.spinner("Thinking..."):

                    # Create a placeholder for the streaming output

                    placeholder = st.empty()

                    full_response = ""

                    # Call the model and get the stream

                    stream = ollama_client.chat(

                        model=OLLAMA_MODEL,

                        messages=[m for m in st.session_state.messages if isinstance(m['content'], str)],

                        stream=True

                    )

                    # Iterate through the stream and update the placeholder

                    for chunk in stream:
                        full_response += chunk['message']['content']

                        placeholder.markdown(full_response + "▌")  # The "▌" is a blinking cursor effect

                    # Update the placeholder one last time without the cursor

                    placeholder.markdown(full_response)

                    # Save the complete response to the message history

                    st.session_state.messages.append({"role": "assistant", "content": full_response})


if __name__ == "__main__":
    main()
