# api/views.py
import json
import logging
import uuid
import re # Added for internal tag checking
import asyncio
from typing import Dict, Any, Optional, List

from django.http import JsonResponse, HttpRequest, Http404
from django.views.decorators.csrf import csrf_exempt
from asgiref.sync import sync_to_async as database_sync_to_async

from .models import ChatSession, ChatMessage
from .orchestrator import (
    process_chat_message,
    STAGE_START, STAGE_NEGOTIATING, STAGE_EXPLAINING, STAGE_ERROR,
    STATE_STAGE, STATE_HISTORY, STATE_FINAL_SYLLABUS,
    STATE_EXPLAINER_PROMPT, STATE_EXPLANATION_START_INDEX,
    STATE_DISPLAY_SYLLABUS, STATE_TRANSITION_EXPLAINER,
    # --- ADD THESE TWO ---
    STATE_CURRENT_TITLE,
    STATE_GENERATED_TITLE
    # --- END ADDITION ---
)


logger = logging.getLogger(__name__)

# --- Define known internal command tags ---
INTERNAL_COMMAND_TAGS = [
    "<request_syllabus_generation/>",
    "<request_syllabus_modification/>",
    "<request_finalization/>",
    "<persona/>",
]

# --- Database Helper Functions (Async) ---

@database_sync_to_async
def get_or_create_session(session_id_str: Optional[str]) -> tuple[ChatSession, bool]:
    """Loads or creates a ChatSession."""
    session_id: Optional[uuid.UUID] = None
    session: Optional[ChatSession] = None
    is_new = False
    if session_id_str:
        try:
            session_id = uuid.UUID(session_id_str)
            session = ChatSession.objects.filter(session_id=session_id).first()
            if session:
                logger.info(f"Found existing session: {session_id}")
                return session, is_new
            else:
                logger.warning(f"Session ID {session_id_str} not found. Creating new.")
                session_id = None
        except (ValueError, TypeError):
            logger.warning(f"Invalid Session ID '{session_id_str}'. Creating new.")
            session_id = None
    if session_id is None:
        session = ChatSession.objects.create()
        is_new = True
        logger.info(f"Created new session: {session.session_id}")
    assert session is not None
    return session, is_new

@database_sync_to_async
def load_chat_history(session: ChatSession) -> List[Dict[str, Any]]:
    """Loads and formats chat history (role, parts with text) for orchestrator."""
    messages = ChatMessage.objects.filter(session=session).order_by('timestamp', 'order').values('role', 'content')
    # Format matches Gemini's expected input history structure
    history = [{"role": msg['role'], "parts": [{'text': msg['content']}]} for msg in messages]
    logger.info(f"Loaded {len(history)} messages for session {session.session_id} (orchestrator format)")
    return history

@database_sync_to_async
def save_message(session: ChatSession, role: str, content: str, order: int, message_type: Optional[str] = None) -> Optional[ChatMessage]:
    """
    Saves message. Determines message_type for model/system syllabus
    and identifies internal command messages from the model.
    """
    if not content:
        if role != 'system' or not message_type:
            logger.debug(f"Skipping save for empty message. Role: {role}, Order: {order}")
            return None

    determined_type = 'message' # Default

    if message_type: # Use explicitly passed type if available
        determined_type = message_type
        logger.debug(f"Using explicitly passed message_type: '{determined_type}' for Order {order}")
    elif role == 'model':
        content_stripped_lower = content.strip().lower() if content else ""
        if content_stripped_lower in INTERNAL_COMMAND_TAGS:
            determined_type = 'internal'
            logger.debug(f"Identified internal command message. Setting type='internal' for Order {order}")
        elif "<syllabus>" in content_stripped_lower and "</syllabus>" in content_stripped_lower:
            determined_type = 'syllabus'
            logger.debug(f"Identified syllabus message. Setting type='syllabus' for Order {order}")
        else:
            determined_type = 'message' # Standard model response
            # logger.debug(f"Standard model message detected. Setting type='message' for Order {order}")
    elif role == 'system':
         if "--- Starting Learning Session ---" in content:
             determined_type = 'info'
         # else: keep default 'message' for other system msgs

    try:
        msg = ChatMessage.objects.create(
            session=session, role=role, content=content, order=order, message_type=determined_type
        )
        logger.debug(f"Saved message {msg.message_id} (Order: {order}, Role: {role}, Type: {msg.message_type})")
        return msg
    except Exception as e:
        logger.error(f"DB error saving msg order {order} for session {session.session_id}: {e}", exc_info=True)
        return None

@database_sync_to_async
def update_session_state(session: ChatSession, new_state: Dict[str, Any]):
    """Updates persistent state fields on the ChatSession model."""
    try: session.refresh_from_db() # Refresh to avoid race conditions if needed elsewhere
    except Exception as e: logger.error(f"Failed refresh session {session.session_id} before update: {e}")

    stage = new_state.get(STATE_STAGE)
    final_syllabus = new_state.get(STATE_FINAL_SYLLABUS)
    explainer_prompt = new_state.get(STATE_EXPLAINER_PROMPT)
    explainer_index = new_state.get(STATE_EXPLANATION_START_INDEX)

    updated_fields = ['updated_at'] # Always update this
    changed = False

    if stage and session.current_stage != stage:
        session.current_stage = stage; updated_fields.append('current_stage'); changed = True
    if final_syllabus is not None and session.final_syllabus_xml != final_syllabus:
        session.final_syllabus_xml = final_syllabus; updated_fields.append('final_syllabus_xml'); changed = True
    if explainer_prompt is not None and session.explainer_system_prompt != explainer_prompt:
        session.explainer_system_prompt = explainer_prompt; updated_fields.append('explainer_system_prompt'); changed = True
    if explainer_index is not None and session.explanation_start_index != explainer_index:
        session.explanation_start_index = explainer_index; updated_fields.append('explanation_start_index'); changed = True

    if changed:
        try:
            session.save(update_fields=updated_fields)
            logger.info(f"Updated session {session.session_id} state. Fields: {updated_fields}")
        except Exception as e:
            logger.error(f"DB error updating session state for {session.session_id}: {e}", exc_info=True)
    else:
        # If only updated_at needs saving (no state change, just activity)
        try:
             session.save(update_fields=['updated_at'])
        except Exception as e:
             logger.error(f"DB error updating session updated_at for {session.session_id}: {e}", exc_info=True)


# --- API View Functions ---

# --- Main Chat Endpoint (POST message) ---
@csrf_exempt # Exempt the main chat endpoint
async def plain_django_chat_view(request: HttpRequest):
    """Handles POST requests for sending messages."""
    if request.method == 'POST':
        # ... (Implementation remains the same as provided before) ...
        # ... It uses the updated save_message internally ...
        logger.info("------ Chat Message Handler (POST /api/chat/) ------")
        session: Optional[ChatSession] = None
        history_from_db: List[Dict[str, Any]] = []
        try:
            body = request.body; request_data = {}
            if not body: return JsonResponse({"error": "Request body empty."}, status=400)
            try: request_data = json.loads(body); logger.debug(f"Received data: {request_data}")
            except json.JSONDecodeError: return JsonResponse({"error": "Invalid JSON."}, status=400)
            user_message = request_data.get('user_message'); session_id_str = request_data.get('session_id')
            if not user_message or not isinstance(user_message, str): return JsonResponse({"error": "user_message required."}, status=400)
            if session_id_str is not None and not isinstance(session_id_str, str): logger.warning(f"Received non-string session_id: {type(session_id_str)}. Treating as null."); session_id_str = None

            session, is_new_session = await get_or_create_session(session_id_str)
            history_from_db = await load_chat_history(session) # For orchestrator context

            current_state = { STATE_STAGE: session.current_stage, STATE_HISTORY: list(history_from_db), STATE_FINAL_SYLLABUS: session.final_syllabus_xml, STATE_EXPLAINER_PROMPT: session.explainer_system_prompt, STATE_EXPLANATION_START_INDEX: session.explanation_start_index,STATE_CURRENT_TITLE: session.title, }
            logger.debug(f"View prepared current_state: Stage='{current_state.get(STATE_STAGE)}', Title='{current_state.get(STATE_CURRENT_TITLE)}', History Len={len(current_state.get(STATE_HISTORY))}") 

            last_saved_message = await database_sync_to_async( ChatMessage.objects.filter(session=session).order_by('-timestamp', '-order').first )()
            last_order = last_saved_message.order if last_saved_message else -1
            user_message_order = last_order + 1
            await save_message(session, 'user', user_message, user_message_order, message_type='message')

            history_len_before_user_msg = len(current_state[STATE_HISTORY])
            current_state[STATE_HISTORY].append({'role': 'user', 'parts': [{'text': user_message}]})

            logger.info(f"Processing message for session {session.session_id} (New: {is_new_session}) in stage: {current_state.get(STATE_STAGE)}")
            ai_reply, new_state = await process_chat_message(user_message, current_state) # Orchestrator call

            # Save messages added by orchestrator
            returned_history = new_state.get(STATE_HISTORY, [])
            num_new_messages = len(returned_history) - (history_len_before_user_msg + 1)
            if num_new_messages > 0:
                 logger.info(f"View found {num_new_messages} new message(s) added by orchestrator.")
                 start_index_in_returned = history_len_before_user_msg + 1
                 for i in range(num_new_messages):
                     msg_index = start_index_in_returned + i
                     if msg_index < len(returned_history):
                         message_to_save = returned_history[msg_index]; msg_role = message_to_save.get("role", "unknown")
                         if msg_role != "user":
                             parts_list = message_to_save.get('parts', []); msg_content = ""
                             if isinstance(parts_list, list) and len(parts_list) > 0: first_part = parts_list[0]; msg_content = first_part.get('text', '') if isinstance(first_part, dict) else first_part if isinstance(first_part, str) else ""
                             elif isinstance(parts_list, str): msg_content = parts_list
                             await save_message(session, msg_role, msg_content, user_message_order + 1 + i) # Uses updated save_message
                         else: logger.warning(f"Orchestrator added 'user' message at index {msg_index}.")
            elif ai_reply and (not returned_history or returned_history[-1].get('role') == 'user'):
                 logger.warning(f"Orchestrator didn't add AI message to history list. Saving ai_reply separately.")
                 await save_message(session, 'model', ai_reply, user_message_order + 1) # Uses updated save_message
            elif not ai_reply and num_new_messages == 0: logger.warning(f"Orchestrator returned no ai_reply and added no messages.")

            await update_session_state(session, new_state)
            generated_title = new_state.get(STATE_GENERATED_TITLE)
            if generated_title and isinstance(generated_title, str) and generated_title.strip():
                try:
                    # Refresh just the title field to get the most current value before comparing
                    await session.arefresh_from_db(fields=['title'])
                    logger.debug(f"VIEW: Refreshed title is '{session.title}' before save check.")
                except Exception as refresh_err:
                    logger.error(f"VIEW: Error refreshing session title before save check: {refresh_err}")
                    # Proceed cautiously, compare against potentially stale session.title

                # Save only if the title in the DB is different from the generated one
                if session.title != generated_title:
                    logger.info(f"View received generated title '{generated_title}' from orchestrator. Saving...")
                    try:
                        session.title = generated_title # Update object in memory
                        # Save ONLY the title field. updated_at was handled by update_session_state.
                        await database_sync_to_async(session.save)(update_fields=['title'])
                        logger.info(f"View successfully saved generated title for session {session.session_id}")
                    except Exception as save_err:
                        logger.error(f"View failed to save generated title '{generated_title}': {save_err}", exc_info=True)
                else:
                    logger.debug(f"View received generated title '{generated_title}', but session title already matches. Skipping save.")
            elif generated_title is not None:
                 logger.warning(f"Orchestrator returned a non-True generated title: '{generated_title}'. Skipping title save.")


            response_data = { "ai_reply": ai_reply, "new_state": { STATE_STAGE: new_state.get(STATE_STAGE, session.current_stage), STATE_DISPLAY_SYLLABUS: new_state.get(STATE_DISPLAY_SYLLABUS), STATE_TRANSITION_EXPLAINER: new_state.get(STATE_TRANSITION_EXPLAINER, False), }, "session_id": str(session.session_id) }
            logger.info(f"Successfully processed message for session {session.session_id}. Returning state flags: {response_data['new_state']}")
            return JsonResponse(response_data, status=200)
        except Exception as e:
            logger.error(f"Unexpected error processing message for session {session.session_id if session else 'None'}: {e}", exc_info=True); error_stage = STAGE_ERROR; session_id_to_return = str(session.session_id) if session else None
            if session: 
                try: session.current_stage = STAGE_ERROR; await database_sync_to_async(session.save)(update_fields=['current_stage', 'updated_at']); logger.info(f"Set session stage to ERROR.") 
                except Exception as db_err: logger.error(f"CRITICAL: Failed to update session stage to ERROR: {db_err}", exc_info=True)
            return JsonResponse({"ai_reply": "[SYSTEM ERROR]", "new_state": { STATE_STAGE: error_stage }, "session_id": session_id_to_return}, status=500)
    else:
        return JsonResponse({"error": f"Method {request.method} Not Allowed"}, status=405, headers={"Allow": "POST"})

# @csrf_exempt
# async def plain_django_chat_view(request: HttpRequest):
#     """
#     Handles POST requests for sending messages. Loads/creates session, passes state
#     (including current title) to the orchestrator, processes orchestrator's response,
#     saves messages, saves generated title if provided by orchestrator, updates
#     session state (stage, etc.), and returns the immediate AI reply to the frontend.
#     """
#     if request.method == 'POST':
#         logger.info("------ Chat Message Handler (POST /api/chat/) ------")
#         session: Optional[ChatSession] = None
#         try:
#             # --- 1. Request Parsing and Validation ---
#             body = request.body; request_data = {}
#             if not body: return JsonResponse({"error": "Request body empty."}, status=400)
#             try: request_data = json.loads(body); logger.debug(f"Received data: {request_data}")
#             except json.JSONDecodeError: return JsonResponse({"error": "Invalid JSON."}, status=400)
#             user_message = request_data.get('user_message'); session_id_str = request_data.get('session_id')
#             if not user_message or not isinstance(user_message, str): return JsonResponse({"error": "user_message required."}, status=400)
#             if session_id_str is not None and not isinstance(session_id_str, str): session_id_str = None; logger.warning("Invalid session_id type.")

#             # --- 2. Load/Create Session and History ---
#             session, is_new_session = await get_or_create_session(session_id_str)
#             history_for_orchestrator = await load_chat_history(session)

#             # --- 3. Prepare Current State for Orchestrator ---
#             current_state_for_orchestrator = { # Use a distinct name
#                 STATE_STAGE: session.current_stage,
#                 STATE_HISTORY: list(history_for_orchestrator),
#                 STATE_FINAL_SYLLABUS: session.final_syllabus_xml,
#                 STATE_EXPLAINER_PROMPT: session.explainer_system_prompt,
#                 STATE_EXPLANATION_START_INDEX: session.explanation_start_index,
#                 STATE_CURRENT_TITLE: session.title, # Pass current title
#             }
#             logger.debug(f"View prepared state: Stage='{current_state_for_orchestrator.get(STATE_STAGE)}', Title='{current_state_for_orchestrator.get(STATE_CURRENT_TITLE)}', History Len={len(current_state_for_orchestrator.get(STATE_HISTORY))}")

#             # --- 4. Save User Message ---
#             last_saved_message = await database_sync_to_async( ChatMessage.objects.filter(session=session).order_by('-timestamp', '-order').first )()
#             last_order = last_saved_message.order if last_saved_message else -1
#             user_message_order = last_order + 1
#             await save_message(session, 'user', user_message, user_message_order, message_type='message')

#             # --- 5. Add User Message to In-Memory History for Orchestrator Call ---
#             current_state_for_orchestrator[STATE_HISTORY].append({'role': 'user', 'parts': [{'text': user_message}]})

#             logger.info(f"Processing message for session {session.session_id} (New: {is_new_session}) in stage: {current_state_for_orchestrator.get(STATE_STAGE)}")

#             # --- 6. Call the Core Orchestrator Logic ---
#             ai_reply, new_state_from_orchestrator = await process_chat_message(user_message, current_state_for_orchestrator) # Use distinct name

#             # --- 7. Save AI/System Message(s) Added by Orchestrator ---
#             returned_history = new_state_from_orchestrator.get(STATE_HISTORY, [])
#             history_len_before_llm_msgs = len(current_state_for_orchestrator[STATE_HISTORY]) # Length *after* user msg was added in memory
#             num_new_messages_by_llm = len(returned_history) - history_len_before_llm_msgs
#             if num_new_messages_by_llm > 0:
#                 logger.info(f"View found {num_new_messages_by_llm} new message(s).")
#                 start_index_in_returned = history_len_before_llm_msgs
#                 for i in range(num_new_messages_by_llm):
#                      msg_index = start_index_in_returned + i
#                      if msg_index < len(returned_history):
#                          message_to_save = returned_history[msg_index]; msg_role = message_to_save.get("role", "unknown")
#                          if msg_role != "user":
#                              parts_list = message_to_save.get('parts', []); msg_content = ""
#                              if isinstance(parts_list, list) and parts_list: first_part = parts_list[0]; msg_content = first_part.get('text', '') if isinstance(first_part, dict) else first_part if isinstance(first_part, str) else ""
#                              elif isinstance(parts_list, str): msg_content = parts_list
#                              await save_message(session, msg_role, msg_content, user_message_order + 1 + i)
#                          else: logger.warning(f"Orchestrator added 'user' msg at index {msg_index}.")
#             elif ai_reply:
#                 logger.warning(f"Orchestrator didn't add AI msg. Saving ai_reply separately.")
#                 await save_message(session, 'model', ai_reply, user_message_order + 1)
#             else: logger.warning(f"No new messages or reply from orchestrator.")

#             # --- 8. Update Session State (Stage, Prompts, etc.) ---
#             # This saves fields based on the 'new_state' dict AND updates 'updated_at'.
#             await update_session_state(session, new_state_from_orchestrator)

#             # --- 9. Save Generated Title IF Returned by Orchestrator ---
#             # This block runs *after* update_session_state
#             generated_title = new_state_from_orchestrator.get(STATE_GENERATED_TITLE)
#             if generated_title and isinstance(generated_title, str) and generated_title.strip():
#                 # Refreshing ensures we compare against the most current DB state *after* step 8 ran.
#                 await session.arefresh_from_db(fields=['title'])
#                 if session.title != generated_title:
#                     logger.info(f"View received generated title '{generated_title}' from orchestrator. Saving...")
#                     try:
#                         session.title = generated_title # Update object in memory
#                         # Save ONLY the title field. `updated_at` was handled by update_session_state.
#                         await database_sync_to_async(session.save)(update_fields=['title'])
#                         logger.info(f"View successfully saved generated title for session {session.session_id}")
#                     except Exception as save_err:
#                         logger.error(f"View failed to save generated title '{generated_title}': {save_err}", exc_info=True)
#                         # Optionally revert session.title in memory
#                         # session.title = current_state_for_orchestrator.get(STATE_CURRENT_TITLE, DEFAULT_CHAT_TITLE)
#                 else:
#                     logger.debug(f"View received generated title '{generated_title}', but session title already matches. Skipping save.")
#             elif generated_title is not None:
#                  logger.warning(f"Orchestrator returned a non-True generated title: '{generated_title}'. Skipping title save.")
#             # else: No generated title key provided by orchestrator.

#             # --- 10. Prepare and Send Response ---
#             response_data = {
#                 "ai_reply": ai_reply,
#                 "new_state": {
#                     STATE_STAGE: new_state_from_orchestrator.get(STATE_STAGE, session.current_stage),
#                     STATE_DISPLAY_SYLLABUS: new_state_from_orchestrator.get(STATE_DISPLAY_SYLLABUS),
#                     STATE_TRANSITION_EXPLAINER: new_state_from_orchestrator.get(STATE_TRANSITION_EXPLAINER, False),
#                 },
#                 "session_id": str(session.session_id)
#             }
#             logger.info(f"Successfully processed message for session {session.session_id}. Returning state flags: {response_data['new_state']}")
#             return JsonResponse(response_data, status=200)

#         # --- Error Handling ---
#         except Exception as e:
#              logger.error(f"Unexpected error processing message for session {session.session_id if session else 'None'}: {e}", exc_info=True); error_stage = STAGE_ERROR; session_id_to_return = str(session.session_id) if session else None
#              if session: 
#                  try: session.current_stage = STAGE_ERROR; await database_sync_to_async(session.save)(update_fields=['current_stage', 'updated_at']); logger.info(f"Set session stage to ERROR.") 
#                  except Exception as db_err: logger.error(f"CRITICAL: Failed to update session stage to ERROR: {db_err}", exc_info=True)
#              return JsonResponse( {"ai_reply": "[SYSTEM ERROR]", "new_state": { STATE_STAGE: error_stage }, "session_id": session_id_to_return}, status=500 )
#     else:
#         # --- Method Not Allowed ---
#         logger.warning(f"Unsupported method on /api/chat/: {request.method}")
#         return JsonResponse({"error": f"Method {request.method} Not Allowed"}, status=405, headers={"Allow": "POST"})

# --- List Sessions Endpoint (GET) ---
@database_sync_to_async
def list_chat_sessions(request: HttpRequest):
    """Lists chat sessions, ordered by last updated."""
    # TODO: Filter by request.user when auth is added
    sessions = ChatSession.objects.all().order_by('-updated_at').values(
        'session_id', 'title', 'updated_at', 'current_stage'
    )
    session_list = list(sessions)
    for session in session_list:
        if 'updated_at' in session and session['updated_at']:
            session['updated_at'] = session['updated_at'].isoformat()
    logger.info(f"Fetched {len(session_list)} sessions.")
    return JsonResponse({"sessions": session_list})

# Async wrapper for list_chat_sessions
async def list_chat_sessions_async(request: HttpRequest):
    if request.method != 'GET':
         return JsonResponse({'error': 'Method Not Allowed'}, status=405)
    return await list_chat_sessions(request)


# --- Get Session Details Endpoint (GET) ---
@database_sync_to_async
def get_session_details(request: HttpRequest, session_id: uuid.UUID):
    """Fetches full history and state for a specific session."""
    try:
        # TODO: Filter by request.user when auth is added
        session = ChatSession.objects.get(session_id=session_id)
        # Query messages and format for frontend display (including type)
        messages = ChatMessage.objects.filter(session=session).order_by('timestamp', 'order')
        history = [ { "role": msg.role, "content": msg.content, "type": msg.message_type, "timestamp": msg.timestamp.isoformat() if msg.timestamp else None } for msg in messages ]
        logger.info(f"Fetched details for session {session_id}. History length: {len(history)}")
        response_data = { "session_id": str(session.session_id), "title": session.title, "current_stage": session.current_stage, "final_syllabus_xml": session.final_syllabus_xml, "explainer_system_prompt": session.explainer_system_prompt, "explanation_start_index": session.explanation_start_index, "history": history, "updated_at": session.updated_at.isoformat() if session.updated_at else None, }
        return JsonResponse(response_data)
    except ChatSession.DoesNotExist:
        # Return 404 directly if session not found
        return JsonResponse({'error': 'Session not found'}, status=404)
    except Exception as e:
        logger.error(f"Error fetching details for session {session_id}: {e}", exc_info=True)
        return JsonResponse({"error": "Failed to fetch session details"}, status=500)

# Async wrapper for get_session_details
async def get_session_details_async(request: HttpRequest, session_id_str: str):
    if request.method != 'GET':
         return JsonResponse({'error': 'Method Not Allowed'}, status=405)
    try:
        session_uuid = uuid.UUID(session_id_str)
        return await get_session_details(request, session_uuid)
    except (ValueError, TypeError):
        return JsonResponse({"error": "Invalid session ID format."}, status=400)
    except Exception as e:
        logger.error(f"Unexpected error in get_session_details_async wrapper: {e}", exc_info=True)
        return JsonResponse({"error": "Internal server error"}, status=500)


# --- Delete Session Endpoint (DELETE) ---
# (Sync part - NO @csrf_exempt here)
@database_sync_to_async
def delete_session(request: HttpRequest, session_id: uuid.UUID):
    """Handles actual DB deletion for DELETE requests."""
    try:
        # TODO: Add user check
        session = ChatSession.objects.get(session_id=session_id)
        session_id_str = str(session.session_id)
        session.delete()
        logger.info(f"Successfully deleted session {session_id_str}")
        return JsonResponse({}, status=204) # No Content
    except ChatSession.DoesNotExist:
        return JsonResponse({'error': 'Session not found'}, status=404)
    except Exception as e:
        logger.error(f"Error deleting session {session_id}: {e}", exc_info=True)
        return JsonResponse({'error': 'Internal server error during deletion'}, status=500)

# (Async wrapper - APPLY @csrf_exempt here)
@csrf_exempt # Apply decorator to the view function called by Django
async def delete_session_async(request: HttpRequest, session_id_str: str):
    """Async wrapper for delete_session view, handles DELETE method."""
    if request.method != 'DELETE':
        return JsonResponse({'error': 'Method Not Allowed'}, status=405)
    try:
        session_uuid = uuid.UUID(session_id_str)
        return await delete_session(request, session_uuid) # Await the sync-wrapped function
    except (ValueError, TypeError):
        return JsonResponse({"error": "Invalid session ID format."}, status=400)
    except Exception as e:
        logger.error(f"Unexpected error in delete_session_async wrapper: {e}", exc_info=True)
        return JsonResponse({"error": "Internal server error"}, status=500)


# --- Update Session Title Endpoint (PATCH) ---
# (Sync part - NO @csrf_exempt here)
@database_sync_to_async
def update_session_title(request: HttpRequest, session_id: uuid.UUID):
    """Handles actual DB update for PATCH requests."""
    try:
        # TODO: Add user check
        session = ChatSession.objects.get(session_id=session_id)
        try:
            data = json.loads(request.body)
            new_title = data.get('title')
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON format'}, status=400)

        if not new_title or not isinstance(new_title, str) or not new_title.strip():
             return JsonResponse({'error': "Missing, invalid, or empty 'title' field"}, status=400)

        new_title = new_title.strip()
        max_length = 200 # Example limit
        if len(new_title) > max_length: new_title = new_title[:max_length]

        session.title = new_title
        session.save(update_fields=['title', 'updated_at']) # Also update timestamp
        logger.info(f"Successfully updated title for session {session_id} to '{new_title}'")
        response_data = { 'session_id': str(session.session_id), 'title': session.title, 'updated_at': session.updated_at.isoformat() if session.updated_at else None }
        return JsonResponse(response_data, status=200)

    except ChatSession.DoesNotExist:
        return JsonResponse({'error': 'Session not found'}, status=404)
    except Exception as e:
        logger.error(f"Error updating session title for {session_id}: {e}", exc_info=True)
        return JsonResponse({'error': 'Internal server error during title update'}, status=500)

# (Async wrapper - APPLY @csrf_exempt here)
@csrf_exempt # Apply decorator to the view function called by Django
async def update_session_title_async(request: HttpRequest, session_id_str: str):
    """Async wrapper for update_session_title view, handles PATCH method."""
    if request.method != 'PATCH':
         return JsonResponse({'error': 'Method Not Allowed'}, status=405)
    try:
        session_uuid = uuid.UUID(session_id_str)
        return await update_session_title(request, session_uuid) # Await the sync-wrapped function
    except (ValueError, TypeError):
        return JsonResponse({"error": "Invalid session ID format."}, status=400)
    except Exception as e:
        logger.error(f"Unexpected error in update_session_title_async wrapper: {e}", exc_info=True)
        return JsonResponse({"error": "Internal server error"}, status=500)