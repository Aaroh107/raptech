# api_backend.py

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import mariadb
import ollama
import uvicorn
from pydantic import BaseModel
import re  # Import the regular expressions module

# --- CONFIGURATION ---
OLLAMA_BASE_URL = "https://moose-relieved-bison.ngrok-free.app"
OLLAMA_MODEL = "llama3"
DB_CONFIG = {
    "user": "root",
    "password": "aaroh107",
    "host": "127.0.0.1",
    "port": 3307,
    "database": "data_db"
}
DB_VIEW_NAME = "SUPPLIER_VIEW"

# --- INITIALIZATION ---
app = FastAPI(title="Database Query API")
ollama_client = ollama.Client(host=OLLAMA_BASE_URL)

# Add CORS middleware to allow requests from our Streamlit app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)


# Pydantic model for the request body
class QueryRequest(BaseModel):
    question: str


# --- DATABASE HELPER FUNCTIONS ---
def get_db_connection():
    try:
        conn = mariadb.connect(**DB_CONFIG)
        return conn, conn.cursor(dictionary=True)
    except mariadb.Error as e:
        raise HTTPException(status_code=500, detail=f"Database connection failed: {e}")


def get_view_schema(cur):
    try:
        cur.execute(f"DESCRIBE {DB_VIEW_NAME}")
        columns = cur.fetchall()
        schema = f"View Name: {DB_VIEW_NAME}\nColumns:\n"
        schema += ",\n".join(f"  - {col['Field']} (Type: {col['Type']})" for col in columns)
        return schema
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to describe view '{DB_VIEW_NAME}': {e}")


# --- API ENDPOINT ---
@app.post("/query")
async def query_database_endpoint(request: QueryRequest):
    """
    Takes a natural language question, generates and executes a SQL query,
    and returns the results.
    """
    question = request.question
    conn, cur = get_db_connection()
    if not conn:
        return  # Exception is already raised by get_db_connection

    try:
        schema = get_view_schema(cur)
        if not schema:
            return  # Exception is already raised

        # --- CHANGE #1: A MORE STRICT PROMPT ---
        # We added a clear instruction to ONLY respond with SQL and gave a one-shot example.
        prompt = f"""
You are an expert MariaDB SQL assistant. Your SOLE task is to generate a single, executable SELECT query based on the user's question and the provided schema.

**Schema for view '{DB_VIEW_NAME}':**
{schema}

**User's Question:**
"{question}"

**Instructions:**
1.  Generate a `SELECT` query ONLY.
2.  Your response MUST begin with `SELECT`.
3.  Do NOT include any explanations, introductory text, or markdown like ```sql.
4.  If asked to perform DELETE, INSERT, UPDATE, respond with the text "INVALID QUERY".

**Example:**
User Question: "Show me suppliers in London"
Your Response: SELECT * FROM SUPPLIER_VIEW WHERE City = 'London';

**Generated SQL Query:**
"""
        response = ollama_client.generate(model=OLLAMA_MODEL, prompt=prompt)
        raw_output = response['response'].strip()

        # --- CHANGE #2: MORE ROBUST PARSING LOGIC ---
        # This new logic actively finds the 'SELECT' statement,
        # making it resilient to introductory text from the model.
        # It handles cases like "Here is the query: SELECT..."

        # First, clean potential markdown fences
        clean_output = re.sub(r'```sql\s*|\s*```', '', raw_output, flags=re.IGNORECASE)

        # Find the start of the actual SELECT statement, case-insensitive
        select_pos = clean_output.upper().find("SELECT")

        # If 'SELECT' is found, slice the string from that point
        if select_pos != -1:
            sql_query = clean_output[select_pos:]
        else:
            # If 'SELECT' is not in the response, we assume it's an invalid query
            sql_query = clean_output  # Let the validation below handle it

        if not sql_query.upper().startswith("SELECT"):
            # The model's response did NOT start with "SELECT", even after cleaning.
            # This will now correctly catch "INVALID QUERY" or other non-SQL responses.
            raise HTTPException(status_code=400,
                                detail=f"Could not generate a valid SQL query. Model response: '{sql_query}'")

        cur.execute(sql_query)
        rows = cur.fetchall()

        return {
            "question": question,
            "generated_query": sql_query,
            "row_count": cur.rowcount,
            "data": rows,
        }

    except mariadb.Error as db_error:
        # Catch database-specific errors (e.g., syntax error in the generated SQL)
        raise HTTPException(status_code=400,
                            detail=f"Database execution error: {str(db_error)}. Query was: '{sql_query}'")
    except Exception as e:
        # Catch all other exceptions
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")
    finally:
        if conn:
            cur.close()
            conn.close()


# To run this file directly for testing
if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
