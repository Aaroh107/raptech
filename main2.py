# main.py
import multiprocessing
import uvicorn
import subprocess
import time

# --- Configuration ---
# Match the host and port from your api_backend.py
API_HOST = "127.0.0.1"
API_PORT = 8000

# The name of your Streamlit UI file
STREAMLIT_UI_FILE = "streamlitui2.py"


def run_fastapi_app():
    """
    Runs the FastAPI backend using uvicorn.
    We import the app object from the api_backend file.
    """
    print("Starting FastAPI server...")
    # Note: We are telling uvicorn to look for an object named 'app'
    # inside a file named 'api_backend.py'.
    uvicorn.run("apibackend2:app", host=API_HOST, port=API_PORT, log_level="info")


def run_streamlit_app():
    """
    Runs the Streamlit UI using the command-line interface.
    """
    print("Starting Streamlit UI...")
    # We use subprocess to execute the shell command: streamlit run streamlit_ui.py
    command = ["streamlit", "run", STREAMLIT_UI_FILE]
    subprocess.run(command)


if __name__ == "__main__":
    # Create two separate processes
    # One for the API backend
    api_process = multiprocessing.Process(target=run_fastapi_app)

    # Another for the Streamlit UI
    ui_process = multiprocessing.Process(target=run_streamlit_app)

    print("Launching services...")

    # Start both processes
    api_process.start()
    ui_process.start()

    print(f"Backend API should be running at http://{API_HOST}:{API_PORT}")
    print(f"Streamlit UI should be running at http://localhost:8501 (check terminal for exact URL)")

    # Wait for the processes to complete.
    # You will need to manually stop this script (Ctrl+C) to terminate the child processes.
    api_process.join()
    ui_process.join()

    print("Services have been terminated.")
