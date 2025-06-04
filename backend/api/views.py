# api/views.py
import json
import logging
import uuid
import os
import asyncio
from typing import Dict, Any, Optional, List
from django.http import JsonResponse, HttpRequest, Http404
from django.views.decorators.csrf import csrf_exempt
from asgiref.sync import sync_to_async as database_sync_to_async
from django.conf import settings # To get MEDIA_ROOT
from .models import ChatSession, ChatMessage
from .orchestrator import (
    process_chat_message,
    STAGE_START, STAGE_NEGOTIATING, STAGE_EXPLAINING, STAGE_ERROR,
    STATE_STAGE, STATE_HISTORY, STATE_FINAL_SYLLABUS,
    STATE_EXPLAINER_PROMPT, STATE_EXPLANATION_START_INDEX,
    STATE_CURRENT_TITLE, STATE_GENERATED_TITLE,
    STATE_DISPLAY_SYLLABUS_FLAG, STATE_TRANSITION_EXPLAINER_FLAG
    # format_history_for_dspy # This helper is now in orchestrator.py
)
# from .ai_services import extract_xml # This is also in orchestrator.py if needed there, or keep a copy in ai_services.py for general use

# For simulated resource loading (temporary)
from .resource_processor import (_extract_text_from_txt_bytes,
                               _extract_text_from_pdf_bytes,
                               _extract_text_from_docx_bytes,process_uploaded_files)

logger = logging.getLogger(__name__)

INTERNAL_COMMAND_TAGS = [
    "<request_syllabus_generation/>",
    "<request_syllabus_modification/>",
    "<request_finalization/>",
    "<persona/>",
]
def save_extracted_text_to_server(
    session_id: uuid.UUID,
    original_filename: str,
    text_content: str
) -> Optional[str]:
    """
    Saves the given text content to a .txt file on the server
    within a session-specific directory.
    Returns the relative path to the saved file or None on failure.
    """
    try:
        # Sanitize original_filename to create a safe new filename
        base_name, _ = os.path.splitext(original_filename)
        safe_base_name = "".join(c if c.isalnum() or c in (' ', '_', '-') else '_' for c in base_name).rstrip()
        if not safe_base_name: # Handle cases where filename becomes empty after sanitization
            safe_base_name = f"resource_{uuid.uuid4().hex[:8]}"
        
        txt_filename = f"{safe_base_name}.txt"

        # Create a session-specific directory path
        # MEDIA_ROOT / uploaded_resources / <session_id_str> / file.txt
        session_dir_name = str(session_id)
        relative_session_path = os.path.join('uploaded_resources', session_dir_name)
        absolute_session_dir = os.path.join(settings.MEDIA_ROOT, relative_session_path)
        
        os.makedirs(absolute_session_dir, exist_ok=True) # Create directory if it doesn't exist

        absolute_file_path = os.path.join(absolute_session_dir, txt_filename)
        
        # Prevent simple path traversal (though os.path.join usually handles this for basename)
        if os.path.commonprefix((os.path.realpath(absolute_file_path), settings.MEDIA_ROOT)) != str(settings.MEDIA_ROOT):
            logger.error(f"Potential path traversal attempt for filename '{txt_filename}' in session '{session_id}'. Denying save.")
            return None

        with open(absolute_file_path, 'w', encoding='utf-8') as f:
            f.write(text_content)
        
        # Return the path relative to MEDIA_ROOT for storage in the model
        relative_file_path = os.path.join(relative_session_path, txt_filename)
        logger.info(f"Saved extracted text from '{original_filename}' to '{relative_file_path}' for session '{session_id}'.")
        return relative_file_path
    except Exception as e:
        logger.error(f"Error saving extracted text for '{original_filename}' (session {session_id}): {e}", exc_info=True)
        return None
# --- Database Helper Functions (Async) ---
# api/views.py
# ... (existing imports) ...
import uuid # For generating unique temp filenames
import os
from django.conf import settings
from django.http import JsonResponse, HttpRequest
from django.views.decorators.csrf import csrf_exempt # If needed for this new endpoint
from .resource_processor import process_uploaded_files # Assuming this can handle a list with one file

logger = logging.getLogger(__name__)


@csrf_exempt 
async def upload_temp_resource_view(request: HttpRequest):
    if request.method != 'POST':
        return JsonResponse({"success": False, "error": "Method Not Allowed"}, status=405)

    try:
        if not request.FILES.getlist('resource_file'): # Frontend will send as 'resource_file'
            return JsonResponse({"success": False, "error": "No file provided in 'resource_file' field."}, status=400)

        uploaded_file = request.FILES.getlist('resource_file')[0] # Get the first (and only) file
        original_filename = uploaded_file.name

        logger.info(f"Temporary upload: Received '{original_filename}' for pre-processing.")

        # Use existing process_uploaded_files by wrapping the single file in a list
        extracted_data = process_uploaded_files([uploaded_file])

        if not extracted_data or original_filename not in extracted_data:
            logger.error(f"Temporary upload: Failed to extract text from '{original_filename}'.")
            return JsonResponse({"success": False, "error": f"Could not extract text from {original_filename}."}, status=500)

        text_content = extracted_data[original_filename]

        # --- Save extracted text to a temporary file ---
        temp_dir_path = os.path.join(settings.MEDIA_ROOT, settings.TEMP_UPLOAD_DIR_NAME)
        os.makedirs(temp_dir_path, exist_ok=True)

        # Generate a unique filename for the temporary text file
        temp_text_filename = f"{uuid.uuid4().hex}.txt"
        temp_text_filepath = os.path.join(temp_dir_path, temp_text_filename)

        with open(temp_text_filepath, 'w', encoding='utf-8') as f:
            f.write(text_content)

        logger.info(f"Temporary upload: Saved extracted text for '{original_filename}' to temp file '{temp_text_filename}'.")

        return JsonResponse({
            "success": True,
            "tempServerId": temp_text_filename, # This is the ID the frontend needs
            "originalFilename": original_filename # Send back original name for later use
        }, status=200)

    except Exception as e:
        logger.error(f"Error in upload_temp_resource_view: {e}", exc_info=True)
        return JsonResponse({"success": False, "error": "Internal server error during temporary file processing."}, status=500)
# @database_sync_to_async # For now Resource Uploading is Synchronous
def load_and_extract_simulated_resources(file_paths: List[str]) -> Dict[str, str]:
    extracted_data = {}
    if not file_paths:
        return extracted_data
    logger.info(f"Simulating resource loading for {len(file_paths)} paths in view.")
    for file_path in file_paths:
        if not os.path.exists(file_path) or not os.path.isfile(file_path):
            logger.error(f"Simulated resource: Path '{file_path}' not found or not a file. Skipping.")
            continue
        filename = os.path.basename(file_path)
        try:
            with open(file_path, 'rb') as f:
                file_bytes = f.read()
            
            # Get file extension
            ext = ''
            if '.' in filename:
                ext = filename.split('.')[-1].lower()
            
            text_content = None
            if ext == 'txt':
                text_content = _extract_text_from_txt_bytes(file_bytes, filename)
            elif ext == 'pdf':
                text_content = _extract_text_from_pdf_bytes(file_bytes, filename)
            elif ext == 'docx':
                text_content = _extract_text_from_docx_bytes(file_bytes, filename)
            else:
                logger.warning(f"Simulated resource: Unsupported file type '{filename}' with extension '{ext}'. Skipping.")
                continue
            
            if text_content:
                extracted_data[filename] = text_content
                logger.info(f"Simulated resource: Loaded '{filename}', length {len(text_content)} chars.")
            else:
                logger.warning(f"Simulated resource: No text extracted from '{filename}'.")
        except Exception as e:
            logger.error(f"Simulated resource: Error loading '{filename}': {e}", exc_info=True)
    return extracted_data


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
    logger.debug(f"Loading chat history for session {session.session_id}...")
    messages_from_db = ChatMessage.objects.filter(session=session).order_by('timestamp', 'order').values(
        'role', 
        'content', 
        'message_type'  # We confirmed this should be here
    )
    
    history = []
    for msg_data in messages_from_db:
        history_item = {
            "role": msg_data['role'],
            "parts": [{'text': msg_data['content']}],
            "message_type": msg_data['message_type'] # And included here
        }
        history.append(history_item)
        logger.debug(f"Loaded DB msg for history: Role='{msg_data['role']}', DB_Msg_Type='{msg_data['message_type']}', Content='{msg_data['content'][:30]}...'") # ADD THIS LOG
    logger.info(f"Loaded {len(history)} messages for session {session.session_id} (orchestrator format, with message_type).")
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
    logger.info(
        f"SAVE_MESSAGE: About to create ChatMessage. "
        f"Role='{role}', Order={order}, "
        f"DETERMINED_TYPE_TO_SAVE='{determined_type}', " # <<< MOST IMPORTANT
        f"Content Snippet='{content[:70]}...'"
    )
    # ---- END ADD THIS LOG ----

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
    try: session.refresh_from_db()
    except Exception as e: logger.error(f"Failed refresh session {session.session_id} before update: {e}")

    stage = new_state.get(STATE_STAGE)
    final_syllabus = new_state.get(STATE_FINAL_SYLLABUS)
    explainer_prompt = new_state.get(STATE_EXPLAINER_PROMPT)
    explainer_index = new_state.get(STATE_EXPLANATION_START_INDEX)

    res_type = new_state.get("resource_type_for_syllabus_gen") # Match orchestrator key
    res_content_json = new_state.get("resource_content_json_for_syllabus_gen") # Match orchestrator key
    raw_data_dynamic = new_state.get('raw_resource_data_for_dynamic_summary') # Match orchestrator key
    initial_summary_mgr = new_state.get("resource_summary_overview_for_manager") # Match orchestrator key

    updated_fields = ['updated_at']
    changed = False

    if stage and session.current_stage != stage:
        session.current_stage = stage; updated_fields.append('current_stage'); changed = True
    if final_syllabus is not None and session.final_syllabus_xml != final_syllabus:
        session.final_syllabus_xml = final_syllabus; updated_fields.append('final_syllabus_xml'); changed = True
    if explainer_prompt is not None and session.explainer_system_prompt != explainer_prompt:
        session.explainer_system_prompt = explainer_prompt; updated_fields.append('explainer_system_prompt'); changed = True
    if explainer_index is not None and session.explanation_start_index != explainer_index:
        session.explanation_start_index = explainer_index; updated_fields.append('explanation_start_index'); changed = True
    
    # Persist resource info if it's different
    if res_type is not None and session.processed_resource_type != res_type:
        session.processed_resource_type = res_type; updated_fields.append('processed_resource_type'); changed = True
    if res_content_json is not None and session.processed_resource_content_json != res_content_json:
        session.processed_resource_content_json = res_content_json; updated_fields.append('processed_resource_content_json'); changed = True
    
    if raw_data_dynamic is not None: # This is a Dict
        raw_data_dynamic_json_str = json.dumps(raw_data_dynamic)
        if session.raw_data_for_dynamic_summary_json != raw_data_dynamic_json_str:
            session.raw_data_for_dynamic_summary_json = raw_data_dynamic_json_str
            updated_fields.append('raw_data_for_dynamic_summary_json')
            changed = True
    elif session.raw_data_for_dynamic_summary_json is not None: # Clear it if not present in new_state
        session.raw_data_for_dynamic_summary_json = None
        updated_fields.append('raw_data_for_dynamic_summary_json'); changed = True

    if initial_summary_mgr is not None and session.initial_resource_summary_for_manager != initial_summary_mgr:
        session.initial_resource_summary_for_manager = initial_summary_mgr
        updated_fields.append('initial_resource_summary_for_manager'); changed = True


    if changed:
        try:
            session.save(update_fields=list(set(updated_fields))) # Use set to avoid duplicates
            logger.info(f"Updated session {session.session_id} state. Fields: {updated_fields}")
        except Exception as e:
            logger.error(f"DB error updating session state for {session.session_id}: {e}", exc_info=True)
    else:
        try: session.save(update_fields=['updated_at'])
        except Exception as e: logger.error(f"DB error updating session updated_at for {session.session_id}: {e}", exc_info=True)

@csrf_exempt
async def plain_django_chat_view(request: HttpRequest):
    if request.method != 'POST':
        logger.warning(f"Unsupported method on /api/chat/: {request.method}")
        return JsonResponse({"error": f"Method {request.method} Not Allowed"}, status=405, headers={"Allow": "POST"})

    logger.info("------ Chat Message Handler (POST /api/chat/) ------")
    session_model_instance: Optional[ChatSession] = None
    # This will hold data for orchestrator, derived from temp files or direct upload
    orchestrator_resource_data: Optional[Dict[str, str]] = None
    # This will hold info about temp files to be finalized after session creation
    temp_resources_to_finalize: List[Dict[str, Any]] = [] # Ensure it's always a list

    try:
        # --- 1. Request Parsing and Validation ---
        user_message_text: Optional[str] = None
        session_id_str_from_request: Optional[str] = None
        direct_uploaded_files: List[Any] = [] # For direct multipart upload (fallback)
        # Frontend sends: temp_resources: [{tempServerId: "uuid.txt", originalFilename: "user_file.pdf"}]
        temp_resources_payload: Optional[List[Dict[str, str]]] = None

        if 'multipart/form-data' in request.content_type: # Fallback for direct upload
            user_message_text = request.POST.get('user_message')
            session_id_str_from_request = request.POST.get('session_id')
            direct_uploaded_files = request.FILES.getlist('resource_files')
            logger.info(f"Multipart request: User msg: '{user_message_text}', Session: {session_id_str_from_request}, Files: {len(direct_uploaded_files)}")
        else: # JSON request (expected for new flow with temp_resources)
            try:
                request_data = json.loads(request.body)
                user_message_text = request_data.get('user_message')
                session_id_str_from_request = request_data.get('session_id')
                temp_resources_payload = request_data.get('temp_resources') # Array of {tempServerId, originalFilename}
                logger.info(f"JSON request: User msg: '{user_message_text}', Session: {session_id_str_from_request}, Temp Resources: {len(temp_resources_payload) if temp_resources_payload else 0}")
            except json.JSONDecodeError:
                logger.error("Invalid JSON in request body (and not multipart).")
                return JsonResponse({"error": "Invalid JSON or request format."}, status=400)

        if not user_message_text and not temp_resources_payload and not direct_uploaded_files:
            return JsonResponse({"error": "A 'user_message' or 'temp_resources' or direct file uploads are required."}, status=400)
        
        user_message_text = user_message_text or "" # Ensure it's a string if None (e.g. only files sent)

        if session_id_str_from_request is not None and not isinstance(session_id_str_from_request, str):
            logger.warning(f"Invalid session_id format received: {session_id_str_from_request}. Treating as new session if applicable.")
            session_id_str_from_request = None


        # --- 2. Load/Create Session and History ---
        session_model_instance, is_new_session = await get_or_create_session(session_id_str_from_request)
        orchestrator_input_history = await load_chat_history(session_model_instance)
        # --- End 2. ---

        # --- 3. Prepare Resource Data for Orchestrator ---
        if is_new_session:
            if temp_resources_payload: # New flow: Use pre-processed temporary files
                logger.info(f"New session ({session_model_instance.session_id}): Processing {len(temp_resources_payload)} pre-uploaded temp resources.")
                orchestrator_resource_data = {}
                temp_dir_path = os.path.join(settings.MEDIA_ROOT, settings.TEMP_UPLOAD_DIR_NAME)

                for res_info in temp_resources_payload:
                    temp_server_id = res_info.get('tempServerId')
                    original_filename = res_info.get('originalFilename')
                    if not temp_server_id or not original_filename:
                        logger.warning(f"Skipping invalid temp resource info in payload: {res_info}")
                        continue

                    temp_filepath = os.path.join(temp_dir_path, temp_server_id)
                    if os.path.exists(temp_filepath) and os.path.isfile(temp_filepath):
                        try:
                            with open(temp_filepath, 'r', encoding='utf-8') as f:
                                text_content = f.read()
                            orchestrator_resource_data[original_filename] = text_content
                            temp_resources_to_finalize.append({
                                "temp_filepath": temp_filepath,
                                "original_filename": original_filename,
                                "text_content": text_content
                            })
                            logger.debug(f"Loaded text from temp file: {temp_server_id} for orchestrator.")
                        except Exception as e:
                            logger.error(f"Error reading temp file {temp_server_id}: {e}", exc_info=True)
                    else:
                        logger.warning(f"Temp resource file not found or is not a file: {temp_filepath}. It might have been already processed or deleted.")
                if not orchestrator_resource_data: orchestrator_resource_data = None # Ensure None if empty

            elif direct_uploaded_files: # Fallback: Direct multipart upload on new session
                logger.info(f"New session ({session_model_instance.session_id}): Processing {len(direct_uploaded_files)} directly uploaded files.")
                orchestrator_resource_data = process_uploaded_files(direct_uploaded_files)
                # For this flow, text_content will be saved directly later, no temp_resources_to_finalize
            else:
                logger.info(f"New session ({session_model_instance.session_id}): No resources provided.")
        # --- End 3. ---

        # --- 4. Prepare Current State for Orchestrator ---
        current_state_for_orchestrator = {
            STATE_STAGE: session_model_instance.current_stage,
            STATE_HISTORY: list(orchestrator_input_history), # Use a copy
            STATE_FINAL_SYLLABUS: session_model_instance.final_syllabus_xml,
            STATE_EXPLAINER_PROMPT: session_model_instance.explainer_system_prompt,
            STATE_EXPLANATION_START_INDEX: session_model_instance.explanation_start_index,
            STATE_CURRENT_TITLE: session_model_instance.title,
        }
        if not is_new_session: # Load persisted resource info for existing sessions
            current_state_for_orchestrator.update({
                "resource_type_for_syllabus_gen": session_model_instance.processed_resource_type,
                "resource_content_json_for_syllabus_gen": session_model_instance.processed_resource_content_json,
                "raw_resource_data_for_dynamic_summary": json.loads(session_model_instance.raw_data_for_dynamic_summary_json)
                                                        if session_model_instance.raw_data_for_dynamic_summary_json else None,
                "resource_summary_overview_for_manager": session_model_instance.initial_resource_summary_for_manager
            })
        # --- End 4. ---

        # --- 5. Save User Message to DB & Add to In-Memory History for Orchestrator ---
        last_message_in_db = await database_sync_to_async(
            ChatMessage.objects.filter(session=session_model_instance).order_by('-timestamp', '-order').first
        )()
        current_message_order = (last_message_in_db.order + 1) if last_message_in_db else 0
        
        await save_message(session_model_instance, 'user', user_message_text, current_message_order)
        current_state_for_orchestrator[STATE_HISTORY].append({'role': 'user', 'parts': [{'text': user_message_text}]})
        history_len_before_orchestrator_adds = len(current_state_for_orchestrator[STATE_HISTORY])
        # --- End 5. ---

        # --- 6. Call the Core Orchestrator Logic ---
        logger.info(f"Calling orchestrator for session {session_model_instance.session_id} (New: {is_new_session}) with {len(orchestrator_resource_data or {})} resources.")
        ai_reply_text, new_state_from_orchestrator = await process_chat_message(
            user_message_text=user_message_text,
            current_session_state=current_state_for_orchestrator,
            uploaded_resource_data=orchestrator_resource_data
        )
        # --- End 6. ---

        # --- 7. Save AI/System Message(s) Added by Orchestrator to DB ---
        returned_history_from_orchestrator = new_state_from_orchestrator.get(STATE_HISTORY, [])
        num_new_messages_by_orchestrator = len(returned_history_from_orchestrator) - history_len_before_orchestrator_adds
        next_message_order_start = current_message_order + 1

        if num_new_messages_by_orchestrator > 0:
            logger.debug(f"View: Orchestrator added {num_new_messages_by_orchestrator} new message(s) to history list.")
            for i in range(num_new_messages_by_orchestrator):
                msg_index_in_returned_hist = history_len_before_orchestrator_adds + i
                if msg_index_in_returned_hist < len(returned_history_from_orchestrator):
                    message_to_save_dict = returned_history_from_orchestrator[msg_index_in_returned_hist]
                    msg_role = message_to_save_dict.get("role", "model")
                    msg_content_parts = message_to_save_dict.get('parts', [])
                    msg_content = ""
                    if isinstance(msg_content_parts, list) and msg_content_parts:
                        first_part = msg_content_parts[0]
                        if isinstance(first_part, dict): msg_content = first_part.get('text', '')
                        elif isinstance(first_part, str): msg_content = first_part
                    elif isinstance(msg_content_parts, str): msg_content = msg_content_parts
                    
                    msg_type_from_orchestrator = message_to_save_dict.get("message_type") # Orchestrator might set this
                    
                    if msg_role != "user": # Don't re-save user messages
                        await save_message(
                            session_model_instance, msg_role, msg_content,
                            next_message_order_start + i, message_type=msg_type_from_orchestrator
                        )
        elif ai_reply_text and not returned_history_from_orchestrator: # Should ideally not happen if orchestrator updates history
             logger.warning("View: Orchestrator returned ai_reply_text but no new history. Saving reply as 'model' message.")
             await save_message(session_model_instance, 'model', ai_reply_text, next_message_order_start)
        # --- End 7. ---

        # --- 8. Update Session Model State (Stage, Prompts, Orchestrator-set resource fields etc.) ---
        await update_session_state(session_model_instance, new_state_from_orchestrator)
        # --- End 8. ---

        # --- 9. Finalize Resource Saving for New Sessions and Update ChatSession.resource_file_paths ---
        saved_resource_paths_for_session: List[str] = []
        list_of_original_filenames_for_session: List[str] = [] 

        if is_new_session:
            if temp_resources_to_finalize: # New flow with pre-processed files
                logger.info(f"Finalizing {len(temp_resources_to_finalize)} temp resources for session {session_model_instance.session_id}")
                for res_data in temp_resources_to_finalize:
                    saved_path = save_extracted_text_to_server(
                        session_model_instance.session_id,
                        res_data["original_filename"],
                        res_data["text_content"]
                    )
                    if saved_path:
                        saved_resource_paths_for_session.append(saved_path)
                    list_of_original_filenames_for_session.append(res_data["original_filename"]) # Capture original name
                    try:
                        os.remove(res_data["temp_filepath"])
                        logger.debug(f"Deleted temp file: {res_data['temp_filepath']}")
                    except OSError as e:
                        logger.error(f"Error deleting temp file {res_data['temp_filepath']}: {e}", exc_info=True)

            elif orchestrator_resource_data and direct_uploaded_files: # Fallback: direct multipart upload
                logger.info(f"Saving {len(orchestrator_resource_data)} directly uploaded resources for session {session_model_instance.session_id}")
                for original_filename_key, text_content_val in orchestrator_resource_data.items(): # Iterate through dict
                    saved_path = save_extracted_text_to_server(
                        session_model_instance.session_id,
                        original_filename_key, # Use the key as original_filename
                        text_content_val
                    )
                    if saved_path:
                        saved_resource_paths_for_session.append(saved_path)
                    list_of_original_filenames_for_session.append(original_filename_key) # Capture original name
            
            # Now, update the ChatSession instance if there's anything to update
            if saved_resource_paths_for_session or list_of_original_filenames_for_session:
                # Fetch a fresh instance to ensure we have the latest version, especially after other async ops
                current_session_instance_to_update = await database_sync_to_async(ChatSession.objects.get)(session_id=session_model_instance.session_id)
                
                fields_to_save_in_db = ['updated_at'] # Always update timestamp

                if saved_resource_paths_for_session:
                    current_session_instance_to_update.resource_file_paths = saved_resource_paths_for_session
                    fields_to_save_in_db.append('resource_file_paths')
                
                if list_of_original_filenames_for_session:
                    current_session_instance_to_update.original_resource_filenames = list_of_original_filenames_for_session
                    fields_to_save_in_db.append('original_resource_filenames')
                
                if len(fields_to_save_in_db) > 1: # Check if more than just 'updated_at' needs saving
                    await database_sync_to_async(current_session_instance_to_update.save)(update_fields=list(set(fields_to_save_in_db)))
                    logger.info(f"Updated session {current_session_instance_to_update.session_id} with resource paths and/or original filenames. Fields: {fields_to_save_in_db}")
                # else: # If only updated_at, it might have been saved by update_session_state already, or save it explicitly if needed
                #    await database_sync_to_async(current_session_instance_to_update.save)(update_fields=['updated_at'])

        # --- 10. Save Generated Title IF Returned by Orchestrator ---
        generated_title_text_from_state = new_state_from_orchestrator.get(STATE_GENERATED_TITLE)
        if generated_title_text_from_state and isinstance(generated_title_text_from_state, str) and generated_title_text_from_state.strip():
            current_session_instance_for_title = await database_sync_to_async(ChatSession.objects.get)(session_id=session_model_instance.session_id)
            if current_session_instance_for_title.title != generated_title_text_from_state:
                current_session_instance_for_title.title = generated_title_text_from_state
                await database_sync_to_async(current_session_instance_for_title.save)(update_fields=['title', 'updated_at'])
                logger.info(f"Session title updated to: '{generated_title_text_from_state}'")
        # --- End 10. ---

        # --- 11. Prepare and Send JSON Response to Frontend ---
        response_payload = {
            "ai_reply": ai_reply_text,
            "new_state": { # Only send flags and stage, not full state
                STATE_STAGE: new_state_from_orchestrator.get(STATE_STAGE, session_model_instance.current_stage),
                STATE_DISPLAY_SYLLABUS_FLAG: new_state_from_orchestrator.get(STATE_DISPLAY_SYLLABUS_FLAG), # Can be None
                STATE_TRANSITION_EXPLAINER_FLAG: new_state_from_orchestrator.get(STATE_TRANSITION_EXPLAINER_FLAG, False),
            },
            "session_id": str(session_model_instance.session_id)
        }
        logger.info(f"Successfully processed message for session {session_model_instance.session_id}. Returning response.")
        return JsonResponse(response_payload, status=200)
        # --- End 11. ---

    except Exception as e:
        error_message_for_user = "[SYSTEM ERROR: An unexpected error occurred. Please try again or start a new chat.]"
        logger.error(f"Unexpected error in plain_django_chat_view for session {session_model_instance.session_id if session_model_instance else 'None'}: {e}", exc_info=True)
        
        error_stage_for_response = STAGE_ERROR
        session_id_for_error_response = str(session_model_instance.session_id) if session_model_instance else None
        
        if session_model_instance:
            try:
                session_model_instance.current_stage = STAGE_ERROR
                await database_sync_to_async(session_model_instance.save)(update_fields=['current_stage', 'updated_at'])
            except Exception as db_err:
                logger.critical(f"CRITICAL: Failed to update session stage to ERROR for {session_model_instance.session_id}: {db_err}", exc_info=True)
        
        return JsonResponse(
            {"ai_reply": error_message_for_user, "new_state": {STATE_STAGE: error_stage_for_response}, "session_id": session_id_for_error_response},
            status=500
        )

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
        response_data = { "session_id": str(session.session_id), "title": session.title, "current_stage": session.current_stage, "final_syllabus_xml": session.final_syllabus_xml, "explainer_system_prompt": session.explainer_system_prompt, "explanation_start_index": session.explanation_start_index, "history": history, "updated_at": session.updated_at.isoformat() if session.updated_at else None,"original_resource_filenames": session.original_resource_filenames}
        return JsonResponse(response_data)
    except ChatSession.DoesNotExist:
        # Return 404 directly if session not found
        return JsonResponse({'error': 'Session not found'}, status=404)
    except Exception as e:
        logger.error(f"Error fetching details for session {session_id}: {e}", exc_info=True)
        return JsonResponse({"error": "Failed to fetch session details"}, status=500)

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