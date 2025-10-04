"""
Prompts for Web Crawler Agent
"""
# This file can be extended later with NLP prompts for content analysis
# For now, it's a placeholder for future enhancements

WEB_CRAWLER_PROMPTS = {
    "analyze_content": """
    Analyze the following web content and extract key information:

    Content: {content}

    Please provide:
    1. Main topics and themes
    2. Key entities (people, organizations, locations)
    3. Important dates and numbers
    4. Overall sentiment and tone
    5. Action items or calls to action

    Respond in JSON format.
    """,

    "summarize_page": """
    Summarize the following web page content in 3-5 sentences:

    Title: {title}
    Content: {content}

    Focus on the main purpose, key points, and any important details.
    """,

    "extract_contact_info": """
    Extract any contact information from the following content:

    Content: {content}

    Look for:
    - Email addresses
    - Phone numbers
    - Physical addresses
    - Social media handles
    - Website URLs

    Return as JSON.
    """
}
