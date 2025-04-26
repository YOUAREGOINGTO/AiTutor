# api/ai_services.py
import google.generativeai as genai
from django.conf import settings
import logging
from typing import List, Dict, Optional, Any
import re
# --- Add necessary imports for rate limiting ---
import asyncio
from collections import deque
from datetime import datetime, timedelta, timezone
# --- End imports ---


# --- Configuration and Client Setup ---
logger = logging.getLogger(__name__) # Ensure logger uses 'api' name
gemini_configured = False
if settings.GEMINI_API_KEY:
    try:
        genai.configure(api_key=settings.GEMINI_API_KEY)
        gemini_configured = True
        logger.info("Google Generative AI configured successfully.")
    except Exception as e:
        logger.error(f"Error configuring Google Generative AI: {e}", exc_info=True)
else:
    logger.warning("GEMINI_API_KEY not found in settings. AI services will not function.")
# --- End Configuration ---


# --- Rate Limiting Setup ---
RATE_LIMIT_CALLS = 8                # Max calls allowed
RATE_LIMIT_PERIOD = timedelta(minutes=1) # Time window (1 minute)
# Use a deque for efficient timestamp storage and removal
llm_call_timestamps: deque[datetime] = deque() # Type hint for clarity
# Async lock to prevent race conditions when checking/updating timestamps
rate_limit_lock = asyncio.Lock()

# --- Rate Limit Error Message Constant ---
RATE_LIMIT_EXCEEDED_MESSAGE = "[RATE_LIMIT_EXCEEDED] Too many requests, please wait a minute."
# --- End Rate Limiting Setup ---


# --- Refactored Asynchronous LLM Call Function (with Rate Limiting) ---
async def async_llm_call(
    prompt: str,
    chat_history: Optional[List[Dict[str, Any]]] = None,
    system_prompt: Optional[str] = None,
    model_name: Optional[str] = None,
    temperature: float = 0.4, # Using the default from your previous version
    safety_settings: Optional[List[Dict]] = None
) -> str:
    """
    Asynchronously interacts with the Gemini API, incorporating rate limiting.
    Limits calls to RATE_LIMIT_CALLS per RATE_LIMIT_PERIOD.
    Returns the LLM response or a specific rate limit error message string.
    """
    if not gemini_configured:
        logger.error("Attempted to call LLM but Gemini API key is not configured.")
        return "[ERROR: Gemini API Key not configured]"

    # --- Rate Limiting Check ---
    async with rate_limit_lock: # Acquire lock to safely access shared state
        now = datetime.now(timezone.utc) # Use UTC for consistency

        # Remove timestamps older than the rate limit period from the left side
        while llm_call_timestamps and llm_call_timestamps[0] <= now - RATE_LIMIT_PERIOD:
            llm_call_timestamps.popleft()

        # Check if the number of recent calls meets or exceeds the limit
        if len(llm_call_timestamps) >= RATE_LIMIT_CALLS:
            logger.warning(
                f"Rate limit exceeded. Current calls in period ({RATE_LIMIT_PERIOD}): "
                f"{len(llm_call_timestamps)} >= {RATE_LIMIT_CALLS}"
            )
            # Return the specific error message string
            # Lock is automatically released when exiting 'async with' block
            return RATE_LIMIT_EXCEEDED_MESSAGE

        # If limit not exceeded, record the timestamp of this allowed call
        llm_call_timestamps.append(now)
        logger.debug(
            f"LLM call allowed. Current calls in period: {len(llm_call_timestamps)}/{RATE_LIMIT_CALLS}"
        )
    # --- End Rate Limiting Check (Lock Released) ---


    # --- Proceed with Original LLM Call Logic ---
    model_to_use = model_name if model_name else settings.DEFAULT_GEMINI_MODEL
    effective_safety_settings = safety_settings if safety_settings else settings.DEFAULT_SAFETY_SETTINGS
    effective_system_prompt = system_prompt # Keep None if not provided

    logger.debug(f"Making async LLM call. Model: {model_to_use}, Temp: {temperature}")

    try:
        model_instance = genai.GenerativeModel(
            model_name=model_to_use,
            system_instruction=effective_system_prompt,
            safety_settings=effective_safety_settings
        )
        generation_config = genai.types.GenerationConfig(
            temperature=temperature
        )

        # Prepare input history and prompt
        full_chat_content = []
        if chat_history:
            if isinstance(chat_history, list) and all(isinstance(item, dict) and 'role' in item and 'parts' in item for item in chat_history):
                full_chat_content.extend(chat_history)
            else:
                 logger.warning("Invalid chat_history format provided to async_llm_call.")
        # Ensure prompt is correctly formatted in parts
        if isinstance(prompt, str):
            full_chat_content.append({"role": "user", "parts": [{'text': prompt}]})
        else:
             logger.error(f"Invalid prompt type received: {type(prompt)}")
             return "[ERROR: Invalid prompt type]"

        generation_input = full_chat_content

        # --- THE ASYNC CALL to Gemini ---
        response = await model_instance.generate_content_async(
            generation_input,
            generation_config=generation_config
        )
        # --------------------------------

        # --- Response Handling (Keep robust checks) ---
        response_text = ""
        block_reason = None
        finish_reason = None

        if hasattr(response, 'prompt_feedback') and response.prompt_feedback.block_reason:
            block_reason = response.prompt_feedback.block_reason.name
            logger.warning(f"LLM call blocked by API (prompt). Reason: {block_reason}")
            return f"[BLOCKED DUE TO PROMPT: {block_reason}]"

        if hasattr(response, 'candidates') and response.candidates:
            candidate = response.candidates[0]
            if hasattr(candidate, 'finish_reason'):
                finish_reason = candidate.finish_reason.name
            if finish_reason not in ['STOP', 'UNSPECIFIED', None]:
                logger.warning(f"LLM generation potentially stopped prematurely. Reason: {finish_reason}")

            if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts') and candidate.content.parts:
                response_text = "".join(part.text for part in candidate.content.parts if hasattr(part, 'text'))

        if not response_text and hasattr(response, 'text'):
            response_text = response.text # Fallback

        if response_text:
            logger.debug("LLM call successful, returning text.")
            return response_text
        elif finish_reason == 'STOP':
             logger.warning("LLM call finished with STOP reason but no text content extracted.")
             return "[EMPTY RESPONSE - STOP]"
        else:
            logger.warning(f"LLM call returned no text content. Finish Reason: {finish_reason}, Block Reason: {block_reason}")
            return f"[EMPTY RESPONSE - Finish: {finish_reason}, Block: {block_reason}]"
        # --- End Response Handling ---

    except Exception as e:
        # Catch potential API errors or other issues
        logger.error(f"Error during async Gemini API call: {e}", exc_info=True)
        # You could check for specific API error types here if the library raises them
        # e.g., if isinstance(e, google.api_core.exceptions.ResourceExhausted): return RATE_LIMIT_EXCEEDED_MESSAGE
        return f"[ERROR: {type(e).__name__} - {e}]"

# --- XML Extraction Function (Keep as is) ---
def extract_xml(text: str, tag: str) -> str:
    """
    Extracts the content of the specified XML tag from the given text.
    Made case-insensitive and strips whitespace. Returns empty string if not found.
    """
    if not text or not tag:
        return ""
    match = re.search(f'<{tag}>(.*?)</{tag}>', text, re.DOTALL | re.IGNORECASE)
    return match.group(1).strip() if match else ""

# --- Test Call Function (Keep as is for testing rate limiter) ---
async def test_call():
    print(f"Testing rate limiter ({RATE_LIMIT_CALLS} calls / {RATE_LIMIT_PERIOD})...")
    tasks = []
    for i in range(RATE_LIMIT_CALLS + 5): # Try to exceed the limit
        # Create tasks to run concurrently
        task = asyncio.create_task(
            async_llm_call(f"Short explanation request #{i+1}.")
        )
        tasks.append(task)
        # Optional small delay between starting tasks if needed for testing setup
        # await asyncio.sleep(0.05)

    # Wait for all tasks to complete and print results
    results = await asyncio.gather(*tasks)
    for i, result in enumerate(results):
        print(f"Result {i+1}: {result[:100]}{'...' if len(result)>100 else ''}")
    print("Test calls finished.")


# To test in shell:
# python manage.py shell
# >>> from api.ai_services import test_call
# >>> import asyncio
# >>> asyncio.run(test_call())