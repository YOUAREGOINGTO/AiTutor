# test_orchestrator_no_db.py
# test_orchestrator_no_db.py
import asyncio
import sys
import os
import django
import logging
from typing import Dict, List, Any, Optional, Tuple

# --- Configure Django Settings ---
print("Configuring Django settings...")
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tutor_project.settings')
try: django.setup(); print("Django setup complete.")
except Exception as e: print(f"FATAL: Django setup error: {e}"); sys.exit(1)

# --- Configure Logging ---
logging.basicConfig(level=logging.INFO, format='{levelname} {asctime} {name} {module} {lineno}: {message}', style='{')
logger = logging.getLogger(__name__)
logging.getLogger('api').setLevel(logging.DEBUG) # See orchestrator DEBUG logs
print("Logging configured (api set to DEBUG).")

# --- Import Orchestrator and Dependencies ---
try:
    print("Importing orchestrator components...")
    from api.orchestrator import ( process_chat_message, STAGE_START, STATE_STAGE, STATE_HISTORY, STATE_FINAL_SYLLABUS, STATE_EXPLAINER_PROMPT, STATE_TRANSITION_EXPLAINER ) # Removed unused state keys
    from api.ai_services import async_llm_call, gemini_configured # Keep LLM call for it to work
    print("Imports successful.")
    if not gemini_configured: print("\nWARNING: Gemini API Key not found or configuration failed.")
except ImportError as e: print(f"FATAL: Import error: {e}"); sys.exit(1)
# --- End Imports ---


async def chat_loop_no_db():
    """Simulates a command-line chat session using the orchestrator IN MEMORY."""
    print("\nStarting Orchestrator IN-MEMORY Test.")
    print("Tests the latest orchestrator logic (history lookup, no PENDING stage).")
    print("NO database interaction. State is lost on exit.")
    print("Uses ACTUAL LLM calls.")
    print("Type 'quit' or 'exit' to end.")
    print("=" * 50)

    # Initialize in-memory state (only persistent fields needed)
    session_state: Dict[str, Any] = {
        STATE_STAGE: STAGE_START,
        STATE_HISTORY: [],
        STATE_FINAL_SYLLABUS: None,
        STATE_EXPLAINER_PROMPT: None,
    }

    turn_counter = 0
    while True:
        turn_counter += 1
        print("-" * 20, f"Turn {turn_counter}", "-" * 20)

        # Get user input
        try: user_input = input("You: ").strip()
        except EOFError: print("\nEOF received, exiting."); break
        if user_input.lower() in ['quit', 'exit']: print("Exiting chat."); break
        if not user_input: print("(Skipping empty input)"); continue

        # --- Prepare state for THIS turn ---
        # Copy the state from the previous turn. No reconstruction needed.
        state_for_orchestrator = session_state.copy()
        logger.debug(f"CLI Test: Preparing state for orchestrator. Stage='{state_for_orchestrator.get(STATE_STAGE)}'")

        # Add current user message to the history list *within the state being passed*
        # Ensure history list exists
        if STATE_HISTORY not in state_for_orchestrator or not isinstance(state_for_orchestrator[STATE_HISTORY], list):
             state_for_orchestrator[STATE_HISTORY] = []
        state_for_orchestrator[STATE_HISTORY].append({'role': 'user', 'parts': [{'text': user_input}]})

        # Log the state being sent
        logger.debug(f"CLI Test: State being passed: Stage='{state_for_orchestrator.get(STATE_STAGE)}', History Len={len(state_for_orchestrator.get(STATE_HISTORY,[]))}, Final Syllabus Set: {state_for_orchestrator.get(STATE_FINAL_SYLLABUS) is not None}")

        try:
            # --- Call the orchestrator function ---
            print("...")
            ai_reply, next_session_state = await process_chat_message(
                user_input, state_for_orchestrator
            )

            # --- Update the main session state for the *next* loop ---
            # This directly uses the state returned by the orchestrator
            session_state = next_session_state

            # --- Output AI Response & Debug Info ---
            print(f"\nAI:  {ai_reply}")
            print("-" * 5)
            print(f"     [Debug: Stage = '{session_state.get(STATE_STAGE)}']")
            # Display flag no longer used by this orchestrator version
            # if session_state.get(STATE_DISPLAY_SYLLABUS): print("[Debug: Display Syllabus Flag Set!]")
            if session_state.get(STATE_TRANSITION_EXPLAINER):
                 print(f"     [Debug: Transition to Explainer Flag Set!]")
            print(f"     [Debug: History Len = {len(session_state.get(STATE_HISTORY, []))}]")
            print(f"     [Debug: Final Syllabus Set = {session_state.get(STATE_FINAL_SYLLABUS) is not None}]")
            print(f"     [Debug: Explainer Prompt Set = {session_state.get(STATE_EXPLAINER_PROMPT) is not None}]")
            print("-" * 5)

        except Exception as e:
            print(f"\n--- ERROR DURING ORCHESTRATOR CALL ---")
            print(f"Error Type: {type(e).__name__}: {e}")
            import traceback; traceback.print_exc()
            print("-" * 30)
            print("Session state might be inconsistent. Continuing...")

if __name__ == "__main__":
    print("Starting CLI script...")
    try:
        asyncio.run(chat_loop_no_db())
    except KeyboardInterrupt: print("\nChat interrupted.")
    except Exception as main_e: print(f"\nFATAL ERROR: {main_e}"); import traceback; traceback.print_exc()
    finally: print("\nCLI Test Finished.")
# import asyncio
# import sys
# import os
# import django
# import logging
# from typing import Dict, List, Any, Optional, Tuple

# # --- Configure Django Settings ---
# # Necessary to import modules from your Django app ('api')
# print("Configuring Django settings...")
# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tutor_project.settings') # Adjust if needed
# try:
#     django.setup()
#     print("Django setup complete.")
# except Exception as e:
#     print(f"FATAL: Error setting up Django: {e}")
#     print("Make sure:")
#     print("  1. You are running this script from your project's root directory (where manage.py is).")
#     print("  2. Your virtual environment is active.")
#     print("  3. 'tutor_project.settings' is the correct path to your settings file.")
#     sys.exit(1)
# # --- End Django Setup ---

# # --- Configure Logging ---
# # Set up basic logging to see output from orchestrator, ai_services, and this script
# logging.basicConfig(level=logging.INFO, format='{levelname} {asctime} {name} {module} {lineno}: {message}', style='{')
# logger = logging.getLogger(__name__) # Logger for this script
# # Set the logger for your 'api' app (and its submodules like orchestrator, ai_services) to DEBUG
# logging.getLogger('api').setLevel(logging.DEBUG)
# print("Logging configured (api set to DEBUG).")
# # --- End Logging Setup ---


# # --- Import Orchestrator and Dependencies ---
# try:
#     print("Importing orchestrator components...")
#     from api.orchestrator import (
#         process_chat_message,
#         # Import constants needed for initial state and inspection
#         STAGE_START, STAGE_NEGOTIATING, STAGE_EXPLAINING, STAGE_ERROR, # Stages needed
#         STATE_STAGE,
#         STATE_HISTORY,
#         STATE_CURRENT_SYLLABUS,
#         STATE_FINAL_SYLLABUS,
#         STATE_EXPLAINER_PROMPT,
#         STATE_DISPLAY_SYLLABUS,
#         STATE_TRANSITION_EXPLAINER
#     )
#     # Import LLM call and extraction helper
#     from api.ai_services import async_llm_call, gemini_configured, extract_xml
#     print("Imports successful.")

#     if not gemini_configured:
#         print("\nWARNING: Gemini API Key not found or configuration failed.")
#         print("LLM calls will likely fail or return error messages.")

# except ImportError as e:
#     print(f"FATAL: Error importing from 'api' module: {e}")
#     print("Ensure api/orchestrator.py, api/ai_services.py, api/prompts.py exist and have no import errors.")
#     sys.exit(1)
# # --- End Imports ---


# async def chat_loop_no_db():
#     """Simulates a command-line chat session using the orchestrator IN MEMORY."""
#     print("\nStarting Orchestrator IN-MEMORY Test.")
#     print("This script interacts directly with process_chat_message.")
#     print("NO database interaction occurs here. State is lost on exit.")
#     print("Uses ACTUAL LLM calls via async_llm_call.")
#     print("Type 'quit' or 'exit' to end.")
#     print("=" * 50)

#     # Initialize in-memory state for this single test session
#     session_state: Dict[str, Any] = {
#         STATE_STAGE: STAGE_START,
#         STATE_HISTORY: [],
#         STATE_CURRENT_SYLLABUS: None,
#         STATE_FINAL_SYLLABUS: None,
#         STATE_EXPLAINER_PROMPT: None,
#     }

#     turn_counter = 0
#     while True:
#         turn_counter += 1
#         print("-" * 20, f"Turn {turn_counter}", "-" * 20)

#         # Get user input
#         try:
#             user_input = input("You: ").strip()
#         except EOFError:
#              print("\nEOF received, exiting.")
#              break
#         if user_input.lower() in ['quit', 'exit']:
#             print("Exiting chat.")
#             break
#         if not user_input:
#             print("(Skipping empty input)")
#             continue

#         # --- Prepare state dictionary to pass to the orchestrator ---
#         state_for_orchestrator = session_state.copy()

#         # --- Simulate View's Reconstruction of STATE_CURRENT_SYLLABUS ---
#         logger.info("CLI Test: === Starting Syllabus Reconstruction from History ===")
#         current_syllabus_from_history = None
#         temp_history = session_state.get(STATE_HISTORY, [])
#         logger.debug(f"CLI Test: History length to scan: {len(temp_history)}")
#         try:
#             # Ensure extract_xml is available
#             # from api.ai_services import extract_xml # Already imported above

#             for i in range(len(temp_history) - 1, -1, -1): # Iterate backwards
#                 msg = temp_history[i]
#                 msg_role = msg.get('role')
#                 logger.debug(f"CLI Test: ---- Checking History Index {i}, Role: {msg_role} ----")

#                 # Check model responses that might contain the syllabus
#                 if msg_role == 'model':
#                     parts_list = msg.get('parts', [])
#                     content = ""
#                     # Robustly extract text content from parts
#                     if isinstance(parts_list, list) and len(parts_list) > 0:
#                         first_part = parts_list[0]
#                         if isinstance(first_part, dict):
#                             content = first_part.get('text', '')
#                         elif isinstance(first_part, str):
#                              content = first_part # Handle case where parts might be just strings
#                     elif isinstance(parts_list, str): # Handle case where parts itself is a string
#                          content = parts_list
#                     else:
#                          logger.warning(f"CLI Test: Unexpected parts format at index {i}: {parts_list}")

#                     logger.debug(f"CLI Test: Content at index {i}:\n'''\n{content[:300]} {'...' if len(content)>300 else ''}\n'''") # Log content start

#                     if content:
#                         # Try extracting with tags first
#                         logger.debug("CLI Test: Attempting extract_xml...")
#                         extracted = extract_xml(content, "syllabus")
#                         if extracted:
#                             current_syllabus_from_history = extracted
#                             logger.info(f"CLI Test: FOUND syllabus via extract_xml at index {i}")
#                             break # Found the latest one, stop searching

#                         # Fallback check for direct tags only if extraction fails
#                         else:
#                              logger.debug("CLI Test: extract_xml failed. Checking for direct <syllabus> tags...")
#                              content_stripped = content.strip()
#                              if content_stripped.startswith("<syllabus>") and content_stripped.endswith("</syllabus>"):
#                                  inner = content_stripped[len("<syllabus>"):-len("</syllabus>")].strip()
#                                  if inner:
#                                      current_syllabus_from_history = inner
#                                      logger.info(f"CLI Test: FOUND syllabus via direct tags at index {i}")
#                                      break
#                                  else:
#                                      logger.debug("CLI Test: Found direct tags but empty content.")
#                              # else: logger.debug("CLI Test: Direct tags not found.") # Optional

#         except Exception as recon_e:
#              logger.error(f"CLI Test: Error during syllabus reconstruction simulation: {recon_e}", exc_info=True)

#         # Log result of reconstruction
#         if not current_syllabus_from_history:
#              logger.warning("CLI Test: === Finished searching history, DID NOT FIND syllabus content. ===")
#         else:
#              logger.info("CLI Test: === Finished searching history, FOUND syllabus content. ===")
#         # --- End Syllabus Reconstruction Simulation ---


#         # Set the reconstructed value (or None) in the state dictionary that will be passed to orchestrator
#         state_for_orchestrator[STATE_CURRENT_SYLLABUS] = current_syllabus_from_history


#         # Add current user message to the history list *within the state being passed*
#         if STATE_HISTORY not in state_for_orchestrator or not isinstance(state_for_orchestrator[STATE_HISTORY], list):
#              state_for_orchestrator[STATE_HISTORY] = []
#         state_for_orchestrator[STATE_HISTORY].append(
#             {'role': 'user', 'parts': [{'text': user_input}]}
#         )

#         # Log the state being sent just before the call
#         logger.debug(f"CLI Test: State being passed to orchestrator: Stage='{state_for_orchestrator.get(STATE_STAGE)}', Has current_syllabus={state_for_orchestrator.get(STATE_CURRENT_SYLLABUS) is not None}, History Len={len(state_for_orchestrator.get(STATE_HISTORY,[]))}")


#         try:
#             # --- Call the orchestrator function ---
#             print("...") # Indicate processing
#             ai_reply, next_session_state = await process_chat_message(
#                 user_input, state_for_orchestrator
#             )

#             # --- Update the main session state for the *next* loop ---
#             session_state = next_session_state

#             # --- Output AI Response ---
#             print(f"\nAI:  {ai_reply}")

#             # --- Output state changes for debugging ---
#             print("-" * 5)
#             print(f"     [Debug: Stage = '{session_state.get(STATE_STAGE)}']")
#             if session_state.get(STATE_DISPLAY_SYLLABUS):
#                  print(f"     [Debug: Display Syllabus Flag Set! Content starts: '{str(session_state[STATE_DISPLAY_SYLLABUS])[:60]}...']")
#             if session_state.get(STATE_TRANSITION_EXPLAINER):
#                  print(f"     [Debug: Transition to Explainer Flag Set!]")
#             print(f"     [Debug: History Len = {len(session_state.get(STATE_HISTORY, []))}]")
#             print("-" * 5)


#         except Exception as e:
#             print(f"\n--- ERROR DURING ORCHESTRATOR CALL ---")
#             print(f"Error Type: {type(e).__name__}")
#             print(f"Error Details: {e}")
#             import traceback
#             traceback.print_exc()
#             print("-" * 30)
#             print("Session state might be inconsistent. Continuing...")


# if __name__ == "__main__":
#     print("Starting CLI script...")
#     try:
#         asyncio.run(chat_loop_no_db())
#     except KeyboardInterrupt:
#         print("\nChat interrupted by user (Ctrl+C).")
#     except Exception as main_e:
#          print(f"\nFATAL ERROR in script execution: {main_e}")
#          import traceback
#          traceback.print_exc()
#     finally:
#         print("\nCLI Test Finished.")