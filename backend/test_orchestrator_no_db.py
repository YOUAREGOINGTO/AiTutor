# test_orchestrator_no_db.py
import asyncio
import sys
import os
import django # For settings
import logging
from typing import Dict, List, Any, Optional, Tuple
import json # For printing dicts nicely

# --- Configure Django Settings ---
print("Configuring Django settings for test_orchestrator_no_db...")
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tutor_project.settings')
try:
    django.setup()
    print("Django setup complete.")
except Exception as e:
    print(f"FATAL: Django setup error: {e}")
    sys.exit(1)

# --- Configure Logging ---
logging.basicConfig(level=logging.INFO, format='{levelname} {asctime} {name} [{module}:{lineno}]: {message}', style='{')
logger = logging.getLogger(__name__)
logging.getLogger('api').setLevel(logging.DEBUG)
logging.getLogger('litellm').setLevel(logging.WARNING)
print("Logging configured (api set to DEBUG, litellm to WARNING).")

# --- Import Orchestrator and Dependencies ---
try:
    print("Importing orchestrator components...")
    from api.orchestrator import (
        process_chat_message,
        STAGE_START, STATE_STAGE, STATE_HISTORY, STATE_FINAL_SYLLABUS,
        STATE_EXPLAINER_PROMPT, STATE_TRANSITION_EXPLAINER_FLAG, STATE_DISPLAY_SYLLABUS_FLAG,
        STATE_GENERATED_TITLE, DEFAULT_CHAT_TITLE, format_history_for_dspy,
        STATE_CURRENT_TITLE, STATE_EXPLANATION_START_INDEX,
        get_last_syllabus_content_from_history
    )
    from api.ai_services import get_dspy_lm, extract_xml # Added extract_xml as it's used in get_last_syllabus
    from api.resource_processor import (_extract_text_from_txt_bytes,
                                     _extract_text_from_pdf_bytes,
                                     _extract_text_from_docx_bytes) # For load_test_resource_files
    print("Orchestrator and service imports successful.")

    if get_dspy_lm() is None:
        print("\nCRITICAL WARNING: DSPy LM is NOT configured. LLM calls will fail.")
    else:
        print(f"DSPy LM configured: {type(get_dspy_lm())} with model {get_dspy_lm().model}")

except ImportError as e:
    logger.critical(f"FATAL: Import error: {e}", exc_info=True)
    sys.exit(1)
except Exception as e_import_other:
    logger.critical(f"FATAL: Unexpected error during imports: {e_import_other}", exc_info=True)
    sys.exit(1)

# --- Helper to Simulate File Reading for Testing ---
def load_test_resource_files(file_paths: List[str]) -> Dict[str, str]:
    mock_uploaded_file_data = {}
    if not file_paths:
        return mock_uploaded_file_data

    print(f"\n--- Loading Test Resources for Orchestrator ---")
    for file_path in file_paths:
        if not os.path.exists(file_path):
            logger.error(f"Test resource file not found: {file_path}. Skipping.")
            continue
        if not os.path.isfile(file_path):
            logger.error(f"Test resource path is not a file: {file_path}. Skipping.")
            continue

        filename = os.path.basename(file_path)
        try:
            with open(file_path, 'rb') as f:
                file_bytes = f.read()

            ext = filename.split('.')[-1].lower() if '.' in filename else ''
            text_content = None
            if ext == 'txt':
                text_content = _extract_text_from_txt_bytes(file_bytes, filename)
            elif ext == 'pdf':
                text_content = _extract_text_from_pdf_bytes(file_bytes, filename)
            elif ext == 'docx':
                text_content = _extract_text_from_docx_bytes(file_bytes, filename)
            else:
                logger.warning(f"Unsupported test file type: {filename}. Skipping.")
                continue
            
            if text_content:
                mock_uploaded_file_data[filename] = text_content
                logger.info(f"Loaded test resource '{filename}', length {len(text_content)} chars.")
            else:
                logger.warning(f"Could not extract text from test resource: {filename}")

        except Exception as e:
            logger.error(f"Error loading test resource '{filename}': {e}", exc_info=True)
    print(f"--- Finished Loading Test Resources. {len(mock_uploaded_file_data)} files processed. ---\n")
    return mock_uploaded_file_data


async def interactive_chat_loop():
    """Simulates a command-line chat session using the orchestrator IN MEMORY."""
    print("\nStarting Interactive Orchestrator Test (DSPy Version).")
    print("Type 'quit' or 'exit' to end.")
    print("You can provide local file paths for resources at the beginning.")
    print("=" * 70)

    # --- Initialize In-Memory State for this Test Session ---
    session_state: Dict[str, Any] = {
        STATE_STAGE: STAGE_START,
        STATE_HISTORY: [],
        STATE_FINAL_SYLLABUS: None,
        STATE_EXPLAINER_PROMPT: None,
        STATE_EXPLANATION_START_INDEX: None,
        STATE_CURRENT_TITLE: DEFAULT_CHAT_TITLE,
    }
    
    simulated_uploaded_data: Optional[Dict[str, str]] = None
    first_turn = True

    # Ask for resources on the first turn
    try:
        provide_resources_input = input("Do you want to provide local resource files for this session? (yes/no): ").strip().lower()
        if provide_resources_input == 'yes':
            resource_paths_str = input("Enter full paths to resource files, separated by commas: ").strip('"').strip("'")
            if resource_paths_str:
                resource_file_paths = [path.strip() for path in resource_paths_str.split(',') if path.strip()]
                if resource_file_paths:
                    simulated_uploaded_data = load_test_resource_files(resource_file_paths)
                    if not simulated_uploaded_data:
                        print("No valid resources were loaded despite providing paths.")
                else:
                    print("No resource paths entered.")
            else:
                print("No resource paths entered.")
        else:
            print("Skipping resource loading.")
    except EOFError:
        print("\nEOF received during initial setup. Exiting.")
        return
    except Exception as e_setup:
        print(f"Error during resource setup: {e_setup}. Continuing without resources.")


    turn_counter = 0
    while True:
        turn_counter += 1
        print(f"\n--- Turn {turn_counter} ---")

        try:
            user_input_text = input("You: ").strip()
        except EOFError:
            print("\nEOF received, ending chat.")
            break
        if user_input_text.lower() in ['quit', 'exit']:
            print("AI: Exiting chat.")
            break
        if not user_input_text:
            print("(Skipping empty input)")
            continue

        # Add user message to history
        session_state[STATE_HISTORY].append({'role': 'user', 'parts': [{'text': user_input_text}]})

        current_turn_resource_data = None
        if first_turn and simulated_uploaded_data:
            current_turn_resource_data = simulated_uploaded_data
            logger.info("Passing simulated resource data to orchestrator for the first turn.")
        
        first_turn = False # Resources are only passed on the very first call to process_chat_message

        try:
            print("...") # Indicate processing
            ai_reply, next_session_state_from_orchestrator = await process_chat_message(
                user_message_text=user_input_text,
                current_session_state=session_state.copy(),
                uploaded_resource_data=current_turn_resource_data
            )

            session_state = next_session_state_from_orchestrator

            print(f"\nAI:  {ai_reply}")
            print("-" * 10)
            # print(f"  [State: Stage = '{session_state.get(STATE_STAGE)}', Title='{session_state.get(STATE_CURRENT_TITLE)}']")
            if session_state.get(STATE_DISPLAY_SYLLABUS_FLAG):
                 syllabus_content = session_state.get(STATE_DISPLAY_SYLLABUS_FLAG)
                 # Extract only the inner content for brief display if it's XML
                 inner_syllabus = extract_xml(syllabus_content, "syllabus") if isinstance(syllabus_content, str) else str(syllabus_content)
                 print(f"  [Flag: Display Syllabus - Content: '{inner_syllabus[:100].replace(chr(10), ' ')}...']")
            if session_state.get(STATE_TRANSITION_EXPLAINER_FLAG):
                 print(f"  [Flag: Transition to Explainer!]")
            if session_state.get(STATE_GENERATED_TITLE) and session_state.get(STATE_GENERATED_TITLE) != session_state.get(STATE_CURRENT_TITLE):
                 print(f"  [New Title Generated: {session_state.get(STATE_GENERATED_TITLE)} (will be saved by view)]")
                 session_state[STATE_CURRENT_TITLE] = session_state.get(STATE_GENERATED_TITLE) # Simulate view updating title

            # print(f"  [History for DSPy (last 2):]")
            # formatted_hist_for_log = format_history_for_dspy(session_state.get(STATE_HISTORY, [])[-2:])
            # for line in formatted_hist_for_log.split("\n---\n"): print(f"    {line.strip().replace(chr(10), ' ')}")
            # print(f"  [Final Syllabus Set: {session_state.get(STATE_FINAL_SYLLABUS) is not None}]")
            # print(f"  [Explainer Prompt Set: {session_state.get(STATE_EXPLAINER_PROMPT) is not None}]")
            print("-" * 10)
            current_history_list = session_state.get(STATE_HISTORY, [])
            # print(current_history_list)


        except Exception as e:
            print(f"\n--- ERROR DURING ORCHESTRATOR CALL ---")
            logger.error(f"Orchestrator call failed in test: {e}", exc_info=True)
            print("Session state might be inconsistent. Continuing...")
            # Optionally break or ask user if they want to reset state
    
    print(f"\n{'='*20} Interactive Test Session Finished {'='*20}")

if __name__ == "__main__":
    print("Starting Interactive CLI test script for orchestrator (DSPy)...")
    if get_dspy_lm() is None:
        print("CRITICAL ERROR: DSPy LM is not configured. Test cannot run effectively.")
    else:
        try:
            asyncio.run(interactive_chat_loop())
        except KeyboardInterrupt:
            print("\nTest script interrupted by user (Ctrl+C).")
        except Exception as main_e:
            logger.critical(f"FATAL ERROR in script execution: {main_e}", exc_info=True)

        finally:
            print("\nCLI Test Script Finished.")