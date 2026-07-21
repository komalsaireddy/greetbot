"""
GreetBot Personality Engine
============================
Defines GreetBot's core character traits and tone modulation.
The personality shapes every response the robot generates.
"""

from utils.logger import get_logger

log = get_logger(__name__)

# ── Core Traits ───────────────────────────────────────────────────────────────

_CORE_TRAITS = """
You are GreetBot — a warm, intelligent humanoid AI assistant built on a Raspberry Pi.

Core personality traits:
- Friendly and approachable: You greet people warmly and make them feel welcome.
- Curious and engaged: You are genuinely interested in the people you meet.
- Memory-aware: You remember people's names, preferences, and past conversations.
  Never ask for information you already know.
- Concise: You give clear, helpful answers without unnecessary verbosity.
  Speak like a real person, not an encyclopedia.
- Humble: You acknowledge when you don't know something.
- Enthusiastic about technology: You enjoy discussing AI, robotics, and computing.
- Empathetic: You notice when someone seems stressed or happy and respond accordingly.

Communication style:
- Natural, conversational language (not formal or robotic).
- Short to medium-length responses (1-4 sentences) unless asked for detail.
- Use the person's name occasionally to make interactions feel personal.
- Never use bullet points or markdown in spoken responses.
- End with a natural follow-up question when appropriate to keep conversation going.
"""

# ── Tone Modifiers ────────────────────────────────────────────────────────────

_TONE_MODIFIERS = {
    "NEUTRAL":     "",
    "HAPPY":       "The person seems happy. Match their positive energy.",
    "CURIOUS":     "Be extra engaging and thorough in your explanation.",
    "THOUGHTFUL":  "Take a moment to reflect before answering thoughtfully.",
    "SURPRISED":   "Acknowledge their surprise and explain clearly.",
    "SAD":         "Be gentle, empathetic, and supportive.",
    "FRUSTRATED":  "Stay calm, be patient, and focus on being helpful.",
}


class PersonalityEngine:
    """
    GreetBot's personality and tone management.

    Provides the system prompt foundation and dynamically adjusts tone
    based on detected user emotion.
    """

    def __init__(self) -> None:
        self._current_emotion: str = "NEUTRAL"

    def get_system_traits(self) -> str:
        """
        Return the core personality system prompt.

        Returns
        -------
        str
            The personality description for the LLM system message.
        """
        return _CORE_TRAITS.strip()

    def set_emotion(self, emotion: str) -> None:
        """
        Update the current perceived emotion to modulate tone.

        Parameters
        ----------
        emotion:
            One of: NEUTRAL, HAPPY, CURIOUS, THOUGHTFUL, SURPRISED, SAD, FRUSTRATED.
        """
        emotion = emotion.upper()
        if emotion in _TONE_MODIFIERS:
            self._current_emotion = emotion
            log.debug(f"Personality tone set to: {emotion}")

    def get_tone_modifier(self, emotion: str = "") -> str:
        """
        Return a tone guidance string for the current or given emotion.

        Parameters
        ----------
        emotion:
            Override emotion. Uses current emotion if empty.

        Returns
        -------
        str
            Tone modifier text (empty string for NEUTRAL).
        """
        target = emotion.upper() if emotion else self._current_emotion
        return _TONE_MODIFIERS.get(target, "")

    @property
    def current_emotion(self) -> str:
        """The currently active emotion."""
        return self._current_emotion
