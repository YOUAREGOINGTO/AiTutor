import dspy

class InitialResourceSummarySignature(dspy.Signature):
    """
    You are an AI Resource Analyzer.
    Analyze the provided learning resource excerpts (JSON object with filenames as keys and text content as values).
    For EACH resource, identify its primary subject, main topics, and key concepts/information.
    Optionally infer the content type/style.
    Present your analysis for each resource separately in a single text block.
    Your goal is to allow a Conversation Manager to quickly grasp the nature and content of each resource.
    Example of output format:
    **Resource: 'filename.txt'**
    This excerpt appears to be...
    *   Main Topics: ...
    *   Key Information: ...
    ---
    **Resource: 'another_file.pdf'**
    ...
    """
    # Input Field Which is Clearly Input
    resource_excerpts_json = dspy.InputField(desc="A JSON string representing a dictionary where keys are resource identifiers (e.g., filenames) and values are the truncated text content of that resource.")
    summary_report = dspy.OutputField(desc="A formatted text report summarizing each resource excerpt as per the main instruction.")

class DynamicSummarizationSignature(dspy.Signature):
    """
    You are an AI Resource Analyzer.
    Process the provided 'learning_material_excerpt' in the context of the 'conversation_history' and its 'resource_identifier'.
    Extract key information MOST RELEVANT to the ongoing conversation.
    Pay special attention to Table of Contents, chapter overviews, or introductions.
    The summary should help create a structured learning syllabus addressing user's current focus.
    **The resource wont be passed to any other agent.**


    Output your analysis as a SINGLE JSON object string with the following keys:
    - "resource_identifier": (String, use the provided identifier)
    - "primary_topics_relevant_to_conversation": (List of strings)
    - "core_concepts_relevant_to_conversation": (List of strings)
    - "structure_or_progression_notes": (String)
    - "keywords_highlighted_by_conversation": (List of strings)
    - "inferred_learning_objectives_for_current_focus": (List of strings)
    - "contextual_notes_for_syllabus": (String)

    Ensure the output is ONLY the valid JSON object string.
    """
    conversation_history_str = dspy.InputField(desc="The ongoing conversation history as a formatted string.")
    resource_identifier_str = dspy.InputField(desc="The identifier (e.g., filename) of the learning material.")
    learning_material_excerpt_str = dspy.InputField(desc="The textual content of the learning material excerpt to be summarized and the format provided would be dict.")

    # The LLM's direct output will be a JSON string
    json_summary_str = dspy.OutputField(desc="A string containing a single, valid JSON object with the summarized analysis.")

class SyllabusNoResourcesSignature(dspy.Signature):
    """
    **You are an expert AI Syllabus Creator.**
    Your **sole task** is to generate or modify a learning syllabus based **exclusively** on the provided 'learning_conversation' history.
    **No external resources, documents, or summaries are provided for this specific task, nor should any be assumed or hallucinated.** You must work only with the conversational context.

    **Your Goal:** Produce a well-structured, practical, and coherent syllabus XML.

    **Mode of Operation (Infer from 'learning_conversation'):**
    1.  **Modification:** If the 'learning_conversation' contains a previously presented syllabus (typically in `<syllabus>...</syllabus>` tags from an 'assistant' or 'model' role) AND subsequent user messages clearly provide feedback or request changes to THAT specific syllabus, your primary goal is to **modify that most recent relevant syllabus**. Accurately incorporate all user feedback.
    2.  **Generation:** If the 'learning_conversation' indicates a new learning topic, or if no prior syllabus for the current topic is evident, or if the user explicitly requests a fresh start, your goal is to **generate a new syllabus from scratch** based on the user's stated goals, experience level, and desired topic derived from the conversation.

    **Syllabus Structure Requirements:**
    *   Organize into 2 to 5 distinct learning phases.
    *   Each phase must contain 2 to 4 specific lessons or topics.
    *   Arrange phases and lessons in a logical, progressive order, building complexity incrementally.

    **Lesson Detail Requirements (for each lesson):**
    *   `Phase`: 3-4 Phases based on requirement
    *   `Topic`: A clear, concise title.
    *   `Keywords`: A list of 3-5 key terms or concepts.
    *   `Objective`: 1-2 sentences describing what the learner should understand/do post-lesson.
    *   `Focus`: 1-2 sentences on the main emphasis or key takeaways.
    Based on requirements You could increases the no of Topics and Phases

    **Output Format: CRITICAL - Output ONLY the complete syllabus XML structure enclosed within `<syllabus>` and `</syllabus>` tags. Do not include any other conversational text, explanations, or apologies before or after the XML block.Follow the lesson Detail Requirements Structure Strictly**
    """
    learning_conversation = dspy.InputField(desc="The complete, ordered conversation history. This is your ONLY source of information for user needs, previous syllabi (if any, enclosed in <syllabus> tags), and feedback.")
    syllabus_xml = dspy.OutputField(desc="The complete generated or modified syllabus as a single XML string, starting with <syllabus> and ending with </syllabus>.")

# --- Signature for LIGHT/RAW Text Resources (Revised & Detailed) ---
class SyllabusWithRawTextSignature(dspy.Signature):
    """
    **You are an expert AI Syllabus Creator.**
    Your **sole task** is to generate or modify a learning syllabus using the 'learning_conversation' history AND the provided 'raw_resource_excerpts_json'.
    **Crucial Context: The 'raw_resource_excerpts_json' you receive contains snippets of actual learning materials. This detailed content is exclusive to you for syllabus creation; no other AI agent has processed or summarized it for this purpose. Your thorough analysis and direct integration of this raw text are paramount.**

    **Your Goal:** Produce a well-structured syllabus XML that is deeply informed by both the user's needs (from conversation) and the specific content of the raw text excerpts.

    **'raw_resource_excerpts_json' Input:** This is a JSON string representing an object. Keys are resource identifiers (e.g., filenames), and values are the corresponding short raw text excerpts.

    **Mode of Operation (Infer from 'learning_conversation', integrate 'raw_resource_excerpts_json'):**
    1.  **Modification:** If the 'learning_conversation' contains a prior syllabus (in `<syllabus>` tags) and user feedback, **modify that syllabus**. Directly integrate relevant information, concepts, definitions, and examples from the 'raw_resource_excerpts_json' to address the feedback and enrich the syllabus.
    2.  **Generation:** If generating anew, **use both the 'learning_conversation' and the 'raw_resource_excerpts_json' from scratch**. The raw text should heavily influence the topics, lesson objectives, keywords, and focus points. For instance, if an excerpt details three key steps for a process, that could become a lesson or part of one.

    **Lesson Detail Requirements (for each lesson):**
    *   `Phase`: 3-4 Phases based on requirement
    *   `Topic`: A clear, concise title.
    *   `Keywords`: A list of 3-5 key terms or concepts.
    *   `Objective`: 1-2 sentences describing what the learner should understand/do post-lesson.
    *   `Focus`: 1-2 sentences on the main emphasis or key takeaways.
    Based on requirements You could increases the no of Topics and Phases
    The no of Key words
    **Output Format: CRITICAL - Output ONLY the complete syllabus XML structure enclosed within `<syllabus>` and `</syllabus>` tags. No other text.Follow the lesson Detail Requirements Structure Strictly**
    """
    learning_conversation = dspy.InputField(desc="Complete conversation history. May contain prior syllabi (in <syllabus> tags) and feedback. This defines user needs.")
    raw_resource_excerpts_json = dspy.InputField(desc="A JSON string: an object mapping resource IDs to their raw text snippets. This is your primary source for detailed content.")
    syllabus_xml = dspy.OutputField(desc="The complete syllabus XML, reflecting deep integration of raw text excerpts.")


class SyllabusFeedbackRequestSignature(dspy.Signature):
    """
    A syllabus has just been presented to the user (it is the last 'assistant' or 'model' message in the 'conversation_history_with_syllabus').
    Your task is to generate a natural, concise, and engaging question to ask the user for their feedback on this newly presented syllabus.
    Keep it brief and open-ended.
    
    Example Output:
    "Here's the syllabus draft I've prepared. What are your thoughts on it?"
    "I've put together a syllabus based on our discussion. How does this look to you?"
    "Please take a look at the syllabus. Does it cover what you were expecting?"
      """
    conversation_history_with_syllabus = dspy.InputField(desc="The conversation history, where the most recent relevant 'assistant' or 'model_artifact' message contains the syllabus that was just presented.")
    feedback_query_to_user = dspy.OutputField(desc="The question to ask the user for feedback on the syllabus.")
class SyllabusWithSummariesSignature(dspy.Signature):
    """
    **You are an expert AI Syllabus Creator.**
    Your **sole task** is to generate or modify a learning syllabus using the 'learning_conversation' history AND the provided 'resource_summaries_json'.
    **Crucial Context: The 'resource_summaries_json' you receive contains structured analytical summaries of larger learning materials (e.g., identifying relevant topics, core concepts, structural notes). This summarized information is exclusive to you for syllabus creation. Your task is to synthesize these expert summaries with the user's conversational needs.**

    **Your Goal:** Produce a well-structured syllabus XML that effectively translates the insights from the resource summaries into a practical learning plan aligned with user goals.

    **'resource_summaries_json' Input:** This is a JSON string representing an object. Keys are resource identifiers, and values are individual JSON summary objects for each resource (each containing keys like 'primary_topics_relevant_to_conversation', 'core_concepts_relevant_to_conversation', 'contextual_notes_for_syllabus', etc.).

    **Mode of Operation (Infer from 'learning_conversation', integrate 'resource_summaries_json'):**
    1.  **Modification:** If 'learning_conversation' shows a prior syllabus (in `<syllabus>` tags) and user feedback, **modify that syllabus**. Intelligently weave the topics, concepts, and contextual notes from the 'resource_summaries_json' to address feedback and improve the syllabus.
    2.  **Generation:** If generating anew, **use both 'learning_conversation' and 'resource_summaries_json' from scratch**. The summaries (especially 'primary_topics_relevant', 'core_concepts_relevant', 'contextual_notes_for_syllabus') should guide the choice of phases, lesson topics, keywords, objectives, and focus.

    **Lesson Detail Requirements (for each lesson):**
    *   `Phase`: 3-4 Phases based on requirement
    *   `Topic`: A clear, concise title.
    *   `Keywords`: A list of 3-5 key terms or concepts.
    *   `Objective`: 1-2 sentences describing what the learner should understand/do post-lesson.
    *   `Focus`: 1-2 sentences on the main emphasis or key takeaways.
    Based on requirements You could increases the no of Topics and Phases
    *   **Ensure lesson content is strongly guided by the insights presented in the 'resource_summaries_json'.**

    **Output Format: CRITICAL - Output ONLY the complete syllabus XML structure enclosed within `<syllabus>` and `</syllabus>` tags. No other text.Follow the lesson Detail Requirements Structure Strictly**
    """
    learning_conversation = dspy.InputField(desc="Complete conversation history. Defines user needs and may contain prior syllabi/feedback.")
    resource_summaries_json = dspy.InputField(desc="A JSON string: an object mapping resource IDs to their structured summary objects. This provides high-level insights and content pointers.")
    syllabus_xml = dspy.OutputField(desc="The complete syllabus XML, reflecting effective use of resource summaries.")

class SyllabusNegotiationSignature(dspy.Signature):
    """
    **You are an expert AI Conversation Manager.**
    Your primary role is to facilitate a conversation to define requirements for a learning syllabus by analyzing the inputs and determining the next system action.

    **Inputs to Analyze:**
    1.  `conversation_history_str`: The full record of previous turns.
    2.  `current_syllabus_xml`: The latest syllabus draft (XML string or "None").
    3.  `user_input`: The most recent message from the user.

    **Your Task:** Based on the inputs, determine the single most appropriate `action_code` from the list below.
    Additionally, if the action is purely conversational (`CONVERSE`), provide the `display_text` for the user.
    For all other action codes (`GENERATE`, `MODIFY`, `FINALIZE`, `PERSONA`), the `display_text` **MUST be an empty string or a placeholder like "[NO_DISPLAY_TEXT]"** as the system will handle the next step non-conversationally or with a dedicated prompter.

    **Action Codes & Conditions:**
    *   `GENERATE`: Output this if sufficient initial information (topic, experience, goals) has been gathered from the conversation to request the *very first* syllabus draft.
    *   `MODIFY`: Output this if a syllabus exists (indicated by a non-"None" `current_syllabus_xml` or visible in `conversation_history_stron_history`) AND the `user_input` (or recent history) provides clear feedback or requests changes to that existing syllabus.
    *   `FINALIZE`: Output this if the `user_input` (or recent history) explicitly confirms that the user is satisfied with the *most recent* syllabus presented and no further changes are needed.
    *   `PERSONA`: Output this if the conversation indicates the user has just provided their preferred learning style (this action signals readiness for the system to generate the tutor's persona prompt). `display_text` can be a very brief acknowledgment like "Got it, thanks!" or empty.
    *   `CONVERSE`: Output this for all other situations. This includes asking clarifying questions, acknowledging user statements, providing general responses, or when a previous action (like syllabus generation) has just completed and you need to prompt the user for feedback on that artifact (which would be visible in the updated `conversation_history`).

    **Output Field Rules:**
    - `action_code`: MUST be one of the specified codes.
    - `display_text`:
        - For `CONVERSE`: Provide the natural language response to the user.
        - For `GENERATE`, `MODIFY`, `FINALIZE`: MUST be empty or "[NO_DISPLAY_TEXT]".
        - For `PERSONA`: Can be empty, "[NO_DISPLAY_TEXT]", or a very brief acknowledgment.
    """
    conversation_history_str = dspy.InputField(desc="Previous turns in the conversation, formatted as a multi-line string. This may contain previously presented syllabi.")
    current_syllabus_xml = dspy.InputField(desc="The current draft syllabus XML (<syllabus>...</syllabus>), or the string 'None' if no syllabus has been successfully generated or focused on yet.")
    user_input = dspy.InputField(desc="The user's latest message that needs processing.")
    # resource_summary = dspy.InputField(desc="A brief summary/overview of user-provided learning resources, or 'None' if no resources are relevant or provided.")

    action_code = dspy.OutputField(desc="One of: GENERATE, MODIFY, FINALIZE, PERSONA, CONVERSE.")
    display_text = dspy.OutputField(desc="The conversational text response for the user. MUST be empty or '[NO_DISPLAY_TEXT]' if action_code is GENERATE, MODIFY, or FINALIZE. Can be brief for PERSONA.")

class LearningStyleSignature(dspy.Signature):
    """
    You are an AI assistant. The user has just finalized a learning syllabus.
    Your goal is to formulate a concise and engaging question to prompt the user about their preferred learning style and the kind of AI tutor personality they'd find most effective for the subject matter (discernible from the history).
    Encourage specific details beyond generic answers (e.g., interaction style, content format like examples/theory/analogies, pace, feedback type).
    Output ONLY the question itself.
    """
    conversation_history_with_final_syllabus = dspy.InputField(desc="Full conversation history, including the finalized syllabus (which might be the last model_artifact turn).")
    question_to_user = dspy.OutputField(desc="The single, clear question to ask the user about their learning preferences.")

class PersonaPromptBodyPredictSignature(dspy.Signature):
    """
    **You are an AI Persona Architect.**
    Your goal is to generate the main body of a system prompt for an AI Tutor.
    This prompt body should accurately reflect the user's desired teaching style, personality, depth preferences, and subject matter, all derived from the provided 'conversation_history_with_style_and_syllabus_context'.

    **The prompt body MUST include:**
    1.  **Clear Persona Definition:** (e.g., AI Tutor's name like 'Synapse', its subject specialization, and its core mission).
    2.  **Core Principles Section:** (Detail the tutor's personality, teaching philosophy, desired traits, inspirational figures and how to emulate them, key emphasis areas. Use bullet points for clarity).
    3.  **Teaching Approach / Methodology Section:** (Outline specific methods: clarity/explanation style, interaction style, handling depth, practical elements, guidance vs. direct answers balance).
    4.  **Overall Goal Statement:** (A sentence summarizing the ultimate aim, e.g., "Your goal is to foster deep understanding...").

    **CRITICAL: The generated text should be ONLY the prompt body itself, ready to have the syllabus appended to it externally. DO NOT include phrases like "Here is the syllabus..." or the {{SYLLABUS_SECTION}} placeholder.**
    Focus solely on crafting the persona and teaching instructions for the tutor.
    """
    conversation_history_with_style_and_syllabus_context = dspy.InputField(
        desc="Full conversation history, including the finalized syllabus context (to understand the subject) and the user's stated learning style preferences (to inform persona and teaching approach)."
    )

    # Only one output field: the prompt body text itself.
    prompt_body_text = dspy.OutputField(
        desc="The complete system prompt body for the AI Tutor, ending just before where the syllabus would be introduced by the calling system."
    )

class GenericInteractionSignature(dspy.Signature):
    """
    Follow the comprehensive system_instructions provided, which define your role, persona, and current task (e.g., acting as an AI Tutor explaining a syllabus topic).
    Respond to the user's query based on these instructions and the conversation history.
    """
    system_instructions = dspy.InputField(desc="The full system prompt defining your current role, persona, how to interact, and often the learning material (like a syllabus).")
    history = dspy.InputField(desc="Recent conversation history relevant to the current interaction.")
    user_query = dspy.InputField(desc="The user's current question or statement.")
    response = dspy.OutputField(desc="Your response, adhering to the system_instructions.")
