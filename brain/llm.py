"""
GreetBot LLM Interface
=======================
Upgraded Groq LLM wrapper that integrates the full brain stack:
personality, prompt building, conversation management, and emotion detection.
"""

import time
from typing import Optional

from groq import Groq, RateLimitError, APIError

from config import GROQ_API_KEY, LLM_MODEL, LLM_MAX_TOKENS, LLM_TEMPERATURE
from brain.personality import PersonalityEngine
from brain.prompt import PromptBuilder
from brain.emotion import EmotionDetector, Emotion
from brain.conversation import ConversationManager, ConversationSession
from memory.database import Database
from memory.memory import Memory
from utils.helpers import clean_text
from utils.logger import get_logger

log = get_logger(__name__)


class LLM:
    """
    GreetBot's Groq LLM interface with full brain integration.

    Each call to ``ask()`` is context-aware: it pulls from the person's
    long-term memory, injects personality, respects recent conversation
    history, and auto-saves every turn.

    Parameters
    ----------
    db:
        Shared Database instance. If None, a new one is created.
    """

    def __init__(self, db: Optional[Database] = None) -> None:
        if not GROQ_API_KEY:
            log.warning("GROQ_API_KEY is not set — LLM calls will fail!")

        self._client = Groq(api_key=GROQ_API_KEY)
        self._db = db or Database()

        self._personality = PersonalityEngine()
        self._prompt_builder = PromptBuilder(personality=self._personality)
        self._emotion_detector = EmotionDetector()
        self._conversation_mgr = ConversationManager(db=self._db)
        self._global_memory = Memory(db=self._db)

        log.info(f"LLM ready (model={LLM_MODEL})")

    # ── Public API ────────────────────────────────────────────────────────────

    def ask(
        self,
        user_text: str,
        person_name: Optional[str] = None,
        person_id: Optional[str] = None,
        person_count: int = 1,
    ) -> str:
        """
        Ask the LLM a question in the context of a specific person.

        Automatically:
        - Detects user emotion to tune tone
        - Builds a context-rich system prompt with memory & personality
        - Injects recent conversation history
        - Saves the turn to short-term and long-term memory
        - Updates the personality's current emotion state

        Parameters
        ----------
        user_text:
            The user's spoken/typed message.
        person_name:
            Display name of the speaker (None if unknown).
        person_id:
            Database ID of the speaker (None if unknown).
        person_count:
            Total number of visible persons.

        Returns
        -------
        str
            GreetBot's response text, suitable for TTS.
        """
        # ── Detect user emotion ───────────────────────────────────────────────
        user_emotion = self._emotion_detector.detect(user_text)
        self._personality.set_emotion(user_emotion.value)

        # ── Get or create conversation session ────────────────────────────────
        session: Optional[ConversationSession] = None
        facts_summary = ""
        history_text = ""

        if person_name and person_id:
            session = self._conversation_mgr.get_session(
                person_id=person_id,
                person_name=person_name,
            )
            facts_summary = session.get_facts_summary()
            history_text = session.get_history_text(n=5)

        # ── Build system prompt ───────────────────────────────────────────────
        system_prompt = self._prompt_builder.build_system_prompt(
            person_name=person_name,
            facts_summary=facts_summary,
            conversation_history=history_text,
            emotion=user_emotion.value,
            person_count=person_count,
        )

        # ── Assemble messages ─────────────────────────────────────────────────
        messages = [{"role": "system", "content": system_prompt}]

        # Inject recent session turns as message history for continuity
        if session:
            messages.extend(session.get_short_term_messages())

        # Add the current user message
        messages.append({"role": "user", "content": user_text})

        # ── Call Groq ─────────────────────────────────────────────────────────
        reply = self._call_groq(messages)

        # ── Auto-extract and store facts ──────────────────────────────────────
        if session:
            session.add_user_turn(user_text)
            session.add_assistant_turn(reply)
            self._extract_and_remember_facts(user_text, session)

        # ── Update avatar emotion from reply ──────────────────────────────────
        reply_emotion = self._emotion_detector.detect_from_reply(reply)
        self._personality.set_emotion(reply_emotion.value)

        log.info(f"LLM reply ({len(reply)} chars) | emotion={reply_emotion.value}")
        return clean_text(reply)

    def generate_greeting(
        self,
        person_name: str,
        person_id: str,
        visit_count: int,
    ) -> str:
        """
        Generate a personalized greeting for a recognized person.

        Parameters
        ----------
        person_name:
            Name of the recognized person.
        person_id:
            Database ID.
        visit_count:
            Number of times they've visited.

        Returns
        -------
        str
            A warm, personalized greeting.
        """
        session = self._conversation_mgr.get_session(
            person_id=person_id,
            person_name=person_name,
        )
        facts_summary = session.get_facts_summary()

        prompt = self._prompt_builder.build_greeting_prompt(
            person_name=person_name,
            visit_count=visit_count,
            facts_summary=facts_summary,
        )

        system = self._personality.get_system_traits()
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ]

        return clean_text(self._call_groq(messages))

    def generate_registration_message(self) -> str:
        """
        Generate a message asking an unknown person for their name.

        Returns
        -------
        str
            A friendly introduction and name-request.
        """
        prompt = self._prompt_builder.build_registration_prompt("new_person")
        system = self._personality.get_system_traits()
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ]
        return clean_text(self._call_groq(messages))

    def end_person_session(self, person_id: str) -> None:
        """Close the conversation session for a person who left."""
        self._conversation_mgr.end_session(person_id)

    def describe_vision(self, base64_image: str, user_text: str) -> str:
        """
        Query the Llama 3 Vision model with an image.
        """
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": user_text},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}",
                        },
                    },
                ],
            }
        ]
        
        try:
            response = self._client.chat.completions.create(
                model="llama-3.2-11b-vision-preview",
                messages=messages,
                max_tokens=LLM_MAX_TOKENS,
                temperature=LLM_TEMPERATURE,
            )
            reply = response.choices[0].message.content or ""
            log.info(f"Vision reply: {reply[:60]}...")
            return clean_text(reply)
        except Exception as exc:
            log.error(f"Groq Vision API error: {exc}")
            return "I couldn't process the image right now."

    @property
    def current_emotion(self) -> str:
        """Currently active personality emotion."""
        return self._personality.current_emotion

    # ── Internal ──────────────────────────────────────────────────────────────

    def _call_groq(
        self,
        messages: list[dict],
        retries: int = 2,
    ) -> str:
        """
        Send messages to the Groq API and return the reply text.

        Retries on transient errors with exponential backoff.

        Parameters
        ----------
        messages:
            Full message list for the chat completion.
        retries:
            Number of retry attempts on failure.

        Returns
        -------
        str
            Model reply text.
        """
        for attempt in range(retries + 1):
            try:
                response = self._client.chat.completions.create(
                    model=LLM_MODEL,
                    messages=messages,
                    max_tokens=LLM_MAX_TOKENS,
                    temperature=LLM_TEMPERATURE,
                )
                return response.choices[0].message.content or ""

            except RateLimitError:
                wait = 2 ** attempt
                log.warning(f"Groq rate limit — waiting {wait}s (attempt {attempt+1})")
                time.sleep(wait)

            except APIError as exc:
                log.error(f"Groq API error: {exc}")
                if attempt < retries:
                    time.sleep(1)
                else:
                    return "I'm having trouble connecting right now. Please try again in a moment."

            except Exception as exc:
                log.error(f"Unexpected LLM error: {exc}", exc_info=True)
                return "Something went wrong on my end. Give me a moment and try again."

        return "I couldn't get a response. Please try again."

    def _extract_and_remember_facts(
        self,
        user_text: str,
        session: ConversationSession,
    ) -> None:
        """
        Simple pattern-based fact extraction from user messages.

        Looks for common information-sharing phrases and saves them
        to long-term memory automatically.

        Parameters
        ----------
        user_text:
            The user's message to scan.
        session:
            Active conversation session.
        """
        import re

        text = user_text.lower().strip()

        patterns = [
            (r"i(?:'m| am) (?:from|in) ([a-z\s]+)", "city"),
            (r"i(?:'m| am) (?:a|an) ([a-z\s]+(?:student|engineer|developer|"
             r"doctor|teacher|designer|manager|researcher))", "profession"),
            (r"i(?:(?:'m| am) studying|study|go to) ([a-z\s]+(?:university|"
             r"college|institute|school|iit|nit|bits|jntu))", "college"),
            (r"i(?:'m| am) (\d{1,2}) (?:years old|yr)", "age"),
            (r"my (?:favourite|favorite) (?:color|colour) is ([a-z]+)", "favorite_color"),
            (r"i like (?:to )?(.*?)(?:\.|$)", "likes"),
            (r"i (?:love|enjoy) (.*?)(?:\.|$)", "likes"),
        ]

        for pattern, fact_key in patterns:
            match = re.search(pattern, text)
            if match:
                value = match.group(1).strip().title()
                if len(value) > 2:  # Skip junk matches
                    existing = session.recall_fact(fact_key)
                    if existing != value:
                        session.remember_fact(fact_key, value)
                        log.debug(f"Auto-remembered: {fact_key} = {value}")
