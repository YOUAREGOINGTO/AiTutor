# test_dspy_llm.py
import asyncio
import sys
import os
import django
import logging
from typing import List, Dict, Any


print("Configuring Django settings...")
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tutor_project.settings')
try:
    django.setup()
    print("Django setup complete.")
except Exception as e:
    print(f"FATAL: Django setup error: {e}")
    logging.error("Django setup failed", exc_info=True)
    sys.exit(1)

logging.basicConfig(level=logging.INFO, format='{levelname} {asctime} [%(name)s:%(lineno)s] {message}', style='{')
logger = logging.getLogger(__name__)
logging.getLogger('api').setLevel(logging.DEBUG)
logging.getLogger('litellm').setLevel(logging.INFO)
print("Logging configured (api set to DEBUG).")


try:
    print("Importing DSPy components...")
    import dspy
    from django.conf import settings
    from api.async_rate_limiter import dspy_rate_limiter
    from api.dspy_llm import AsyncCustomGeminiDspyLM
    print("Imports successful.")
    if not settings.GEMINI_API_KEY:
        print("\nWARNING: GEMINI_API_KEY not found in Django settings.")
except ImportError as e:
    logger.error(f"FATAL: Import error: {e}", exc_info=True)
    sys.exit(1)
except AttributeError as e:
    logger.error(f"FATAL: AttributeError during import: {e}", exc_info=True)
    sys.exit(1)

async def run_lm_test():
    print("\n--- Testing AsyncCustomGeminiDspyLM (DSPy Prompt Focus) ---")
    if not settings.GEMINI_API_KEY:
        logger.error("GEMINI_API_KEY is not set. Cannot proceed.")
        return

    custom_lm = None
    try:
        test_model_name = getattr(settings, 'DEFAULT_GEMINI_MODEL', "gemini-2.5-flash-preview-04-17")
        if not test_model_name.startswith("gemini/"):
             test_model_name = f"gemini/{test_model_name}"
        logger.info(f"Initializing AsyncCustomGeminiDspyLM with model: '{test_model_name}'")
        custom_lm = AsyncCustomGeminiDspyLM(
            model=test_model_name,
            api_key=settings.GEMINI_API_KEY,
            rate_limiter_instance=dspy_rate_limiter,
            safety_settings=settings.DEFAULT_SAFETY_SETTINGS,
            temperature=0.7,
        )
        logger.info("AsyncCustomGeminiDspyLM initialized.")
    except Exception as e:
        logger.error(f"Error initializing AsyncCustomGeminiDspyLM: {e}", exc_info=True)
        return
    
    if custom_lm is None:
        logger.error("custom_lm was not initialized. Exiting test.")
        return

    # --- Test Case 1: Simple prompt (Async) ---
    print("\n--- Test Case 1: Simple Prompt (Async) ---")
    test_prompt_1 = "Hello, Gemini! In one concise sentence, what are you?"
    logger.info(f"Sending to custom_lm(prompt=...): \"{test_prompt_1}\"")
    try:
        responses_1 = await custom_lm(prompt=test_prompt_1) # Correctly awaiting
        logger.info(f"Received {len(responses_1)} response(s) for Test Case 1.")
        for i, response_text in enumerate(responses_1):
            print(f"Response {i+1} (Simple Prompt):\n---\n{response_text}\n---")
    except Exception as e:
        logger.error(f"Error during Test Case 1: {e}", exc_info=True)

    # --- Test Case 2: Simulating DSPy module passing history as part of a prompt string ---
    print("\n--- Test Case 2: Formatted History as Prompt String (Async) ---")
    history_for_formatting = [
        {"role": "user", "content": "What is the capital of Japan?"},
        {"role": "assistant", "content": "The capital of Japan is Tokyo."},
    ]
    # The final user query that the LLM should respond to
    final_user_query = "What is a famous traditional food there?"
    
    # Format the history and append the final query, as a DSPy module might do
    full_prompt_string = f"{history_for_formatting}\n---\nuser: {final_user_query}"
    
    # logger.info(f"Sending to custom_lm(prompt=...) (formatted history + query):\n{formatted_history_string}")
    try:
        responses_2 = await custom_lm(messages=full_prompt_string) # Correctly awaiting
        logger.info(f"Received {len(responses_2)} response(s) for Test Case 2.")
        print(responses_2)
        for i, response_text in enumerate(responses_2):
            print(f"Response {i+1} (Formatted History Prompt):\n---\n{response_text}\n---")
    except Exception as e:
        logger.error(f"Error during Test Case 2: {e}", exc_info=True)

    # --- Test Case 3 (Optional): Direct call with messages (if you want to keep testing this specific path) ---
    # This tests if LiteLLM's async Gemini adapter can handle List[Dict[role, content]] directly.
    # Based on previous errors, this specific path might still be problematic with Gemini via LiteLLM
    # if historical 'assistant' roles are present.
    print("\n--- Test Case 3: Direct Messages Call (Async) ---")
    direct_messages_test: List[Dict[str, str]] = [
        {"role": "user", "content": "What are the primary colors?"},
        {"role": "assistant", "content": "The primary colors of light are red, green, and blue."},
        {"role": "user", "content": "What happens if you mix red and green light?"}
    ]
    logger.info(f"Sending directly to custom_lm(messages=...): {direct_messages_test}")
    try:
        responses_3 = await custom_lm(messages=direct_messages_test) # Correctly awaiting
        print(responses_3)
        # logger.info(f"Received {len(responses_3)} response(s) for Test Case 3.")
        for i, response_text in enumerate(responses_3):
            print(f"Response {i+1} (Direct Messages):\n---\n{response_text}\n---")
    except Exception as e:
        logger.error(f"Error during Test Case 3 (Direct Messages): {type(e).__name__} - {e}", exc_info=False) # exc_info=False for brevity here as it's a known tricky case
        print(f"Response for Test Case 3 (Direct Messages):\n---\n[ERROR: {type(e).__name__} - {e}]\n---")


if __name__ == "__main__":
    print("Starting Async DSPy LLM test script (DSPy Prompt Focus)...")
    if 'dspy_rate_limiter' not in globals() or dspy_rate_limiter is None:
        logger.critical("FATAL: Global 'dspy_rate_limiter' not found.")
        sys.exit(1)
    try:
        asyncio.run(run_lm_test())
    except KeyboardInterrupt:
        print("\nTest script interrupted.")
    finally:
        print("\nAsync DSPy LLM Test Script (DSPy Prompt Focus) Finished.")