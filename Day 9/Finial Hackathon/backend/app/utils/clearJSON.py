import re

def clean_json_response(response_text: str) -> str:
    """Clean and extract JSON from Gemini response"""
    cleaned = response_text.strip()
    cleaned = re.sub(r'```json\s*', '', cleaned)
    cleaned = re.sub(r'```\s*', '', cleaned)
    start = cleaned.find('{')
    end = cleaned.rfind('}') + 1
    if start != -1 and end > start:
        return cleaned[start:end]
    return cleaned