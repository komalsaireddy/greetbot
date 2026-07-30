"""
GreetBot Vision Skill
=====================
Skill for identifying if a user is asking the bot to look at something.
"""

def is_vision_query(text: str) -> bool:
    """Detect if the user is asking the bot to 'see' or 'look' at something."""
    lower = text.lower()
    triggers = [
        "what do you see",
        "what am i holding",
        "describe the scene",
        "look at this",
        "can you see",
        "what is this",
        "describe what you see",
    ]
    return any(t in lower for t in triggers)
