# api/resource_processor.py
import io
import PyPDF2 # Make sure this is in your requirements.txt
import docx # Make sure python-docx is in your requirements.txt
import logging
from typing import Optional, Dict, List, Union, Any

logger = logging.getLogger(__name__)

# Maximum file size to process (e.g., 10MB) to prevent server overload
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024 # Just For warning

def _extract_text_from_pdf_bytes(file_bytes: bytes, filename: str) -> Optional[str]:
    try:
        pdf_file = io.BytesIO(file_bytes)
        reader = PyPDF2.PdfReader(pdf_file)
        if reader.is_encrypted:
            try:
                if reader.decrypt('') == PyPDF2.PasswordType.NOT_DECRYPTED:
                    logger.warning(f"PDF '{filename}' is encrypted and password couldn't be bypassed.")
                    return None
            except Exception as e:
                logger.warning(f"Failed to decrypt PDF '{filename}': {e}")
                return None
        
        text = []
        for page_num in range(len(reader.pages)):
            try:
                page = reader.pages[page_num]
                page_text = page.extract_text()
                if page_text:
                    text.append(page_text)
            except Exception as e_page:
                logger.warning(f"Could not extract text from page {page_num + 1} of '{filename}': {e_page}")
                continue # Skip problematic pages
        
        full_text = "\n".join(text).strip()
        logger.info(f"Successfully extracted text from PDF '{filename}'. Length: {len(full_text)} chars.")
        return full_text if full_text else None
    except PyPDF2.errors.PdfReadError as e:
        logger.error(f"Invalid PDF file '{filename}': {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error extracting text from PDF '{filename}': {e}", exc_info=True)
        return None

def _extract_text_from_docx_bytes(file_bytes: bytes, filename: str) -> Optional[str]:
    try:
        doc_file = io.BytesIO(file_bytes)
        document = docx.Document(doc_file)
        text = "\n".join([para.text for para in document.paragraphs if para.text.strip()])
        full_text = text.strip()
        logger.info(f"Successfully extracted text from DOCX '{filename}'. Length: {len(full_text)} chars.")
        return full_text if full_text else None
    except Exception as e:
        logger.error(f"Error extracting text from DOCX '{filename}': {e}", exc_info=True)
        return None

def _extract_text_from_txt_bytes(file_bytes: bytes, filename: str) -> Optional[str]:
    try:
        text = file_bytes.decode('utf-8')
    except UnicodeDecodeError:
        try:
            logger.warning(f"UTF-8 decoding failed for '{filename}', trying latin-1.")
            text = file_bytes.decode('latin-1')
        except UnicodeDecodeError:
            logger.error(f"Could not decode TXT file '{filename}' with UTF-8 or latin-1.")
            return None
        except Exception as e_latin1:
             logger.error(f"Error decoding TXT file '{filename}' with latin-1: {e_latin1}")
             return None
    except Exception as e:
        logger.error(f"Error reading TXT file '{filename}': {e}", exc_info=True)
        return None
    
    full_text = text.strip()
    logger.info(f"Successfully read text from TXT '{filename}'. Length: {len(full_text)} chars.")
    return full_text if full_text else None

def process_uploaded_files(uploaded_files: List[Any]) -> Dict[str, str]:
    """
    Processes a list of uploaded file objects (e.g., from Django's request.FILES).
    Returns a dictionary mapping filenames to their extracted text content.
    Skips files that are too large or unsupported.
    """
    extracted_texts = {}
    if not uploaded_files:
        return extracted_texts

    for uploaded_file in uploaded_files:
        filename = getattr(uploaded_file, 'name', 'unknown_file')
        file_size = getattr(uploaded_file, 'size', 0)

        if file_size > MAX_FILE_SIZE_BYTES:
            logger.warning(f" The file size is Bigger than 10 MB it might take a while.")
            # continue

        file_content_bytes: Optional[bytes] = None
        try:
            # For Django UploadedFile, .read() gives bytes
            # Ensure the file pointer is at the beginning if it might have been read before
            if hasattr(uploaded_file, 'seek'):
                 uploaded_file.seek(0)
            file_content_bytes = uploaded_file.read()
        except Exception as e:
            logger.error(f"Could not read bytes from uploaded file '{filename}': {e}")
            continue
        
        if not file_content_bytes:
            logger.warning(f"File '{filename}' is empty.")
            continue

        text_content: Optional[str] = None
        file_extension = filename.split('.')[-1].lower() if '.' in filename else ''

        logger.info(f"Processing uploaded file: '{filename}', type: '{file_extension}', size: {file_size} bytes")

        if file_extension == 'pdf':
            text_content = _extract_text_from_pdf_bytes(file_content_bytes, filename)
        elif file_extension == 'docx':
            text_content = _extract_text_from_docx_bytes(file_content_bytes, filename)
        elif file_extension == 'txt':
            text_content = _extract_text_from_txt_bytes(file_content_bytes, filename)
        else:
            logger.warning(f"Skipping unsupported file type: '{filename}' (extension: '{file_extension}')")
            continue # Skip to next file

        if text_content:
            extracted_texts[filename] = text_content
        else:
            logger.warning(f"No text could be extracted from '{filename}'.")
            
    return extracted_texts