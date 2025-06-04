# interactive_live_backend_test.py
import asyncio
import httpx
import json
import logging
import os # For checking if file exists for resource prompt

# --- Configure Logging ---
logging.basicConfig(level=logging.INFO, format='{levelname} {asctime} {name} [{module}:{lineno}]: {message}', style='{')
logger = logging.getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.WARNING) # Quiet httpx logs

# --- Backend Server URL ---
BACKEND_CHAT_API_URL = "http://127.0.0.1:8001/api/chat/"

# --- Global HTTP Client & Session ID ---
http_client: httpx.AsyncClient = None
current_session_id: str = None # Will be updated after the first successful response

async def initialize_client():
    global http_client
    if http_client is None: # Initialize only if not already done
        http_client = httpx.AsyncClient(timeout=90.0)
        logger.info("HTTPX AsyncClient initialized.")

async def close_client():
    global http_client
    if http_client:
        await http_client.aclose()
        logger.info("HTTPX AsyncClient closed.")
        http_client = None

async def send_chat_message_to_server(
    user_message: str,
    session_id_to_send: str # Pass current_session_id from the loop
) -> dict: # Returns parsed JSON response or an error dict
    """Sends a message to the backend chat API and returns the JSON response."""
    if not http_client:
        # This should not happen if initialize_client is called first, but good safeguard
        await initialize_client() 

    payload = {"user_message": user_message}
    if session_id_to_send:
        payload["session_id"] = session_id_to_send

    print(f"\n>>> Sending to backend (Session: {session_id_to_send or 'NEW'}):")
    print(f"    User: \"{user_message}\"")
    print("    ...") # Indicate sending

    try:
        response = await http_client.post(BACKEND_CHAT_API_URL, json=payload)
        response.raise_for_status()
        response_data = response.json()
        
        print(f"\n<<< Received from backend (Status: {response.status_code}):")
        ai_reply = response_data.get("ai_reply", "[NO AI REPLY FROM SERVER]")
        print(f"    AI: \"{ai_reply}\"") # Print full AI reply for interactive chat

        # Display key state flags from server for context
        server_new_state = response_data.get("new_state", {})
        server_stage = server_new_state.get("stage", "Unknown")
        display_syllabus_flag = server_new_state.get("display_syllabus_flag")
        transition_explainer_flag = server_new_state.get("transition_to_explainer_flag", False)

        print("    --- Server State Update ---")
        print(f"    Server Stage: {server_stage}")
        if display_syllabus_flag:
            print(f"    Syllabus Display Flag: Content starts with '{str(display_syllabus_flag)[:100].replace(chr(10), ' ')}...'")
            # In a real UI, you'd render this. Here, we just note its presence.
        if transition_explainer_flag:
            print(f"    Transition to Explainer Flag: True")
        print("    ---------------------------")
        
        return response_data

    except httpx.HTTPStatusError as e:
        error_msg = f"HTTP error response {e.response.status_code} while requesting {e.request.url!r}."
        logger.error(error_msg)
        try:
            error_details = e.response.json()
            logger.error(f"Server error details: {error_details}")
            print(f"!!! SERVER ERROR: {error_msg} Details: {error_details}")
            return {"error": error_msg, "details": error_details, "_raw_text": e.response.text}
        except json.JSONDecodeError:
            logger.error(f"Server error (non-JSON): {e.response.text}")
            print(f"!!! SERVER ERROR: {error_msg} Raw: {e.response.text}")
            return {"error": error_msg, "details": e.response.text}
    except httpx.RequestError as e:
        error_msg = f"Request error while requesting {e.request.url!r}: {e}"
        logger.error(error_msg)
        print(f"!!! REQUEST ERROR: {error_msg}")
        return {"error": "Request failed", "details": str(e)}
    except json.JSONDecodeError as e:
        # This implies server returned success status but malformed JSON
        error_msg = f"Failed to decode JSON response from server: {e.msg}"
        logger.error(error_msg)
        print(f"!!! JSON DECODE ERROR: {error_msg}")
        return {"error": "Invalid JSON response", "details": e.msg}


async def interactive_chat_loop():
    global current_session_id # Allow updating the global session ID

    print("\n--- Interactive Chat with LIVE Backend Server (Uses Database) ---")
    print(f"Targeting API: {BACKEND_CHAT_API_URL}")
    print("Type 'quit' or 'exit' to end.")
    print("NOTE: Resource simulation (if any) happens on the SERVER SIDE for new sessions, based on `SIMULATED_RESOURCE_FILE_PATHS_FOR_NEW_SESSION` in `api/views.py`.")
    print("Make sure that list in `views.py` points to valid files on the server machine if you want to test resource processing for new chats.")
    print("=" * 70)

    await initialize_client() # Initialize the client once for the session
    
    turn_counter = 0
    while True:
        turn_counter += 1
        session_display = current_session_id if current_session_id else "NEW"
        print(f"\n--- Turn {turn_counter} (Session: {session_display}) ---")

        try:
            user_input_text = input("You: ").strip()
        except EOFError:
            print("\nEOF received, ending chat.")
            break
        if user_input_text.lower() in ['quit', 'exit']:
            print("CLIENT: Exiting chat.")
            break
        if not user_input_text:
            print("(Skipping empty input)")
            continue

        server_response = await send_chat_message_to_server(
            user_message=user_input_text,
            session_id_to_send=current_session_id # Pass the current session ID
        )

        if server_response:
            # Update session ID if it's a new session or if it changed (shouldn't change after first response)
            if server_response.get("session_id"):
                newly_returned_session_id = server_response["session_id"]
                if current_session_id is None:
                    current_session_id = newly_returned_session_id
                    logger.info(f"CLIENT: New session started with ID: {current_session_id}")
                elif current_session_id != newly_returned_session_id:
                    # This should generally not happen if the backend is stable.
                    logger.warning(f"CLIENT: Session ID changed by server from {current_session_id} to {newly_returned_session_id}! This is unexpected.")
                    current_session_id = newly_returned_session_id
            
            if "error" in server_response:
                # Specific error handling if needed, e.g., if server returns 500, maybe stop
                logger.error(f"CLIENT: Received error response from server: {server_response.get('details', 'No details')}")
                if "Server error: 500" in server_response.get("error", ""):
                    print("!!! Critical server error (500). Further interaction may fail. Check server logs.")
        else:
            # This case means send_chat_message_to_server itself had a major issue before getting a parsable response
            print("CLIENT: Did not receive a valid response structure from server. Check connection or server status.")
            # break # Optionally break the loop if communication is totally lost

    await close_client() # Clean up the client when the loop ends
    print(f"\n{'='*20} Interactive Server Test Session Finished {'='*20}")

if __name__ == "__main__":
    print("Starting Interactive CLI test script for live Django server...")
    # Make sure your Django/Uvicorn server is running on http://127.0.0.1:8001
    # and SIMULATED_RESOURCE_FILE_PATHS_FOR_NEW_SESSION in views.py is set if desired.
    try:
        asyncio.run(interactive_chat_loop())
    except KeyboardInterrupt:
        print("\nTest script interrupted by user (Ctrl+C).")
    except Exception as main_e:
        logger.critical(f"FATAL ERROR in script execution: {main_e}", exc_info=True)
    finally:
        # Ensure client is closed even if main loop errors out unexpectedly
        if http_client and not http_client.is_closed:
            logger.info("Ensuring HTTP client is closed in final cleanup...")
            asyncio.run(close_client()) # Must run async close
        print("\nCLI Server Test Script Finished.")