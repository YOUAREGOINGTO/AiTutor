# api/admin.py
from django.contrib import admin
from .models import ChatSession, ChatMessage

class ChatMessageInline(admin.TabularInline):
    model = ChatMessage
    # Use actual field names from ChatMessage model
    fields = ('role', 'content', 'message_type', 'timestamp', 'order')
    readonly_fields = ('timestamp',) # message_id is also read-only by default as PK
    extra = 0
    ordering = ('timestamp', 'order')
    # Optional: Add raw_id_fields for session if list gets long
    # raw_id_fields = ('session',)

@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    # --- CORRECTED FIELD NAMES ---
    list_display = (
        'session_id',       # Use 'session_id', NOT 'session_uuid'
        'current_stage',
        'title',            # Added title for better identification
        'created_at',
        'updated_at'
    )
    list_filter = ('current_stage', 'created_at')
    search_fields = ('session_id', 'title') # Search by actual ID and title
    readonly_fields = (
        'session_id',       # Use 'session_id', NOT 'session_uuid'
        'created_at',
        'updated_at'
        # Removed 'current_state_json' as it doesn't exist on the model
    )
    # --- END CORRECTIONS ---
    inlines = [ChatMessageInline] # Keep the inline messages

# Keep ChatMessageAdmin as is, assuming its fields match the model
@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('message_id', 'session', 'role', 'message_type', 'content_preview', 'timestamp')
    list_filter = ('role', 'message_type', 'timestamp', 'session')
    search_fields = ('content', 'session__session_id') # Correct way to search related field
    readonly_fields = ('message_id', 'timestamp')

    def content_preview(self, obj):
        # Make preview safer in case content is None
        content = obj.content or ""
        return content[:100] + '...' if len(content) > 100 else content
    content_preview.short_description = 'Content Preview'