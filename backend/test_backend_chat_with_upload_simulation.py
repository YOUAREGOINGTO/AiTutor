# test_backend_chat_with_upload_simulation.py
import requests # pip install requests
import json
import os
from typing import List, Dict, Optional, Any

# --- Configuration ---
BASE_API_URL = "http://127.0.0.1:8001/api/chat/" # Your Django backend URL

DEFAULT_TEST_FILE_PATHS: List[str] = [
    r"C:\Users\yaswa\OneDrive\Desktop\Research Papers\Attention is all You need.pdf",

]

# --- Helper to prepare files for requests library ---
def prepare_files_for_request(file_paths: List[str]) -> Optional[tuple[List[tuple], List[Any]]]:
    """
    Opens files and prepares them in the format requests library expects for multipart uploads.
    Returns a tuple: (list_of_prepared_files, list_of_opened_file_objects_to_close)
    or None if there's a critical error or no valid files are prepared.
    Each item in list_of_prepared_files is: ('resource_files', (filename, file_object, content_type))
    """
    if not file_paths:
        return None

    prepared_files_list = []
    file_objects_to_close = [] # Keep track to close them later

    for file_path in file_paths:
        if not os.path.exists(file_path) or not os.path.isfile(file_path):
            print(f"Warning: File not found or is not a file: {file_path}. Skipping.")
            continue
        
        try:
            # Open the file in binary read mode
            file_object = open(file_path, 'rb')
            file_objects_to_close.append(file_object) 
            
            filename = os.path.basename(file_path)
            
            # Basic content type guessing (can be improved with python-magic if needed)
            content_type = 'application/octet-stream' # Default
            if filename.endswith('.pdf'):
                content_type = 'application/pdf'
            elif filename.endswith('.txt'):
                content_type = 'text/plain'
            elif filename.endswith('.docx'):
                content_type = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            # Add more mimetypes if needed

            # Append to the list in the format requests expects for multipart files
            prepared_files_list.append(('resource_files', (filename, file_object, content_type)))
        except Exception as e:
            print(f"Error opening or preparing file {file_path}: {e}")
            # If one file fails, we might still want to process others,
            # but ensure already opened files are tracked for closure.
            # For simplicity here, if a critical error occurs, we could return None.
            # Let's decide to skip this problematic file and continue with others.
            continue 

    if not prepared_files_list: # If no files were successfully prepared
        # Ensure any opened FOs (e.g., if one opened then another failed) are closed
        for fo in file_objects_to_close:
            try: fo.close()
            except: pass # Ignore errors on close during cleanup
        return None
        
    return prepared_files_list, file_objects_to_close


def run_interactive_chat_test():
    print("--- Backend Interactive Chat Test ---")
    print(f"Targeting API: {BASE_API_URL}")
    print("Type 'quit' or 'exit' to end the session.")
    print("Type 'newsession' to start a new chat (and use pre-defined or prompted files).")
    if DEFAULT_TEST_FILE_PATHS:
        print(f"Default test files for new sessions: {DEFAULT_TEST_FILE_PATHS}")
    else:
        print("No default test files specified. You will be prompted for new sessions.")
    print("-" * 40)

    current_session_id: Optional[str] = None
    is_first_message_in_session = True # True when current_session_id is None and about to send first message
    
    while True:
        try:
            user_input_text = input("You: ").strip()
        except EOFError:
            print("\nEOF received. Exiting.")
            break

        if user_input_text.lower() in ['quit', 'exit']:
            print("Exiting chat test.")
            break
        
        if user_input_text.lower() == 'newsession':
            current_session_id = None
            is_first_message_in_session = True # Reset for the new session
            print("\n--- Starting new session ---")
            print("Enter your first message for this new session.")
            continue # Go to next input prompt for the actual message

        if not user_input_text:
            continue

        payload_data: Dict[str, Any] = {'user_message': user_input_text}
        if current_session_id:
            payload_data['session_id'] = current_session_id

        files_to_send_prepared: Optional[List[tuple]] = None
        opened_file_objects: List[Any] = []

        # File handling logic ONLY for the first message of a new session
        if is_first_message_in_session and not current_session_id:
            local_file_paths_to_use: List[str] = []
            if DEFAULT_TEST_FILE_PATHS: # Check if default paths are provided
                print(f"Using pre-defined files for this new session: {DEFAULT_TEST_FILE_PATHS}")
                local_file_paths_to_use = DEFAULT_TEST_FILE_PATHS
            else: # Fallback to prompting if no defaults
                try:
                    provide_files_choice = input("This is the first message of a new session. Upload files? (yes/no, default no): ").strip().lower()
                    if provide_files_choice == 'yes':
                        paths_str = input("Enter full local file paths, comma-separated: ").strip()
                        if paths_str:
                            local_file_paths_to_use = [p.strip().strip("'\"") for p in paths_str.split(',') if p.strip()]
                except EOFError: 
                    print("\nEOF during file prompt. Exiting.")
                    break 
            
            if local_file_paths_to_use:
                prep_result = prepare_files_for_request(local_file_paths_to_use)
                if prep_result:
                    files_to_send_prepared, opened_file_objects = prep_result
                    if files_to_send_prepared:
                        print(f"Prepared {len(files_to_send_prepared)} files for upload.")
                    else:
                        print("No valid files were prepared from the paths provided.")
                else:
                    print("Failed to prepare any files from the paths provided.")
            else:
                print("No files will be sent for this new session.")
        
        headers = {}
        response_json: Optional[Dict[str, Any]] = None
        response_object: Optional[requests.Response] = None # To access response.text if JSON fails
        
        try:
            print("Sending request...")
            if files_to_send_prepared and is_first_message_in_session and not current_session_id:
                # Send as multipart/form-data
                print(f"Sending MULTIPART request with data: {payload_data} and {len(files_to_send_prepared)} files.")
                response_object = requests.post(BASE_API_URL, data=payload_data, files=files_to_send_prepared)
            else:
                # Send as JSON
                headers['Content-Type'] = 'application/json'
                print(f"Sending JSON request with data: {json.dumps(payload_data)}")
                response_object = requests.post(BASE_API_URL, data=json.dumps(payload_data), headers=headers)

            response_object.raise_for_status() # Raise an exception for HTTP errors (4xx or 5xx)
            response_json = response_object.json()

        except requests.exceptions.HTTPError as http_err:
            print(f"HTTP error occurred: {http_err}")
            if hasattr(http_err, 'response') and http_err.response is not None:
                print(f"Error Response Status: {http_err.response.status_code}")
                try:
                    print(f"Error Response Body: {http_err.response.json()}")
                except json.JSONDecodeError:
                    print(f"Error Response Body (not JSON): {http_err.response.text}")
            continue 
        except requests.exceptions.RequestException as req_err:
            print(f"Request failed: {req_err}")
            continue 
        except json.JSONDecodeError:
            print("Failed to decode JSON response from server.")
            if response_object: print(f"Server raw response: {response_object.text}")
            continue
        finally:
            # IMPORTANT: Close any file objects that were opened
            for fo in opened_file_objects:
                try:
                    fo.close()
                except Exception as e_close:
                    print(f"Warning: Error closing a file object: {e_close}")

        if response_json:
            ai_reply = response_json.get('ai_reply', "[No AI reply found in response]")
            new_state_flags = response_json.get('new_state', {})
            returned_session_id = response_json.get('session_id')

            print(f"\nAI: {ai_reply}")
            print(f"  [Session ID: {returned_session_id}]")
            print(f"  [New State Flags: {new_state_flags}]")
            
            if returned_session_id:
                current_session_id = returned_session_id # Update for subsequent requests
            
            # After the first message in a session (new or existing), it's no longer the "first message"
            # for the purpose of initiating file uploads with this script's logic.
            is_first_message_in_session = False 
        
        print("-" * 20)

if __name__ == "__main__":
    run_interactive_chat_test()