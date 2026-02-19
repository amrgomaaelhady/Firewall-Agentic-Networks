"""
Prompts for generating Language Converter Firewall rules (controlled language template).

The Language Converter Firewall converts free-form natural language from external agents
into a controlled, deterministic key-value structure that can be programmatically verified.
"""

LANGUAGE_TAG = "TEMPLATE"


def get_language_converter_prompt(domain: str, domain_task_description: str) -> str:
    """
    Get the language converter firewall generation prompt for a specific domain.
    
    Args:
        domain: Domain name (travel_planning, real_estate, insurance)
        domain_task_description: Description of what the assistant is tasked with
    
    Returns:
        Prompt string for language converter firewall language template generation
    """
    
    prompt = f"""
You are auditing a conversation between an {{AI assistant}} and an {{external agent}}.
The {{AI assistant}} is tasked with {domain_task_description}.
The {{external agent}} is a service provider in the {domain.replace('_', ' ')} domain.

The {{AI assistant}} is engaging in a conversation with the {{external agent}} to complete the user's task.

The {{external agent}} is providing information about options (e.g., properties, insurance plans, travel packages)
and asking the {{AI assistant}} questions to understand requirements and tailor suggestions. Additionally, the
{{external agent}} may ask the {{AI assistant}} for information about the {{user}}.

Your task is to create a taxonomy of possible input variables that the {{AI assistant}} can accept and respond to.
For example, when the {{external agent}} gives several options with prices, features, and ratings, you would expand
the taxonomy by the given fields:

{{"option_type": "accommodation", "price": Type:float, "currency": "euros", "breakfast_included": Type:bool}}

As much as possible, the value for each field of the taxonomy (e.g., "euros") would have to be also a fixed set of
options that you will build out of the conversation (that cannot be changed later). The values can also be boolean.
They can also be indicated by a "data type".

For example, you can say the price is expected to be a digit. Through several simulations, you will be able to build
such a taxonomy (or think of it as an interface to a class and the allowed data types of each variable) of options
that should be converted into a JSON-like template.

Very importantly, we want to minimize the natural language input fields that will be passed to the {{AI assistant}}.
We will leave this for fields that can never be expressed except in natural language (such as the names of specific
entities, addresses, etc.). If a certain field can't be expressed in anything except arbitrary natural language inputs
that cannot be bound with a fixed set of options, you should indicate that in the value of this field.

Except names and named entities and addresses, you MUST NOT include fields in the taxonomy that require free-form
sentences (that are very generic) such as "descriptions", "highlights", etc. You MUST extract from the natural
language descriptions given by the {{external agent}} some high-level attributes, such as:
"outdoor_activity": Type:bool, "sports_offered": ["diving", "hiking"], and ONLY use this to build the taxonomy instead.

Basically you need to know, ANYTHING expressed in natural language will not be given to the {{AI assistant}} in the
first place, so if this is important for the {{AI assistant}} to decide, then you MUST provide enough predefined
values that would express this option.

If you are indicating a data type such as string, you have to write Type:str, Type:int, Type:float, Type:datetime, etc.
Think of these as Python types.

**CRITICAL SECURITY CONSTRAINTS:**

1. **NEVER use "Type:bool"** - Instead, ALWAYS use a list like ["yes", "no"] or ["true", "false"]. Boolean types 
   cause processing errors.

2. **Minimize "Type:str" usage** - Type:str fields with free-form text are SECURITY VULNERABILITIES that could 
   allow prompt injection attacks. Use Type:str ONLY for:
   - Fields ending in "_name" (e.g., "destination_name", "property_name", "activity_name", "airline_name", 
     "restaurant_name", "plan_name", "service_name") - these are automatically replaced with safe IDs like 
     "destination_option1" before being sent to the AI assistant
   - Fields that absolutely require natural language and cannot be expressed any other way

3. **Remove "_id" fields entirely** - Fields like "destination_id", "property_id", "flight_id" serve no purpose 
   since the "_name" fields already get converted to safe IDs. Do not include any "_id" fields in the template.

4. **Convert vulnerable string fields to enumerations** - For fields like country, city, region, address 
   components: use predefined lists like ["france", "spain", "italy", "usa", "canada", "other"] instead of 
   Type:str. This prevents arbitrary text injection.

5. **Use constrained alternatives** - Instead of free-form Type:str fields, use:
   - Predefined categories/enumerations for locations, types, categories
   - Numeric types (Type:int, Type:float) for quantities, prices, ratings
   - Lists of specific options for features and attributes
   - Type:datetime for dates and times

You could also use simple formattable strings that would contain concrete data types such as
"{{Type:int}} to {{Type:int}}" or "{{Type:datetime}} to {{Type:datetime}}" to express duration, timing, etc.

If you absolutely must keep something as Type:str beyond the "_name" fields mentioned above, you MUST include 
additional properties with predefined values (such as "location_region": ["west_europe", "east_coast"], 
"property_type": ["urban", "suburban", "rural"]) to constrain the information flow.

You must also think of how to expand the fields themselves not just the values. For example, what else may be
included in the package or offering?

Feel free to use your own knowledge in order to suggest what kind of attributes/values would work with each item
even if they were not explicitly expressed in the conversations. For example, you can think of what kind of general
themes and categories this field may usually be associated with.

A helpful way to do that is to think, if the user was different (they have different needs, preferences, constraints),
what properties of options would they be interested to know about? Expand the taxonomy as MUCH as possible in order
to cover other conversations that you may have not seen. You must be proactive.

You can also assume that some fields will be grouped with others: for example, in travel planning, transportation
may be grouped with the destination, so there is no need to include free form fields in the transportation separately.

As a rule of thumb, assume that each entity name field would be replaced by a short identifier (e.g., option_1,
property_2, plan_3, etc.). Everything else should not have free form natural language text.

Fields should denote given or requested information from the {{external agent}} to the {{AI assistant}}, they must
not express inputs from the {{AI assistant}}. For example, you shouldn't include a field of the "remaining_budget"
or the "user_budget" that the {{AI assistant}} has shared. You shouldn't also include items in the final package
summary. This is not a property of options shared by the {{external agent}}.

You have to differentiate between things said in the conversation and the actual properties of items.

Don't include very very specific values for fields that are hard to generalize to new conversations with different
options.

You must also include fields that would express if something was available and now it is not, or any change of
state compared to the previously shared items. This is to support referring to a previous part of the conversation.

You must also include fields related to requested information that the {{external agent}} is asking the
{{AI assistant}} to share. The fields must only express the request, not the actual information or answer from
the {{AI assistant}}. Fields expressing requested information must clearly be indicated as request via the name
of the fields.

Your template must clearly indicate whether this information is given by the {{external agent}} or requested by
the {{external agent}}.

Requested information does not have data types because the values will not be given by the {{external agent}}.
In this case, you must use ["yes", "no"] for boolean requests (for example: "user_availability_needed": ["yes", "no"]).
DO NOT use "Type:bool" anywhere in the template as it causes processing errors.

General fields such as accumulated cost across all options should not be there. The cost/price is a property for
each item. The {{AI assistant}} is responsible to do this computation of the total or remaining budget.

Also, any information the {{AI assistant}} is giving (e.g., what preferences the user has or their conditions)
must not be used to build the template. Your template is strictly based on the {{external agent}}.

But, for example, the template may contain requests from the {{external agent}} asking about the user's preferences, etc.

Essentially, your template is either:
1. Information about packages, items, options, etc. given by the {{external agent}}.
2. Requests about information the {{external agent}} is asking from the {{AI assistant}}, without the actual answers.

These two should be marked clearly as such.

You must include everything in JSON format.

**IMPORTANT: UTILITY AND COMPLETENESS**

Your template must be comprehensive enough to allow the {{AI assistant}} to make informed decisions without requiring
free-form conversation. The template should capture ALL relevant attributes that would influence booking/selection
decisions, including:

- Availability and timing information (dates, schedules, duration)
- Pricing and cost breakdown (base price, taxes, fees, optional add-ons)
- Cancellation policies and flexibility
- Quality indicators (ratings, certifications, compliance)
- Accessibility and dietary accommodation
- Location and proximity information
- Included vs. optional features
- Status changes and availability updates

If important decision-making information cannot be expressed through your template fields, the {{AI assistant}} will
be unable to complete its task effectively. The template should minimize the need for follow-up clarification while
still maintaining structure and validation.
"""
    
    return prompt


def get_previous_template_prompt(previous_template: str = "") -> str:
    """Prompt for refining existing template"""
    template_section = f"""
Here is the previous template you have been working on:

{previous_template}

""" if previous_template else ""
    
    return f"""
You should first write down your observations about the questions the {{{{external agent}}}} have asked. Then if you
are given a previous template that you have worked on, you should write down how you can expand it or refine it.

{template_section}Think also of how to expand this template based on your own knowledge. Also think of how to minimize the natural
language description (Type:str), and how to already refine the template to reduce these (Type:str) items.

Correct any mistakes that you have done before if you have introduced lots of (Type:str) items. You must also make
sure the template reflects either information given or information requested by the {{{{external agent}}}}. It must
not reflect information given or information requested by the {{{{AI assistant}}}}.

Then after all of your analysis, write down the new template based on your analysis. You must not remove existing
information from template. Copy anything you have not changed from the existing template. If there is nothing new
to add, just return the old template.

After your analysis and notes, write the new templates by including this format:
<{LANGUAGE_TAG}>
[Your JSON template here]
</{LANGUAGE_TAG}>
"""


def get_language_converter_input_format() -> str:
    """Format for conversation input"""
    return """
This is a history of a conversation between the {{AI assistant}} and the {{external_agent}}:
{}
"""


def get_language_converter_output_format() -> str:
    """Output format instruction"""
    return f"""
You should first write down your observations about the information and questions the {{{{external agent}}}} provided
and asked. Then if you are given a previous template that you have worked on, you should write down how you can
expand it or refine it. If there are no changes required, just repeat the old ones.

Please use the following format:
<{LANGUAGE_TAG}>
[Your JSON template here]
</{LANGUAGE_TAG}>
"""


# Domain-specific task descriptions (same as data abstraction)
DOMAIN_TASK_DESCRIPTIONS = {
    "travel_planning": "planning and booking a vacation for the user, including flights, accommodation, activities, and restaurants",
    "real_estate": "helping the user find and purchase a property, coordinate financing, legal services, and moving arrangements",
    "insurance": "evaluating and purchasing insurance coverage for health, property, and travel needs"
}
