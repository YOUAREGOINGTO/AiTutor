# api/models.py
from django.db import models
import uuid# api/models.py
from django.db import models
from django.conf import settings # To link to the User model (if needed later)
import uuid                   # To generate unique IDs
from typing import Dict, Any, List # For type hinting (Ensure this import is present)

class ChatSession(models.Model):
    """Represents a single chat conversation thread."""
    # If you implement user authentication later, you can uncomment and use this:
    # user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)

    session_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Store the last known state relevant for resuming (if session persistence is enabled)
    # Values should correspond to STAGE constants in orchestrator.py
    current_stage = models.CharField(max_length=50, default="START")
    # Store the finalized syllabus XML (including tags)
    final_syllabus_xml = models.TextField(null=True, blank=True)
    # Store the generated system prompt for the explainer persona
    explainer_system_prompt = models.TextField(null=True, blank=True)
    explanation_start_index = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Index in ChatMessage history where the EXPLAINING stage began (0-based)."
    )

    # Optional: For easier identification in admin or lists
    title = models.CharField(max_length=200, blank=True, default="New Chat")

    class Meta:
        ordering = ['-created_at'] # Show newest sessions first in queries/admin

    def __str__(self):
         # Simple representation without user for now
         return f"Chat Session {self.session_id} - Stage: {self.current_stage}"


class ChatMessage(models.Model):
    """Represents a single message within a ChatSession."""
    # Define choices for the 'role' field
    ROLE_CHOICES = [
        ('user', 'User'),           # Message from the human user
        ('model', 'AI Model'),      # Message from the LLM (manager, generator, explainer)
        ('system', 'System'),       # Message from application logic (optional, used with message_type)
    ]
    # Define choices for the 'message_type' field (primarily for 'system' role)
    MESSAGE_TYPE_CHOICES = [
        ('message', 'Standard Message'), # Default type for user/model, or generic system msg
        ('syllabus', 'Syllabus Display'), # System msg indicating syllabus should be shown
        ('info', 'Informational'),      # System msg for info banners (like transitions)
        # Add other specific system message types if needed later
    ]

    message_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # Link back to the parent session. Deleting session deletes messages.
    session = models.ForeignKey(ChatSession, related_name='messages', on_delete=models.CASCADE)
    # Store the role (who sent it) using choices for validation/admin UI
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    # The actual text content of the message
    content = models.TextField()
    # Timestamp when the message was created/saved
    timestamp = models.DateTimeField(auto_now_add=True)
    # Explicit ordering field to handle potential timestamp collisions
    order = models.PositiveIntegerField(default=0)
    # Optional field to further classify system messages for UI rendering
    message_type = models.CharField(
        max_length=20,
        choices=MESSAGE_TYPE_CHOICES,
        default='message', # Sensible default
        null=True, blank=True # Allow null/blank as it's less critical for user/model roles
    )

    class Meta:
        # Default ordering for message queries: by session, then time, then explicit order
        ordering = ['session', 'timestamp', 'order']

    def __str__(self):
        """String representation for admin/debugging."""
        ts = self.timestamp.strftime('%Y-%m-%d %H:%M') if self.timestamp else 'No Timestamp'
        # Safely access session ID even if session is somehow None (shouldn't happen with FK)
        session_display_id = str(self.session.session_id) if self.session else 'No Session'
        # Limit content preview length
        content_preview = self.content[:50] + ('...' if len(self.content) > 50 else '')
        return f"{session_display_id} [{ts}] {self.role}: {content_preview}"

    def to_dict(self) -> Dict[str, Any]:
        """
        Converts this message object into the dictionary format expected by
        the orchestrator and the underlying LLM API (e.g., Gemini).
        Ensures the 'parts' structure is correct.
        """
        # Gemini expects 'parts' as a list containing dictionaries with a 'text' key.
        return {"role": self.role, "parts": [{'text': self.content}]}