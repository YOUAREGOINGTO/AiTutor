# api/dspy_llm.py
import dspy
import litellm
from typing import Optional, List, Dict, Any, Union
import logging
from django.conf import settings
from .async_rate_limiter import AsyncRateLimiter # Ensure this is your async rate limiter

logger = logging.getLogger(__name__)

class AsyncCustomGeminiDspyLM(dspy.LM):
    def __init__(
        self,
        model: str, # e.g., "gemini/gemini-1.5-flash-latest"
        rate_limiter_instance: AsyncRateLimiter, # Expects your AsyncRateLimiter
        api_key: Optional[str] = None,
        safety_settings: Optional[List[Dict[str, str]]] = None,
        **kwargs, # For other LiteLLM params like temperature, max_tokens
    ):
        super().__init__(model)
        self.model = model
        self.api_key = api_key if api_key else settings.GEMINI_API_KEY
        self.rate_limiter = rate_limiter_instance
        self.safety_settings = safety_settings if safety_settings else settings.DEFAULT_SAFETY_SETTINGS
        self.kwargs = kwargs # Store kwargs like temperature, max_tokens
        self.provider = "custom_async_gemini_litellm"

        if not self.api_key:
            logger.warning("Gemini API key not found in settings for AsyncCustomGeminiDspyLM. LiteLLM will try env vars.")
        
        logger.info(f"AsyncCustomGeminiDspyLM initialized for model: {self.model} via LiteLLM. Rate limiter enabled.")

    def _prepare_litellm_messages_from_dspy_inputs(
        self, dspy_input: Union[str, List[Dict[str, str]]]
    ) -> List[Dict[str, str]]:
        """
        Converts DSPy style input (string or list of messages)
        to LiteLLM's expected messages format.
        This version is simple, like your working notebook version.
        """
        logger.debug(f"INSIDE _prepare: dspy_input (type {type(dspy_input)}) STARTS WITH: {str(dspy_input)[:200]}...") #
        if isinstance(dspy_input, str):

            return [{"role": "user", "content": dspy_input}]
        elif isinstance(dspy_input, list):
            # While using litellm you shouldn't use model instead you should use system/assistant
            # i.e., [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]
            return dspy_input
        else:
            raise TypeError(
                f"Unsupported dspy_input type for message preparation: {type(dspy_input)}"

            )
    

    async def __call__(
        self,
        prompt: Optional[str] = None,
        messages: Optional[List[Dict[str, str]]] = None,
        only_completed: bool = True, 
        return_sorted: bool = False, 
        **kwargs, # kwargs passed at call time, e.g., from dspy.Predict
    ) -> List[str]:
        if not prompt and not messages:
            raise ValueError("Either 'prompt' or 'messages' must be provided.")
        if prompt and messages:
            raise ValueError("Provide either 'prompt' or 'messages', not both.")
        if messages is not None:
          dspy_input_content = messages
        elif prompt is not None:
            dspy_input_content = prompt
        else:
            raise ValueError("Either 'prompt' or 'messages' must be provided.")
        # if not prompt and not messages:
        #     raise ValueError("Either 'prompt' or 'messages' must be provided to AsyncCustomGeminiDspyLM.")
        # if prompt and messages:
        #     raise ValueError("Provide either 'prompt' or 'messages' to AsyncCustomGeminiDspyLM, not both.")

        await self.rate_limiter.wait_if_needed() # Use the async rate limiter
        
        dspy_input_content = prompt if prompt is not None else messages
        try:
            messages_for_litellm = self._prepare_litellm_messages_from_dspy_inputs(dspy_input_content)
        except TypeError as e:
            logger.error(f"Error preparing messages for LiteLLM: {e}")
            return [f"[ERROR: Message preparation error - {e}]"]

        # Combine kwargs: instance-level default -> call-level override
        final_call_kwargs = {**self.kwargs, **kwargs}

        current_safety_settings = final_call_kwargs.pop('safety_settings', self.safety_settings)
        
        extra_body = {}
        if current_safety_settings:
            extra_body['safety_settings'] = current_safety_settings

        logger.debug(f"[AsyncCustomGeminiDspyLM] Calling LiteLLM. Model: {self.model}")
        logger.debug(f"Messages for LiteLLM: {messages_for_litellm}")
        logger.debug(f"Final kwargs for LiteLLM: {final_call_kwargs}") # Includes temp, max_tokens etc.
        if extra_body:
            logger.debug(f"Extra body for LiteLLM: {extra_body}")

        try:
            # Use ASYNCHRONOUS acompletion call
            print(messages_for_litellm)
            response_obj = await litellm.acompletion(
                model=self.model,
                messages=messages_for_litellm, # This is List[Dict[role, content]]
                api_key=self.api_key,
                extra_body=extra_body if extra_body else None,
                **final_call_kwargs, # Pass combined kwargs for temp, max_tokens, etc.
            )
            print(response_obj)
            completions = []
            if response_obj.choices:
                for choice in response_obj.choices:
                    # For Gemini, the response text is typically in choice.message.content
                    # LiteLLM should handle transforming Gemini's "parts" to "content" here.
                    if choice.message and choice.message.content is not None:
                        completions.append(choice.message.content)
                    else:
                        finish_reason = getattr(choice, 'finish_reason', "N/A")
                        logger.warning(f"[AsyncCustomGeminiDspyLM] Received a choice with None content. Finish reason: {finish_reason}")
                        completions.append(f"[WARN: Content filtered or empty. Finish Reason: {finish_reason}]")
            else:
                logger.warning("[AsyncCustomGeminiDspyLM] LiteLLM response object had no choices.")
                completions.append("[WARN: No choices in response]")
            
            return completions

        except litellm.RateLimitError as rle:
            logger.error(f"[AsyncCustomGeminiDspyLM] LiteLLM RateLimitError: {rle}.")
            return [f"[ERROR: LiteLLM RateLimitError - {rle}]"]
        except Exception as e:
            logger.error(f"[AsyncCustomGeminiDspyLM] Error during LiteLLM acompletion: {type(e).__name__} - {e}", exc_info=True)
            return [f"[ERROR: {type(e).__name__} - {e}]"]

    async def ARL_basic_request(self, prompt: str, **kwargs) -> List[Dict[str, Any]]:
        # This is primarily for DSPy's internal use if it needs basic_request
        # It should align with what __call__ returns, wrapped as per DSPy's expectation for this method.
        responses_as_strings = await self.__call__(prompt=prompt, **kwargs)
        return [{"text": r} for r in responses_as_strings]
    

