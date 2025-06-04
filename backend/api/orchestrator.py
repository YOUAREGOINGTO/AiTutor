# api/orchestrator.py
import logging
import json 
from typing import List, Dict, Any, Tuple, Optional
from .dspy_heavyprompts import FormatSyllabusXMLToMarkdown 
# FormatSyllabusXMLToMarkdown has a Long Prompt to make sure that the rendering Happens Properly

# DSPy specific imports
import dspy
from .ai_services import get_dspy_lm, extract_xml 
from .dspy_modules import (
    ConversationManager,
    SyllabusGeneratorRouter,
    InitialResourceSummarizer,
    DynamicResourceSummarizerModule,
    LearningStyleQuestioner,
    PersonaPromptGenerator,
    ExplainerModule
)
from .dspy_signatures import GenericInteractionSignature,SyllabusFeedbackRequestSignature  

# Resource processing (if files are uploaded)
from .resource_processor import process_uploaded_files # We'll use this later in views.py

logger = logging.getLogger(__name__)
initial_summary_info = """
This Resource Summary is visible only to You (the agent/system) and not to the end-user.
It is provided for Your reference after the user has uploaded a resource.
This information is primarily for understanding the context of the user's resource.
For the syllabus, you should provide either the raw data or a dynamic summary.\n"""

# --- State Keys  ---
STATE_STAGE = "stage"
STATE_HISTORY = "conversation_history"
STATE_FINAL_SYLLABUS = "final_syllabus_xml" # XML string
STATE_EXPLAINER_PROMPT = "explainer_system_prompt" # Full system prompt for explainer
STATE_EXPLANATION_START_INDEX = "explanation_start_index"
STATE_CURRENT_TITLE = "current_title"
STATE_GENERATED_TITLE = "generated_title"

# New state keys for resource processing results (transient within orchestrator run)
STATE_RESOURCE_SUMMARY_OVERVIEW = "resource_summary_overview_for_manager" # Brief text for ConvoManager
STATE_RESOURCE_TYPE_FOR_SYLLABUS = "resource_type_for_syllabus_gen" # "NONE", "RAW_TEXT", "SUMMARIES"
STATE_RESOURCE_CONTENT_JSON_FOR_SYLLABUS = "resource_content_json_for_syllabus_gen" # JSON string

# Flags returned to UI (transient, cleared each turn)
STATE_DISPLAY_SYLLABUS_FLAG = "display_syllabus_flag" # To tell UI to render a new/updated syllabus
STATE_TRANSITION_EXPLAINER_FLAG = "transition_to_explainer_flag"
# --- Stages ---
STAGE_START = "START"
STAGE_NEGOTIATING = "NEGOTIATING"
STAGE_EXPLAINING = "EXPLAINING"
STAGE_ERROR = "ERROR"

# --- Constants ---
DEFAULT_CHAT_TITLE = "New Chat"
TITLE_GENERATION_THRESHOLD = 4 # Generate title after fewer messages
TITLE_MAX_HISTORY_SNIPPET_FOR_TITLE = 6 # How many messages from history to use for title



# --- Orchestrator Modules (Instantiated once) ---
# These will be initialized when the orchestrator module is loaded.
# Ensure ai_services.configure_dspy_lm() has run before these are used.
SYLLABUS_XML_TO_MARKDOWN_FORMATTER = None

try:
    if get_dspy_lm(): # Check if LM is configured
        SYLLABUS_XML_TO_MARKDOWN_FORMATTER = dspy.Predict(
        FormatSyllabusXMLToMarkdown, 
        temperature=0.5, 
    )

        CONVO_MANAGER = ConversationManager()
        SYLLABUS_ROUTER = SyllabusGeneratorRouter()
        INITIAL_RESOURCE_SUMMARIZER = InitialResourceSummarizer()
        DYNAMIC_SUMMARIZER_MODULE = DynamicResourceSummarizerModule()
        LEARNING_STYLE_QUESTIONER = LearningStyleQuestioner()
        PERSONA_PROMPT_GENERATOR = PersonaPromptGenerator()
        EXPLAINER_MODULE = ExplainerModule()
        SYLLABUS_FEEDBACK_REQUESTER = dspy.Predict(SyllabusFeedbackRequestSignature, temperature=0.7)

        # For title generation, we use dspy.Predict directly with a simple signature
        class TitleGenerationSignature(dspy.Signature):
            """Generate a concise title (3-6 words, max 17 words) for a chat session based on the learning topic in the history. Output ONLY the title text."""
            chat_history_summary = dspy.InputField(desc="A summary or key excerpts of the chat history.")
            chat_title = dspy.OutputField(desc="The generated concise title.")
        TITLE_GENERATOR_PREDICTOR = dspy.Predict(TitleGenerationSignature, temperature=0.4) 

        logger.info("DSPy modules for orchestrator initialized successfully.")
    else:
        raise RuntimeError("DSPy LM not configured in ai_services. Orchestrator modules cannot be initialized.")
except Exception as e:
    logger.critical(f"Failed to initialize DSPy modules for orchestrator: {e}", exc_info=True)
    # Set them to None so checks later will prevent their use
    CONVO_MANAGER, SYLLABUS_ROUTER, INITIAL_RESOURCE_SUMMARIZER, DYNAMIC_SUMMARIZER_MODULE, \
    LEARNING_STYLE_QUESTIONER, PERSONA_PROMPT_GENERATOR, EXPLAINER_MODULE, TITLE_GENERATOR_PREDICTOR,SYLLABUS_FEEDBACK_REQUESTER = \
    (None,) * 9

def format_history_for_dspy(history_list: List[Dict[str, Any]]) -> str:
    formatted_history = []
    for turn in history_list:
        content = ""
        if isinstance(turn.get('parts'), list) and turn['parts']:
            content = turn['parts'][0]['text']
        elif isinstance(turn.get('parts'), str):
            content = turn['parts']

        role = turn.get('role', 'unknown')
        if role == 'model':
            role = 'assistant'  # Replace 'model' with 'assistant'

        formatted_history.append(f"{role}: {content}")
    return "\n---\n".join(formatted_history)

# The role part for model has been replaced with assistant for compatibility with litellm.

def get_last_syllabus_content_from_history(history: List[Dict[str, Any]]) -> Optional[str]:

    logger.debug("Helper: Searching history backwards for last syllabus-typed message...")
    if not history:
        logger.warning("Helper: History is empty, cannot find syllabus.")
        return None

    for i in range(len(history) - 1, -1, -1):
        message = history[i]
        msg_role = message.get('role')
        msg_type = message.get('message_type') # Get the message_type

        logger.debug(f"Helper: Checking history index {i}, Role: '{msg_role}', Type: '{msg_type}'")

        # We are looking for messages from 'model' or 'system' that are explicitly typed
        # as either 'syllabus' (for old XML format) or 'syllabus_markdown' (for new Markdown format).
        if msg_role in ['model', 'system'] and msg_type in ['syllabus', 'syllabus_markdown']:
            content = ""
            parts_list = message.get('parts', [])

            if isinstance(parts_list, list) and len(parts_list) > 0:
                first_part = parts_list[0]
                if isinstance(first_part, dict):
                    content = first_part.get('text', '')
                elif isinstance(first_part, str):
                    content = first_part
            elif isinstance(parts_list, str): # Handle if 'parts' itself was saved as a string
                content = parts_list
            elif 'content' in message: # Fallback if structure is simpler like {'role': ..., 'content': ...}
                logger.debug("Helper: 'parts' key not found or empty, trying 'content' key directly.")
                if isinstance(message.get('content'), str):
                    content = message.get('content', '')


            if content:
                logger.info(f"Helper: FOUND syllabus content via message_type '{msg_type}' at index {i}. Content starts: '{content[:70]}...'")
                return content.strip() # Return the full content of this message
            else:
                logger.warning(f"Helper: Found syllabus-typed message at index {i} but content was empty.")
                # Continue searching

    logger.warning("Helper: Finished searching history, did not find a valid syllabus-typed message with content.")
    return None




# --- Main Orchestration Logic ---
async def process_chat_message(
    user_message_text: str, 
    current_session_state: Dict[str, Any],
    uploaded_resource_data: Optional[Dict[str, str]] = None # Filename -> text content
) -> Tuple[str, Dict[str, Any]]:
    """
    Processes user message using DSPy modules.
    Handles initial resource processing if `uploaded_resource_data` is provided.
    """
    if not CONVO_MANAGER: 
        logger.error("Orchestrator's DSPy modules are not initialized. Cannot process message.")
        # Return an error state immediately
        error_state = current_session_state.copy()
        error_state[STATE_STAGE] = STAGE_ERROR
        error_state[STATE_HISTORY].append({'role': 'user', 'parts': [{'text': user_message_text}]})
        error_state[STATE_HISTORY].append({'role': 'model', 'parts': [{'text': "[FATAL ERROR: AI modules not initialized. Please contact support.]"}]})
        return "[FATAL ERROR: AI modules not initialized]", error_state
    
    
    new_state = current_session_state.copy()
    new_state.pop(STATE_DISPLAY_SYLLABUS_FLAG, None)
    new_state.pop(STATE_TRANSITION_EXPLAINER_FLAG, None)
    new_state.pop(STATE_GENERATED_TITLE, None)


  
    stage = new_state.get(STATE_STAGE, STAGE_START)
    history: List[Dict[str, Any]] = new_state.get(STATE_HISTORY, []) # History from view already includes latest user msg
    current_title = new_state.get(STATE_CURRENT_TITLE, DEFAULT_CHAT_TITLE)
    
    ai_reply_for_user = ""
    
    logger.debug(f"Orchestrator (DSPy) received: Stage='{stage}', Title='{current_title}', History len={len(history)}")
    if uploaded_resource_data:
        logger.info(f"Processing {len(uploaded_resource_data)} uploaded resources.")

    try:
        # --- Initial Resource Processing (only if resources are provided AND it's the start of negotiation) ---
        #Resources can Be only Uploaded at the start.
        if stage == STAGE_START and uploaded_resource_data:
            logger.info("First turn with resources. Processing them now...")
            
            total_chars = sum(len(text) for text in uploaded_resource_data.values())
            
            resource_summary_for_manager = "Resources were provided by the user." # Default
            resource_type_for_syllabus = "NONE"
            resource_content_json = "{}"
            #Syllabus Segregation

            if not uploaded_resource_data:
                resource_summary_for_manager = "No resources were processed or user did not provide any."
                resource_type_for_syllabus = "NONE"
            elif total_chars > 70000: # Heuristic from your notebook for "heavy" resources
                logger.info(f"Total resource chars ({total_chars}) > 70k. Using DYNAMIC SUMMARIES for syllabus gen.")
                resource_type_for_syllabus = "SUMMARIES"
                # For manager, provide an overview from InitialResourceSummarizer
                # Truncate content for initial summary if very large before sending to InitialResourceSummarizer
                initial_summary_input_dict = {
                    fname: content[:40000] for fname, content in uploaded_resource_data.items()
                }
                resource_summary_for_manager = await INITIAL_RESOURCE_SUMMARIZER.forward(initial_summary_input_dict)

                new_state['raw_resource_data_for_dynamic_summary'] = uploaded_resource_data # Store full data
            else:
                logger.info(f"Total resource chars ({total_chars}) <= 70k. Using RAW TEXT for syllabus gen.")
                resource_type_for_syllabus = "RAW_TEXT"
                initial_summary_input_dict = {
                    fname: content[:40000] for fname, content in uploaded_resource_data.items()
                }
                resource_summary_for_manager = await INITIAL_RESOURCE_SUMMARIZER.forward(initial_summary_input_dict)
                resource_content_json = json.dumps(uploaded_resource_data, indent=2)
            new_state[STATE_RESOURCE_SUMMARY_OVERVIEW] = resource_summary_for_manager
            new_state[STATE_RESOURCE_TYPE_FOR_SYLLABUS] = resource_type_for_syllabus
            new_state[STATE_RESOURCE_CONTENT_JSON_FOR_SYLLABUS] = resource_content_json
            new_state['raw_resource_data_for_dynamic_summary'] = uploaded_resource_data # Alreday done upside
            
            
            # This should be done if Only History length is less than 2.
            if resource_summary_for_manager and resource_summary_for_manager != "No resources were processed or user did not provide any." and len(history)<=2:
                
                history.append({'role': 'model', 'parts': [{"text" : str(initial_summary_info) + str(resource_summary_for_manager)}],'message_type': 'internal_resource_summary'})
                


        # --- Negotiation Phase (STAGE_START, STAGE_NEGOTIATING) ---
        if stage in [STAGE_START, STAGE_NEGOTIATING]:
            if stage == STAGE_START:
                new_state[STATE_STAGE] = STAGE_NEGOTIATING
                stage = STAGE_NEGOTIATING # Update local stage variable

            logger.info(f"Orchestrator (DSPy): Stage={stage}. Calling ConversationManager.")
            
            history_str = format_history_for_dspy(history)
            current_syllabus_xml_str = new_state.get(STATE_FINAL_SYLLABUS) or \
                                       get_last_syllabus_content_from_history(history) or \
                                       "None" # Try to get latest syllabus for manager

            # Get resource overview from state if set, otherwise "None"
            resource_overview_for_manager = new_state.get(STATE_RESOURCE_SUMMARY_OVERVIEW, "No resources were processed or provided by the user for this session.")

            action_code, display_text = await CONVO_MANAGER.forward(
                conversation_history_str=history_str,
                current_syllabus_xml=current_syllabus_xml_str,
                user_input=user_message_text, # Manager needs the latest user message explicitly

            )
            logger.info(f"ConversationManager action: '{action_code}', display_text: '{display_text[:100]}...'")
            
            ai_reply_for_user = display_text # This will be empty if action is not CONVERSE
            if display_text:
                history.append({'role': 'model', 'parts': [{'text': display_text}]})
            
            

            # --- Handle Actions from ConversationManager ---
            if action_code in ["GENERATE", "MODIFY"]:
                task_type_str = "generation" if action_code == "GENERATE" else "modification"
                logger.info(f"Syllabus {task_type_str} requested. Resource type: {new_state.get(STATE_RESOURCE_TYPE_FOR_SYLLABUS)}")
                retrieved_resource_type = new_state.get(STATE_RESOURCE_TYPE_FOR_SYLLABUS, "NONE")
                retrieved_resource_content_json = new_state.get(STATE_RESOURCE_CONTENT_JSON_FOR_SYLLABUS, "{}")
                _temp_resource_type = new_state.get(STATE_RESOURCE_TYPE_FOR_SYLLABUS) # Get value, could be Python None
                if _temp_resource_type is None: 
                    retrieved_resource_type = "NONE"
                else:
                    retrieved_resource_type = _temp_resource_type
                logger.info(f"Syllabus {task_type_str} requested. Resource type from state: {retrieved_resource_type}")
                # If type is SUMMARIES, we need to generate them now using DynamicSummarizer
                if retrieved_resource_type  == "SUMMARIES":
                    raw_data_for_dynamic_summary = new_state.get('raw_resource_data_for_dynamic_summary')
                    if raw_data_for_dynamic_summary and isinstance(raw_data_for_dynamic_summary, dict):
                        logger.info("Generating dynamic summaries for syllabus router...")
                        summaries_for_syllabus = {}
                        history_str_for_summarizer = format_history_for_dspy(history) # Fresh history string
                        for res_id, res_content in raw_data_for_dynamic_summary.items():
                            summary_dict = await DYNAMIC_SUMMARIZER_MODULE.forward(
                                resource_content=res_content,
                                resource_identifier=res_id,
                                conversation_history_str=history_str_for_summarizer
                            )
                            if summary_dict:
                                summaries_for_syllabus[res_id] = summary_dict
                        current_resource_content_json = json.dumps(summaries_for_syllabus, indent=2)
                        logger.info(f"Dynamic summaries generated. JSON length: {len(current_resource_content_json)}")
                
                    else:
                        logger.warning("SUMMARIES type selected but no 'raw_resource_data_for_dynamic_summary' found. Falling back to NONE.")
                        current_resource_type = "NONE"
                        current_resource_content_json = "{}"
                if retrieved_resource_type == "RAW_TEXT":
                    current_resource_content_json = retrieved_resource_content_json

                

                generated_xml = await SYLLABUS_ROUTER.forward(
                                    conversation_history_str=format_history_for_dspy(history),
                                    resource_type=retrieved_resource_type,
                                    resource_content=current_resource_content_json if retrieved_resource_type != "NONE" else None
                                )
                
                final_syllabus_content_for_frontend = generated_xml 
                message_content_type_for_syllabus_display = 'syllabus_markdown' 
                syllabus_generation_was_successful = False # Initialize flag

                # --- BLOCK 1: XML to Markdown Formatting (and set success flag) ---
                if generated_xml and not generated_xml.strip().upper().startswith(("<SYLLABUS>\n[ERROR", "<SYLLABUS>[ERROR")):
                    syllabus_generation_was_successful = True # Mark initial generation as successful
                    logger.info(f"Syllabus XML generated. Length: {len(generated_xml)}. Attempting Markdown formatting.")
                    
                    if SYLLABUS_XML_TO_MARKDOWN_FORMATTER:
                        try:
                            format_prediction = await SYLLABUS_XML_TO_MARKDOWN_FORMATTER.acall(
                                syllabus_xml_input=generated_xml
                            )
                            formatted_markdown = format_prediction.cleaned_syllabus_markdown.strip()
                            
                            if formatted_markdown and not formatted_markdown.lower().startswith(("[error", "[warn")):
                                final_syllabus_content_for_frontend = formatted_markdown
                                # message_content_type_for_syllabus_display = 'syllabus'
                                logger.info("Syllabus successfully formatted to Markdown.")
                            else:
                                logger.warning(f"Syllabus Markdown formatting returned empty/error: {formatted_markdown[:100]}. Using raw XML (from router).")

                        except Exception as fmt_e:
                            logger.error(f"Error during syllabus XML to Markdown formatting: {fmt_e}", exc_info=True)
                    else:
                        logger.warning("SYLLABUS_XML_TO_MARKDOWN_FORMATTER not available. Using raw XML (from router).")

                else:
                   
                    syllabus_generation_was_successful = False # Explicitly false
                    logger.error(f"Syllabus XML generation by SYLLABUS_ROUTER failed or returned error: {generated_xml[:200]}")
                    
                # --- BLOCK 2: Add syllabus to history and state ---
                # This message is the syllabus display itself (or the error from the router if generation failed)
                history.append({
                    'role': 'model', 
                    'parts': [{'text': final_syllabus_content_for_frontend}],
                    'message_type': message_content_type_for_syllabus_display 
                })
                print(history[-1])
                new_state[STATE_DISPLAY_SYLLABUS_FLAG] = { 
                    "content": final_syllabus_content_for_frontend,
                    "type": message_content_type_for_syllabus_display
                }

                # --- NEW BLOCK 3: Generate Conversational Reply (Feedback or Error) ---
                if syllabus_generation_was_successful:
                    # The syllabus (Markdown or XML) is already in history. Now add the feedback prompt.
                    logger.info(f"Syllabus processed for display (type: {message_content_type_for_syllabus_display}). Requesting user feedback.")
                    if SYLLABUS_FEEDBACK_REQUESTER:
                        try:

                            history_for_feedback_str = format_history_for_dspy(history) 
                            feedback_prediction = await SYLLABUS_FEEDBACK_REQUESTER.acall(
                                conversation_history_with_syllabus=history_for_feedback_str
                            )
                            ai_reply_for_user = feedback_prediction.feedback_query_to_user.strip()
                            if not ai_reply_for_user:
                                logger.warning("SYLLABUS_FEEDBACK_REQUESTER returned empty, using fallback.")
                                ai_reply_for_user = "I've drafted the syllabus. What are your thoughts?"
                        except Exception as fb_err:
                            logger.error(f"Error calling SYLLABUS_FEEDBACK_REQUESTER: {fb_err}", exc_info=True)
                            ai_reply_for_user = "Here is the syllabus draft. How does it look?"
                    else:
                        logger.error("SYLLABUS_FEEDBACK_REQUESTER not initialized. Using hardcoded feedback prompt.")
                        ai_reply_for_user = "I've prepared the syllabus. Please review it."
                    
                    # Add the feedback prompt as the next message in history
                    history.append({'role': 'model', 'parts': [{'text': ai_reply_for_user}]})
                    
                else: 

                    ai_reply_for_user = final_syllabus_content_for_frontend
                    logger.info(f"Syllabus generation failed. AI reply set to the error from router: {ai_reply_for_user[:100]}")

            
            elif action_code == "FINALIZE":
                logger.info("Finalization requested by manager.")
                last_syllabus_in_history = get_last_syllabus_content_from_history(history)
                if last_syllabus_in_history:
                    new_state[STATE_FINAL_SYLLABUS] = f"<syllabus>\n{last_syllabus_in_history}\n</syllabus>" # Store it
                    
                    # Ask for learning style
                    style_question = await LEARNING_STYLE_QUESTIONER.forward(
                        conversation_history_str=format_history_for_dspy(history)
                    )
                    ai_reply_for_user = style_question
                    history.append({'role': 'model', 'parts': [{'text': style_question}]})
                else:
                    logger.warning("FINALIZE action but no syllabus found in history.")
                    ai_reply_for_user = "It seems we don't have a syllabus to finalize yet. Could we create one first?"
                    history.append({'role': 'model', 'parts': [{'text': ai_reply_for_user}]})

            elif action_code == "PERSONA":
                logger.info("Persona generation triggered by manager.")
                final_syllabus_xml_str = new_state.get(STATE_FINAL_SYLLABUS)
                if final_syllabus_xml_str:
                    logger.info("Generating explainer prompt body...")
                    explainer_prompt_body = await PERSONA_PROMPT_GENERATOR.forward(
                        conversation_history_str=format_history_for_dspy(history)
                    )
                    if explainer_prompt_body:
                        full_explainer_prompt = f"{explainer_prompt_body}\n\nHere is the syllabus we will follow:\n{final_syllabus_xml_str}"
                        new_state[STATE_EXPLAINER_PROMPT] = full_explainer_prompt
                        new_state[STATE_STAGE] = STAGE_EXPLAINING # << TRANSITION STAGE
                        new_state[STATE_TRANSITION_EXPLAINER_FLAG] = True
                        new_state[STATE_EXPLANATION_START_INDEX] = len(history) # Record index before explainer intro

                        logger.info("Explainer prompt generated. Moving to EXPLAINING stage.")
                        

                        explainer_intro_query = "Based on your persona (defined in system_instructions) and the syllabus provided, please introduce yourself to the user. Briefly state what you'll be helping them with and adopt a welcoming tone consistent with your persona."
                        explainer_intro_response = await EXPLAINER_MODULE.forward(
                            system_instructions_str=full_explainer_prompt,
                            history_str="None", # No prior *explainer* history for this first turn
                            user_query_str=explainer_intro_query
                        )
                        ai_reply_for_user = explainer_intro_response
                        history.append({'role': 'model', 'parts': [{'text': ai_reply_for_user}]})
                    else:
                        logger.error("Failed to generate explainer prompt body.")
                        ai_reply_for_user = "Sorry, I had trouble setting up the learning session. Please try again."
                        history.append({'role': 'model', 'parts': [{'text': ai_reply_for_user}]})
                        new_state[STATE_STAGE] = STAGE_ERROR
                else:
                    logger.warning("PERSONA action but no finalized syllabus in state.")
                    ai_reply_for_user = "We need to finalize a syllabus before we can tailor the tutor. Shall we continue with that?"
                    history.append({'role': 'model', 'parts': [{'text': ai_reply_for_user}]})
            
            elif action_code == "CONVERSE":
                # ai_reply_for_user is already set from manager's display_text
                if not ai_reply_for_user: # Should not happen if manager follows rules
                    logger.warning("CONVERSE action but manager provided no display_text. Using fallback.")
                    ai_reply_for_user = "Okay, how would you like to proceed?"
                    history.append({'role': 'model', 'parts': [{'text': ai_reply_for_user}]})
            
            else: 
                logger.error(f"Unknown action_code '{action_code}' from ConversationManager.")
                ai_reply_for_user = "I'm not sure how to proceed with that. Could you clarify?"
                history.append({'role': 'model', 'parts': [{'text': ai_reply_for_user}]})

        # --- Explanation Phase (STAGE_EXPLAINING) ---
        elif stage == STAGE_EXPLAINING:
            logger.info(f"Orchestrator (DSPy): Stage={stage}. Calling ExplainerModule.")
            explainer_sys_prompt = new_state.get(STATE_EXPLAINER_PROMPT)
            expl_start_idx = new_state.get(STATE_EXPLANATION_START_INDEX, 0)

            if not explainer_sys_prompt:
                logger.error("Explainer stage but no explainer_system_prompt in state.")
                ai_reply_for_user = "[SYSTEM ERROR: Explainer setup incomplete. Cannot proceed.]"
                history.append({'role': 'model', 'parts': [{'text': ai_reply_for_user}]})
                new_state[STATE_STAGE] = STAGE_ERROR
            else:
                # For explainer, only pass relevant part of history (after persona setup)
                explainer_relevant_history_str = format_history_for_dspy(history[expl_start_idx:])
                
                explainer_response = await EXPLAINER_MODULE.forward(
                    system_instructions_str=explainer_sys_prompt,
                    history_str=explainer_relevant_history_str,
                    user_query_str=user_message_text
                )
                ai_reply_for_user = explainer_response
                history.append({'role': 'model', 'parts': [{'text': explainer_response}]})
        
        # --- Error Stage ---
        elif stage == STAGE_ERROR:
            logger.warning("Orchestrator is in ERROR stage.")
            ai_reply_for_user = "I'm sorry, an internal error occurred. Please try starting a new conversation or contact support."
            # To prevent loops, don't add this generic error to history if user just messaged. Let user try again.

        # --- Unknown Stage ---
        else:
            logger.error(f"Orchestrator encountered an unknown stage: {stage}")
            ai_reply_for_user = "[SYSTEM ERROR: Invalid application state. Please start over.]"
            history.append({'role': 'model', 'parts': [{'text': ai_reply_for_user}]})
            new_state[STATE_STAGE] = STAGE_ERROR

        # --- Title Generation Logic (Simplified to use DSPy Predict) ---
        final_message_count = len(history)
        if current_title == DEFAULT_CHAT_TITLE and final_message_count >= TITLE_GENERATION_THRESHOLD:
            logger.info("Conditions met for title generation.")
            # Prepare a snippet of history for the title generator
            history_for_title_str = format_history_for_dspy(history[:TITLE_MAX_HISTORY_SNIPPET_FOR_TITLE])
            if TITLE_GENERATOR_PREDICTOR:
                try:
                    title_prediction =  await TITLE_GENERATOR_PREDICTOR.acall(chat_history_summary=history_for_title_str) # await predict
                    generated_title_text = title_prediction.chat_title.strip().strip('"\'')
                    if generated_title_text and not generated_title_text.lower().startswith(("[error", "[warn", "[empty")):
                        new_state[STATE_GENERATED_TITLE] = generated_title_text[:150] # Max length
                        logger.info(f"Generated title: '{new_state[STATE_GENERATED_TITLE]}'")
                    else:
                        logger.warning(f"Title generator returned empty or error-like: {generated_title_text}")
                except Exception as title_e:
                    logger.error(f"Error during title generation predictor call: {title_e}", exc_info=True)
            else:
                logger.error("TITLE_GENERATOR_PREDICTOR not initialized.")


    except Exception as e:
        logger.error(f"Orchestrator (DSPy): Unhandled exception: {e}", exc_info=True)
        ai_reply_for_user = "[SYSTEM ERROR: An unexpected issue occurred. Please try again.]"
        new_state[STATE_STAGE] = STAGE_ERROR
        # Ensure error is logged to history if not already the last message
        if not history or not (history[-1]['role'] == 'model' and history[-1]['parts'][0]['text'] == ai_reply_for_user):
            history.append({'role': 'model', 'parts': [{'text': ai_reply_for_user}]})
    
    # --- Final State Update & Return ---
    new_state[STATE_HISTORY] = history
    logger.debug(f"Orchestrator (DSPy) returning: Stage='{new_state.get(STATE_STAGE)}', History Len={len(history)}, AI Reply starts: '{ai_reply_for_user[:50]}...'")
    logger.debug(f"Flags: DisplaySyllabus='{new_state.get(STATE_DISPLAY_SYLLABUS_FLAG) is not None}', TransitionExplainer='{new_state.get(STATE_TRANSITION_EXPLAINER_FLAG)}'")
    
    return ai_reply_for_user, new_state


