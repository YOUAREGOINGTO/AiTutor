# api/dspy_modules.py
import dspy
import json
import logging
from typing import Optional, Dict, Any, List

from .dspy_signatures import (
    InitialResourceSummarySignature, DynamicSummarizationSignature,
    SyllabusNoResourcesSignature, SyllabusWithRawTextSignature, SyllabusWithSummariesSignature,
    SyllabusNegotiationSignature, LearningStyleSignature, PersonaPromptBodyPredictSignature,
    GenericInteractionSignature
)


logger = logging.getLogger(__name__)


class InitialResourceSummarizer(dspy.Module):
    def __init__(self):
        super().__init__()
        self.summarize = dspy.Predict(InitialResourceSummarySignature)

    async def forward(self, extracted_basedata_dict: Dict[str, str]):
        # Convert dict to JSON string for the input field
        json_input_str = json.dumps(extracted_basedata_dict, indent=2)
        prediction = await self.summarize.acall(resource_excerpts_json=json_input_str)
        return prediction.summary_report # Means Return Output and There is



class DynamicResourceSummarizerModule(dspy.Module):
    def __init__(self):
        super().__init__()
        # Using Predict, as the task is to generate a structured string based on clear instructions.
        # If formatting is tricky, ChainOfThought could be an alternative.
        self.generate_json_summary = dspy.Predict(DynamicSummarizationSignature)

    async def forward(self,
                resource_content: str,
                resource_identifier: str,
                conversation_history_str: str, # Takes the list of dicts
                max_length: int = 100000 # Consistent with your original function
               ) -> Optional[Dict[str, Any]]: # Returns a Python dict or None

        if not resource_content.strip():
            print(f"[DynamicResourceSummarizerModule] Skipping empty resource: {resource_identifier}")
            return None

        truncated_content = resource_content[:max_length]
        if len(resource_content) > max_length:
            print(f"[DynamicResourceSummarizerModule] INFO: Resource '{resource_identifier}' truncated to {max_length} chars.")

        # Format conversation history for the signature's input field

        try:
            # Call the DSPy Predictor
            prediction =  await self.generate_json_summary.acall(
                conversation_history_str=conversation_history_str,
                resource_identifier_str=resource_identifier,
                learning_material_excerpt_str=truncated_content
            )
            raw_json_string_output = prediction.json_summary_str

            # Parse the JSON string output from the LLM
            # (Similar parsing logic as in your original summarize_single_resource_dynamically)
            cleaned_json_str = raw_json_string_output.strip()
            if cleaned_json_str.startswith("```json"):
                cleaned_json_str = cleaned_json_str[len("```json"):]
            elif cleaned_json_str.startswith("```"):
                cleaned_json_str = cleaned_json_str[len("```"):]
            if cleaned_json_str.endswith("```"):
                cleaned_json_str = cleaned_json_str[:-len("```")]
            cleaned_json_str = cleaned_json_str.strip()
            print("1")
            print(cleaned_json_str)

            if not cleaned_json_str:
                print(f"WARN [DynamicResourceSummarizerModule]: LLM returned empty string for JSON summary for '{resource_identifier}'.")
                return {"resource_identifier": resource_identifier, "raw_summary_text": raw_json_string_output, "is_fallback": True, "error": "Empty JSON string"}

            try:
                summary_data_dict = json.loads(cleaned_json_str)
                if isinstance(summary_data_dict, dict) and "resource_identifier" in summary_data_dict:
                    return summary_data_dict # Success!
                else:
                    print(f"WARN [DynamicResourceSummarizerModule]: For '{resource_identifier}', LLM produced non-standard JSON structure after cleaning. Output: {raw_json_string_output[:200]}...")
                    return {"resource_identifier": resource_identifier, "raw_summary_text": raw_json_string_output, "is_fallback": True, "error": "Non-standard JSON structure"}
            except json.JSONDecodeError:
                print(f"WARN [DynamicResourceSummarizerModule]: Could not parse JSON from LLM summary for '{resource_identifier}'. Raw output: {raw_json_string_output[:200]}...")
                return {"resource_identifier": resource_identifier, "raw_summary_text": raw_json_string_output, "is_fallback": True, "error": "JSONDecodeError"}

        except Exception as e:
            print(f"ERROR [DynamicResourceSummarizerModule]: Unexpected error during summarization for '{resource_identifier}': {e}")
            import traceback
            traceback.print_exc()
            return {"resource_identifier": resource_identifier, "raw_summary_text": str(e), "is_fallback": True, "error": str(type(e).__name__)}
class SyllabusGeneratorRouter(dspy.Module):
    def __init__(self):
        super().__init__()
        # Use ChainOfThought for potentially better structured output for syllabus generation
        self.gen_no_resources = dspy.Predict(SyllabusNoResourcesSignature)
        self.gen_with_raw = dspy.Predict(SyllabusWithRawTextSignature)
        self.gen_with_summaries = dspy.Predict(SyllabusWithSummariesSignature)

    async def forward(self,
                conversation_history_str: str,
                #task_description: str,
                resource_type: str, # "NONE", "RAW_TEXT", "SUMMARIES"
                resource_content: Optional[str] = None, # Actual raw text or JSON summaries string
                # existing_syllabus_xml: Optional[str] = None Not needed
               ) -> str: # Returns the syllabus_xml string

        common_args = {
            "learning_conversation": conversation_history_str,
            #"task_description": #task_description,
            # "existing_syllabus_xml": existing_syllabus_xml if existing_syllabus_xml else "None"
        }

        if resource_type == "NONE":
            prediction = await self.gen_no_resources.acall(**common_args)
        
        elif resource_type == "RAW_TEXT":
            if not resource_content: raise ValueError("resource_content needed for RAW_TEXT type")
            prediction = await self.gen_with_raw.acall(raw_resource_excerpts_json=resource_content, **common_args)
            # prediction = await self.gen_with_raw.acall(raw_resource_excerpts=resource_content, **common_args)
        elif resource_type == "SUMMARIES":
            if not resource_content: raise ValueError("resource_content needed for SUMMARIES type (should be JSON string)")
            prediction = await self.gen_with_summaries.acall(resource_summaries_json=resource_content, **common_args)
        else:
            raise ValueError(f"Unknown resource_type: {resource_type}")

        # Post-process to ensure <syllabus> tags, as in your previous SyllabusGenerator
        content = prediction.syllabus_xml.strip()
        if not content.lower().startswith("<syllabus>"):
            content = f"<syllabus>\n{content}"
        if not content.lower().endswith("</syllabus>"):
            content = f"{content}\n</syllabus>"
        return content

class ConversationManager(dspy.Module):
    def __init__(self):
        super().__init__()
        # Using Predict as the Signature is now quite detailed.
        # If the LLM struggles to follow the conditional logic for display_text,
        # ChainOfThought might be needed, or more explicit examples in the Signature.
        self.manage = dspy.Predict(SyllabusNegotiationSignature)

    async def forward(self, conversation_history_str: str, current_syllabus_xml: str, user_input: str):
        # The user_input is the latest turn, but the full context is in conversation_history.
        # The Signature is designed to look at the user_input in context of the whole history.
        prediction = await self.manage.acall(
            conversation_history_str=conversation_history_str,
            current_syllabus_xml=current_syllabus_xml,
            user_input=user_input, # Pass the latest user input specifically
            # resource_summary=resource_summary
        )

        action = prediction.action_code.strip().upper()
        text_to_display = prediction.display_text.strip()

        # Enforce display_text rules based on the Signature's instructions
        if action in ["GENERATE", "MODIFY", "FINALIZE"]:
            if text_to_display and text_to_display.upper() != "[NO_DISPLAY_TEXT]":
                print(f"[ConversationManager WARNING] Action '{action}' returned with display_text: '{text_to_display}'. Forcing to empty as per rules.")
            text_to_display = "" # Enforce empty
        elif text_to_display.upper() == "[NO_DISPLAY_TEXT]":
            text_to_display = ""

        # For PERSONA, allow brief confirmation or empty. If it's placeholder, make empty.
        if action == "PERSONA" and text_to_display.upper() == "[NO_DISPLAY_TEXT]":
            text_to_display = ""

        return action, text_to_display
    
class LearningStyleQuestioner(dspy.Module):
    def __init__(self):
        super().__init__()
        self.ask = dspy.Predict(LearningStyleSignature)

    async def forward(self, conversation_history_str: str):
        prediction = await self.ask.acall(conversation_history_with_final_syllabus=conversation_history_str)
        return prediction.question_to_user


class PersonaPromptGenerator(dspy.Module):
    def __init__(self):
        super().__init__()
        # Switched to dspy.Predict with the new signature
        self.generate_prompt_body = dspy.Predict(PersonaPromptBodyPredictSignature)

    async def forward(self,conversation_history_str: str):
      try:
        # Call the dspy.Predict instance
        prediction_object = await self.generate_prompt_body.acall(
            conversation_history_with_style_and_syllabus_context=conversation_history_str
        )

        prompt_body = prediction_object.prompt_body_text

        if not prompt_body or not prompt_body.strip():
            print("[PersonaPromptGenerator] Error: LLM returned an empty or whitespace-only prompt body.")
            return None # Or a default fallback string

        return prompt_body.strip() # Return the generated text

      except Exception as e:
        print(f"[PersonaPromptGenerator] Error in forward pass: {e}")
        import traceback
        traceback.print_exc()
        return None # Or a default fallback string


class ExplainerModule(dspy.Module): # Renamed for clarity
    def __init__(self):
        super().__init__()
        self.explain = dspy.Predict(GenericInteractionSignature)

    async def forward(self, system_instructions_str: str, history_str: str, user_query_str: str) -> str: # Made async
        prediction = await  self.explain.acall( # await predict
            system_instructions=system_instructions_str,
            history=history_str,
            user_query=user_query_str
        )
        return prediction.response.strip()