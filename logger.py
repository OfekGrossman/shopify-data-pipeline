from datetime import datetime, timezone, date
import json
from config import LOG_DIR
import inspect
from pathlib import Path

def log_message(message: str = None, level: str = "INFO", stage: str = None, **kwargs) -> None:

    """
    Logs a message to a log file with a timestamp,caller file and line number, stage, log level and other information and prints it to the console.

    Args:
        message (str): The message to log.
        level (str): The log level (e.g., "INFO", "ERROR"). Default is "INFO".
        stage (str): The stage of the process where the log message is generated.
        **kwargs: Additional keyword arguments to include in the log entry.
    """
    
    # Ensure the log directory exists
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    # the frame that CALLED this function
    frame = inspect.currentframe().f_back   
    caller_file = Path(frame.f_code.co_filename).name   # just the filename, no path
    caller_line = frame.f_lineno   # the line number in the caller's file

    # Create a timestamp for the log entry
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S %Z")

    # Create the log entry as a dictionary
    log_entry = {
        "timestamp": timestamp,
        "file": caller_file+":"+str(caller_line),
        "level": level,
        "message": message,
        "stage": stage,
        **kwargs
    }

    # Define the log file path based on the current date
    log_file_path = LOG_DIR / f"log_{date.today().isoformat()}.jsonl"

    # Append the log entry to the log file in JSON format
    with open(log_file_path, "a", encoding="utf-8") as log_file:
        line = json.dumps(log_entry, ensure_ascii=False)
        print(line)
        log_file.write(line + "\n")   

if __name__ == "__main__":
    # Example usage of the log_message function
    log_message("This is an info message.")
    log_message("This is an error message.", level="ERROR")
    log_message("This is an info message.", stage="data_extraction", rows=123)