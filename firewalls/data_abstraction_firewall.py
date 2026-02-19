"""
Data abstraction firewall for filtering sensitive information from environment responses.
Prevents leakage of PII and confidential user data to external agents.
"""

from typing import Optional
from model import LLM


DATA_ABSTRACTION_SYSTEM_PROMPT = """You are a privacy firewall that filters sensitive information from user environment data before it is shared with external agents.

Your task is to apply the provided confidentiality guidelines to redact or abstract sensitive information while preserving utility for the external agent to complete their task.

**Guidelines for filtering:**
1. Follow the specific confidentiality rules provided in the guidelines
2. Remove or abstract personally identifiable information (PII)
3. Generalize sensitive details while maintaining context
4. Preserve information necessary for the external agent to provide useful assistance
5. Be consistent in your abstraction approach across multiple turns

Return only the filtered/abstracted version of the input, without explanations or additional commentary."""

DATA_ABSTRACTION_TURN_TEMPLATE = """**Confidentiality Guidelines:**
{guidelines}

**Original Environment Response:**
{environment_response}

**Your Task:**
Apply the confidentiality guidelines to filter the environment response. Return only the filtered version."""


class DataAbstractionFirewall:
    """
    Data abstraction firewall that filters sensitive information from environment.
    Uses confidentiality guidelines to determine what information to protect.
    """

    def __init__(
        self,
        guidelines_text: str,
        llm_instance: LLM
    ):
        """
        Initialize data abstraction firewall.
        
        Args:
            guidelines_text: Text containing confidentiality filtering guidelines
            llm_instance: LLM instance to use for filtering
        """
        self.guidelines_text = guidelines_text
        self.llm_instance = llm_instance

    def apply_firewall(self, environment_response: str) -> Optional[str]:
        """
        Apply data abstraction firewall to environment response.
        Filters sensitive information according to guidelines.
        
        Args:
            environment_response: Original response from user environment
            
        Returns:
            Filtered response with sensitive data abstracted, or None if filtering fails
        """
        # Build the firewall prompt
        turn_prompt = DATA_ABSTRACTION_TURN_TEMPLATE.format(
            guidelines=self.guidelines_text,
            environment_response=environment_response
        )
        
        messages = [
            {"role": "system", "content": DATA_ABSTRACTION_SYSTEM_PROMPT},
            {"role": "user", "content": turn_prompt}
        ]
        
        try:
            # Get LLM filtering
            filtered_response = self.llm_instance.call_model(messages)
            
            if not filtered_response:
                print(f"[Data Abstraction Firewall] LLM call failed")
                return None
            
            return filtered_response.strip()
            
        except Exception as e:
            print(f"[Data Abstraction Firewall] Error: {str(e)}")
            return None
