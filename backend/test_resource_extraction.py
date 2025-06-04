# test_resource_extraction.py
import os
import sys
import django
import logging
import asyncio # Needed to run the async function
from typing import Dict, List

# --- Configure Django Settings ---
print("Configuring Django settings for testing load_and_extract_simulated_resources...")
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tutor_project.settings')
try:
    django.setup()
    print("Django setup complete.")
except Exception as e:
    print(f"Django setup error: {e}")
    # For this specific test, Django setup might be crucial if @database_sync_to_async
    # relies on it, or if the _extract functions use Django logging that needs it.
    # sys.exit(1) # You might want to exit if Django setup is critical

# --- Configure Logging ---
logging.basicConfig(level=logging.DEBUG, format='{levelname} {asctime} {name} [{module}:{lineno}]: {message}', style='{}')
logger = logging.getLogger(__name__)
# Set loggers for the modules we are testing to DEBUG
logging.getLogger('api.views').setLevel(logging.DEBUG)
logging.getLogger('api.resource_processor').setLevel(logging.DEBUG)

# --- Import the function to test AND its dependencies ---
try:
    # The function we want to test is in views.py
    from api.views import load_and_extract_simulated_resources
    # It calls these helper functions from resource_processor.py
    from api.resource_processor import (
        _extract_text_from_pdf_bytes,
        _extract_text_from_docx_bytes,
        _extract_text_from_txt_bytes
    )
    # Make sure these helpers are globally available for load_and_extract_simulated_resources
    # This is usually handled by Python's module system if views.py imports them.
    # To be explicit for testing or if running from a non-standard context, you could ensure they are in globals:
    # globals()['_extract_text_from_pdf_bytes'] = _extract_text_from_pdf_bytes
    # globals()['_extract_text_from_docx_bytes'] = _extract_text_from_docx_bytes
    # globals()['_extract_text_from_txt_bytes'] = _extract_text_from_txt_bytes
    # However, direct import into views.py from resource_processor.py is cleaner and standard.

    print("Successfully imported functions for testing.")
except ImportError as e:
    print(f"FATAL: Could not import necessary functions: {e}")
    print("Ensure that:")
    print("  1. This script is run from your Django project's root directory (where manage.py is).")
    print("  2. The paths in `sys.path` allow finding the 'api' module.")
    print("  3. `api.views` correctly imports `_extract_text_from_..._bytes` from `api.resource_processor`.")
    sys.exit(1)


async def main_test():
    logger.info("--- Starting Test for `load_and_extract_simulated_resources` ---")

    # --- !!! IMPORTANT: REPLACE WITH ACTUAL PATHS TO YOUR TEST FILES !!! ---
    # These paths must be accessible from where this script is run.
    test_file_paths: List[str] = [
        r"C:\Users\yaswa\OneDrive\Desktop\Research Papers\Attention is all You need.pdf",
    ]
    
    # Create a dummy unsupported_file.zip for testing if it doesn't exist, or point to a real one
    unsupported_file_path = r"C:\path\to\your\unsupported_file.zip"
    if not os.path.exists(os.path.dirname(unsupported_file_path)):
        try:
            os.makedirs(os.path.dirname(unsupported_file_path))
        except OSError:
            pass # Directory might already exist due to race condition or other reasons
    if not os.path.exists(unsupported_file_path) and os.path.exists(os.path.dirname(unsupported_file_path)):
        try:
            with open(unsupported_file_path, 'wb') as f_zip: # create empty zip for test
                f_zip.write(b"PK\x05\x06\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00")
            logger.info(f"Created dummy unsupported file for testing: {unsupported_file_path}")
        except Exception as e_create_dummy:
             logger.warning(f"Could not create dummy unsupported_file.zip: {e_create_dummy}. Test for unsupported type might behave differently.")


    if not any(os.path.exists(p) for p in test_file_paths if "non_existent" not in p and "unsupported" not in p):
        logger.error("CRITICAL: None of the primary test files (PDF, DOCX, TXT) exist. Please update paths.")
        logger.error("Aborting test.")
        return

    # Call the async function
    extracted_data: Dict[str, str] = await load_and_extract_simulated_resources(test_file_paths)

    logger.info("\n--- Results from `load_and_extract_simulated_resources` ---")
    if extracted_data:
        print(f"Number of successfully processed files: {len(extracted_data)}")
        for filename, text_content in extracted_data.items():
            print(f"  File: '{filename}'")
            print({text_content})
            print(f"    Length of extracted text: {len(text_content)} characters")
            print(f"    Preview (first 200 chars): '{text_content[:200].replace(chr(10), ' ')}...'")
    else:
        print("No data was extracted. Check logs for errors or if all test files were skipped.")

    logger.info("--- Test for `load_and_extract_simulated_resources` Finished ---")


if __name__ == "__main__":
    # Ensure the script is run from the project root so 'api.views' can be found.
    # If your project structure is different, you might need to adjust sys.path:
    # project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..')) # If script is in 'tests' subdir
    # if project_root not in sys.path:
    # sys.path.insert(0, project_root)

    asyncio.run(main_test())