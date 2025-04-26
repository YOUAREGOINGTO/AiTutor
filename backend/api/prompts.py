# api/prompts.py
import os
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

PROMPTS_DIR = os.path.join(settings.BASE_DIR, 'api', 'prompts')

def load_prompt(filename: str) -> str:
    """Loads a prompt from the prompts directory."""
    filepath = os.path.join(PROMPTS_DIR, filename)
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except FileNotFoundError:
        logger.error(f"Prompt file not found: {filepath}")
        return f"[ERROR: Prompt file '{filename}' not found]"
    except Exception as e:
        logger.error(f"Error loading prompt file {filepath}: {e}", exc_info=True)
        return f"[ERROR: Could not load prompt '{filename}']"

# Load prompts on application start
CONVERSATION_MANAGER_PROMPT = load_prompt('conversation_manager.txt')
SYLLABUS_GENERATOR_PROMPT = load_prompt('syllabus_generator.txt')
PERSONA_ARCHITECT_PROMPT = load_prompt('persona_architect.txt')

# Basic check if prompts loaded correctly
if any("[ERROR:" in p for p in [CONVERSATION_MANAGER_PROMPT, SYLLABUS_GENERATOR_PROMPT, PERSONA_ARCHITECT_PROMPT]):
    logger.critical("One or more essential AI prompts failed to load. Tutor functionality will be impaired.")