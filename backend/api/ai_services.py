# api/ai_services.py
import dspy
import litellm # Keep for the custom LM
import logging
from django.conf import settings
import re
from typing import Optional, List, Dict, Any, Union,Tuple,Callable
# New imports for DSPy setup
from .async_rate_limiter import AsyncRateLimiter, RATE_LIMIT_CALLS_DSPY, RATE_LIMIT_PERIOD_DSPY # Use constants from there
from .dspy_llm import AsyncCustomGeminiDspyLM

logger = logging.getLogger(__name__)

# --- Global DSPy LM instance ---
# This will be configured once when the module loads.
__configured_dspy_lm = None
gemini_configured_for_dspy = False

# --- Initialize Rate Limiter ---
# You can adjust parameters here or load from settings if needed
# Using the constants defined in async_rate_limiter.py for consistency
dspy_global_rate_limiter = AsyncRateLimiter(
    max_calls=RATE_LIMIT_CALLS_DSPY, 
    period_seconds=int(RATE_LIMIT_PERIOD_DSPY.total_seconds())
)
logger.info("DSPy global rate limiter initialized in ai_services.")

# --- Configure DSPy ---
def configure_dspy_lm():
    global __configured_dspy_lm, gemini_configured_for_dspy
    
    if gemini_configured_for_dspy:
        logger.info("DSPy LM already configured.")
        return

    if not settings.GEMINI_API_KEY:
        logger.error("CRITICAL: GEMINI_API_KEY not found in settings. DSPy LM cannot be configured for Gemini.")
        # Optionally, configure a fallback dummy LM for testing without API key
        # dspy.settings.configure(lm=dspy.utils.DummyLM("DSPy is in dummy mode. GEMINI_API_KEY missing."))
        # logger.warning("DSPy configured with DummyLM as GEMINI_API_KEY is missing.")
        # gemini_configured_for_dspy = False # Explicitly false
        return

    try:
        # Construct the LiteLLM model string (e.g., "gemini/gemini-1.5-flash-latest")
        # Ensure DEFAULT_GEMINI_MODEL in settings is just the model name like "gemini-1.5-flash-latest"
        # or "gemini-pro", not the full "gemini/..." string.
        model_name_for_litellm = settings.DEFAULT_GEMINI_MODEL
        if not model_name_for_litellm.startswith("gemini/"):
            litellm_model_string = f"gemini/{model_name_for_litellm}"
        else: # If it already has the prefix (less ideal for settings.DEFAULT_GEMINI_MODEL)
            litellm_model_string = model_name_for_litellm
            logger.warning(f"settings.DEFAULT_GEMINI_MODEL ('{model_name_for_litellm}') includes 'gemini/' prefix. Consider using just the model name.")

        logger.info(f"Attempting to configure DSPy with AsyncCustomGeminiDspyLM for model: {litellm_model_string}")

        custom_lm = AsyncCustomGeminiDspyLM(
            model=litellm_model_string,
            api_key=settings.GEMINI_API_KEY, # Passed explicitly, though LiteLLM can use env vars
            rate_limiter_instance=dspy_global_rate_limiter,
            safety_settings=settings.DEFAULT_SAFETY_SETTINGS,
            # Default kwargs for all calls made through this LM instance
            # Temperature, max_tokens, etc., can be set here or overridden in dspy.Predict/Module calls
            temperature=settings.GEMINI_DEFAULT_TEMPERATURE if hasattr(settings, 'GEMINI_DEFAULT_TEMPERATURE') else 0.7,
            # max_tokens=settings.GEMINI_DEFAULT_MAX_TOKENS if hasattr(settings, 'GEMINI_DEFAULT_MAX_TOKENS') else 2048, # Example
        )
        
        dspy.settings.configure(lm=custom_lm)
        __configured_dspy_lm = custom_lm # Store the configured instance
        gemini_configured_for_dspy = True
        logger.info(f"DSPy configured globally with AsyncCustomGeminiDspyLM using model: {litellm_model_string}")
        logger.info(f"DSPy LM type: {type(dspy.settings.lm)}")

    except Exception as e:
        logger.error(f"Error configuring DSPy with AsyncCustomGeminiDspyLM: {e}", exc_info=True)
        # Optionally, configure a fallback dummy LM here as well
        # dspy.settings.configure(lm=dspy.utils.DummyLM(f"DSPy in dummy mode due to config error: {e}"))
        # logger.warning("DSPy configured with DummyLM due to an error during AsyncCustomGeminiDspyLM setup.")
        # gemini_configured_for_dspy = False # Explicitly false

# --- Call configuration when this module is loaded ---
# This ensures DSPy is set up as soon as ai_services is imported.
configure_dspy_lm()


# --- Utility function to get the configured LM ---
def get_dspy_lm() -> Optional[AsyncCustomGeminiDspyLM]:
    """
    Returns the globally configured DSPy LM instance.
    Returns None if not configured or if configuration failed.
    """
    if not gemini_configured_for_dspy:
        logger.warning("get_dspy_lm called, but DSPy LM is not successfully configured with Gemini.")
    return __configured_dspy_lm


# --- XML Extraction Function (Keep as is) ---
def extract_xml(text: str, tag: str) -> str:
    """
    Extracts the content of the specified XML tag from the given text.
    Made case-insensitive and strips whitespace. Returns empty string if not found.
    """
    if not text or not tag:
        return ""
    # Ensure text is a string before using regex
    if not isinstance(text, str):
        logger.warning(f"extract_xml received non-string input (type: {type(text)}). Converting to string.")
        text = str(text)

    match = re.search(f'<{tag}>(.*?)</{tag}>', text, re.DOTALL | re.IGNORECASE)
    return match.group(1).strip() if match else ""

