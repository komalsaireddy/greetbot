"""
GreetBot Prompt Builder
========================
Constructs context-rich system and user prompts for the LLM.
Aggregates personality, memory, and session context into a clean
prompt that gives the LLM everything it needs to respond well.
"""

from datetime import datetime
from typing import Optional

from brain.personality import PersonalityEngine
from utils.helpers import current_time_greeting
from utils.logger import get_logger

log = get_logger(__name__)


class PromptBuilder:
    """
    Builds LLM prompts by combining personality, memory, and context.

    Designed to produce concise, structured prompts that keep the LLM
    focused without wasting tokens.
    """

    def __init__(self, personality: Optional[PersonalityEngine] = None) -> None:
        self._personality = personality or PersonalityEngine()

    def build_system_prompt(
        self,
        person_name: Optional[str] = None,
        facts_summary: str = "",
        conversation_history: str = "",
        emotion: str = "NEUTRAL",
        person_count: int = 1,
    ) -> str:
        """
        Build the system message for the LLM.

        This is sent as the ``"system"`` role message and shapes all
        subsequent responses.

        Parameters
        ----------
        person_name:
            Name of the current speaker (None if unknown).
        facts_summary:
            Formatted facts from long-term memory.
        conversation_history:
            Recent past conversations as text.
        emotion:
            Detected emotion of the current user.
        person_count:
            Number of people currently visible to the camera.

        Returns
        -------
        str
            Complete system prompt string.
        """
        parts: list[str] = []

        # 1. Core personality
        parts.append(self._personality.get_system_traits())

        # 2. Current time context
        now = datetime.now()
        greeting = current_time_greeting()
        parts.append(
            f"\nCurrent time: {now.strftime('%A, %B %d %Y at %I:%M %p')}. "
            f"Use '{greeting}' as a greeting if appropriate."
        )

        # 3. Person context
        if person_name:
            parts.append(f"\nYou are speaking with: {person_name}.")
        else:
            parts.append("\nYou are speaking with an unknown person. "
                         "Introduce yourself and ask for their name.")

        # 4. Person count
        if person_count > 1:
            parts.append(f"\nThere are {person_count} people visible, "
                         "but you are currently responding to one of them.")

        # 5. Long-term memory / facts
        if facts_summary and facts_summary.strip() != "No stored information.":
            parts.append(
                f"\nWhat you know about {person_name or 'this person'}:\n{facts_summary}"
            )

        # 6. Past conversation context
        if conversation_history and conversation_history.strip() != "No previous conversations.":
            parts.append(
                f"\nRecent past conversations with {person_name or 'this person'}:\n"
                f"{conversation_history}"
            )

        # 7. Tone modifier from emotion
        tone = self._personality.get_tone_modifier(emotion)
        if tone:
            parts.append(f"\nTone guidance: {tone}")

        # 8. Critical instruction
        parts.append(
            "\nIMPORTANT: Never ask for information you already know about this person. "
            "Respond naturally and conversationally. "
            "Do NOT use bullet points, markdown, or lists in your response."
        )

        return "\n".join(parts)

    def build_registration_prompt(self, person_id: str) -> str:
        """
        Build a prompt for when an unknown person needs to be registered.

        Returns
        -------
        str
            A prompt guiding the bot to ask for the person's name.
        """
        return (
            f"You just saw a new person you don't recognize (ID: {person_id}). "
            "Greet them warmly, introduce yourself as GreetBot, and politely ask "
            "for their name so you can remember them for future visits. "
            "Keep it natural and friendly, not robotic."
        )

    def build_greeting_prompt(
        self,
        person_name: str,
        visit_count: int,
        facts_summary: str = "",
    ) -> str:
        """
        Build a personalized greeting prompt for a returning person.

        Parameters
        ----------
        person_name:
            Name of the returning person.
        visit_count:
            How many times they've visited before.
        facts_summary:
            Known facts about them.

        Returns
        -------
        str
            Prompt asking the bot to generate a natural greeting.
        """
        is_first = visit_count <= 1
        visit_context = (
            "This is their first visit." if is_first
            else f"This is visit number {visit_count}. Welcome them back warmly."
        )

        memory_note = ""
        if facts_summary and facts_summary.strip() != "No stored information.":
            memory_note = (
                f" You remember the following about them: {facts_summary}. "
                "Reference something specific if it feels natural."
            )

        return (
            f"You just recognized {person_name} on camera. "
            f"{visit_context}{memory_note} "
            "Generate a warm, natural greeting. Keep it to 1-2 sentences."
        )
