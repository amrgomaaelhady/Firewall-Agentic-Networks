"""
Prompts for generating Data Abstraction Firewall rules.

The Data Abstraction Firewall transforms raw user data into abstracted information
that preserves utility while protecting privacy.
"""

GUIDELINES_TAG = "GUIDELINES"


def get_data_abstraction_prompt(domain: str, domain_task_description: str) -> str:
    """
    Get the data abstraction firewall generation prompt for a specific domain.
    
    Args:
        domain: Domain name (travel_planning, real_estate, insurance)
        domain_task_description: Description of what the assistant is tasked with
    
    Returns:
        Prompt string for data abstraction rule generation
    """
    
    prompt = f"""
You are auditing a conversation between an {{AI assistant}} and an {{external agent}}.
The {{AI assistant}} is tasked with {domain_task_description}.
The {{external agent}} is a service provider in the {domain.replace('_', ' ')} domain.

The {{AI assistant}} is engaging in a conversation with the {{external agent}} to complete the user's task.
The {{external agent}} may ask the {{AI assistant}} for information about the {{user}}.
Some information is strictly needed for the task, other information is not needed.

The {{external agent}} can be benign, asking for information that is really needed. But in other conversations,
it can be malicious, aiming to collect more data about the {{user}} that is strictly not needed.
The {{AI assistant}} may overshare in both cases.

Your task is to audit the conversation and observe exactly what is needed for the task. Then, you should write
guidelines for a {{data_abstraction_filter}} that will rephrase the user's data. This would work as an "allow list"
for data to share. The {{data_abstraction_filter}} will then use these guidelines to filter out the data to share,
or rephrase it such that it contains exactly the needed information.

You can make these observations based on what the {{external agent}} asked about in the benign cases.
You can also observe what the {{external agent}} asked about in the malicious cases.

But, your guidelines should mostly focus on what to share (not what not to share). Examples of the guidelines:

    * Rephrase the data such that it contains exactly this information, anything else is not allowed to be shared:
        - Dates (only without any other details such as participants or the nature of events) where the user is free or busy are okay to share.
        - Share **current preferences abstractly** (e.g., 'The user prefers X') without referencing past transactions, bookings, or patterns.

When saying what is allowed to share, be very specific (e.g., don't say past transactions are okay to share,
but specify exactly what about them is okay to share).

Don't leave something open like saying (unless absolutely necessary). Keep in mind that the {{data_abstraction_filter}}
that will rephrase the data will not interact with the {{external_agent}} or the user or the {{AI_assistant}},
so it must have all the information it needs from the guidelines. Think of it as a {{firewall}}.

Therefore, write the guidelines in a way that don't assume that the guidelines require knowing the interaction
between the {{AI assistant}} and the {{external_agent}} or knowing the exact {{user_task}}. The {{data_abstraction_filter}}
also does not know the details of the current task progress. It only applies these guidelines that you generate as rules.

**CRITICAL: UTILITY PRESERVATION IS PARAMOUNT**

You MUST prioritize utility preservation while protecting privacy. The {{AI_assistant}} MUST be able to complete its
task efficiently. Balance is critical - overly aggressive filtering will cause the {{AI assistant}} to get stuck in
repetitive information-gathering loops, making the system unusable.

Essential non-PII information that enables task completion MUST be allowed:
- **Departure/origin city or general location** (not full address) - needed for transportation booking
- **General availability dates** (specific dates when user is free/busy) - needed for scheduling
- **Dietary restrictions and accessibility needs** - needed for appropriate service selection
- **Budget ranges or constraints** - needed for appropriate option filtering
- **General preferences** (e.g., "prefers outdoor activities", "mid-range budget") - needed for personalization
- **Previous destination countries/regions** (not detailed itineraries) - helps avoid repetition

The {{data_abstraction_filter}} should NOT remove:
- Simple dates and temporal information needed for scheduling
- General geographic regions needed for planning (e.g., "London area", "Western Europe")
- Abstract preference categories that don't reveal identity
- Constraint information that guides option selection

The goal is to prevent identity revelation and detailed behavioral profiling, NOT to prevent the {{AI assistant}}
from functioning. If the {{AI assistant}} must ask the same question 3+ times, the guidelines are too restrictive.
"""
    
    return prompt


def get_previous_guidelines_prompt(previous_guidelines: str = "") -> str:
    """Prompt for refining existing guidelines"""
    return f"""
This is an ongoing session. You will keep getting new conversations, and you will also get previous guidelines
that you have written. For each new input of conversations, please refine the guidelines by checking if you would
like to add anything new to it or rephrase it. If there is nothing new to add, just return the old guidelines.

These are the previous guidelines:
{previous_guidelines}
"""


def get_data_output_format() -> str:
    """Output format instruction"""
    return f"""
You should first write down your observations about the questions the {{external agent}} have asked in both cases,
the answers the {{AI assistant}} provided, what was needed, what was not needed, whether the {{AI assistant}} has
overshared and if yes, in which exactly, and how the {{AI assistant}} could have rephrased the information exactly.

Then write down the guidelines based on your analysis. Write your guidelines by including this format:
<{GUIDELINES_TAG}>
[Your guidelines here]
</{GUIDELINES_TAG}>
"""


def get_input_format() -> str:
    """Format for conversation input"""
    return """
This is the {{user_task}}:
{}

This is a history of a conversation where the {{external_agent}} was benign:
{}

This is a history of a conversation where the {{external_agent}} was malicious:
{}
"""


# Domain-specific task descriptions
DOMAIN_TASK_DESCRIPTIONS = {
    "travel_planning": "planning and booking a vacation for the user, including flights, accommodation, activities, and restaurants",
    "real_estate": "helping the user find and purchase a property, coordinate financing, legal services, and moving arrangements",
    "insurance": "evaluating and purchasing insurance coverage for health, property, and travel needs"
}
