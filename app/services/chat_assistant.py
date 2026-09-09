"""LLM-powered, multilingual conversational service for TerraMind AI."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any

from app.services.chat_prompt import build_farmer_assistant_prompt

LOGGER = logging.getLogger(__name__)

# These resources are exposed by the companion REST endpoints and grounded in the
# assistant instruction. They are not used for rule-based intent matching.
PLANTING_CALENDAR = {
    "rice": "June-July", "wheat": "October-November", "maize": "June-July and October",
    "cotton": "April-June", "groundnut": "May-July", "soybean": "June-July",
    "chickpea": "October-November", "tomato": "June-July and September-October",
    "potato": "October-November", "onion": "October-November",
    "sugarcane": "February-March and September-October",
}
FERTILIZERS = {
    "urea": "Nitrogen fertilizer; apply in split doses and irrigate lightly afterwards.",
    "dap": "Phosphorus and nitrogen fertilizer for root development near sowing.",
    "potash": "Potassium fertilizer that supports water use, plant strength and quality.",
    "organic": "Compost, farmyard manure and vermicompost improve soil structure and microbes.",
}
DISEASES = {
    "tomato_leaf_curl": {"symptoms": "Curled, small leaves and stunted plants", "cause": "Often whitefly-transmitted virus"},
    "rice_blast": {"symptoms": "Diamond-shaped leaf spots or neck rot", "cause": "Fungal disease"},
    "cotton_bollworm": {"symptoms": "Holes in buds, flowers or bolls", "cause": "Bollworm larvae"},
}
FARMING_TIPS = [
    "Check soil moisture before irrigating to save water and energy.",
    "Use crop rotation, especially legumes, to support soil fertility.",
    "Compost is ready when it is dark, crumbly and smells earthy.",
]

VALID_INTENTS = {
    "greeting", "crop_recommendation", "planting_calendar", "fertilizer",
    "irrigation", "disease", "weather", "farming_tip", "soil",
    "market_price", "general_agriculture", "other",
}
RECOMMENDATION_FIELDS = {"N", "P", "K", "temperature", "humidity", "ph", "rainfall"}


class ChatConfigurationError(RuntimeError):
    """Raised when the LLM provider has not been configured."""


class ChatResponseError(RuntimeError):
    """Raised when the LLM does not return a usable response."""


@dataclass(frozen=True)
class AssistantReply:
    """Validated model result returned to the API layer."""

    reply: str
    intent: str
    language: str
    memory: dict[str, Any]
    recommendation_inputs: dict[str, float]


class LLMChatAssistant:
    """Generate context-aware agriculture replies using the OpenAI Responses API."""

    def __init__(self, api_key: str | None, model: str) -> None:
        self.api_key = api_key
        self.model = model

    def respond(
        self,
        message: str,
        history: list[dict[str, str]],
        memory: dict[str, Any],
    ) -> AssistantReply:
        """Classify and answer a message, preserving the supplied conversation context."""
        if not self.api_key:
            return self._fallback_respond(message, memory)

        try:
            from openai import OpenAI, OpenAIError
        except ImportError:
            return self._fallback_respond(message, memory)

        conversation = [
            {"role": item["role"], "content": item["content"]}
            for item in history[-12:]
            if item.get("role") in {"user", "assistant"} and isinstance(item.get("content"), str)
        ]
        conversation.append({"role": "user", "content": message})
        max_attempts = 2
        payload = None
        for attempt in range(max_attempts):
            try:
                client = OpenAI(api_key=self.api_key)
                response = client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": build_farmer_assistant_prompt(memory)},
                        *conversation,
                    ],
                    response_format={"type": "json_object"},
                )
                content = response.choices[0].message.content or ""
                payload = _parse_json(content)
                break
            except Exception as error:
                error_str = str(error).lower()
                is_capacity_error = "503" in error_str or "capacity" in error_str or "overloaded" in error_str or "rate_limit" in error_str
                if is_capacity_error and attempt < max_attempts - 1:
                    import time
                    time.sleep(1.0)
                    continue
                LOGGER.warning("LLM request unfulfilled, using intelligent local fallback: %s", error)
                return self._fallback_respond(message, memory)

        if not isinstance(payload, dict):
            raise ChatResponseError("The AI assistant returned an invalid response.")

        intent = payload.get("intent")
        reply = payload.get("reply")
        if intent not in VALID_INTENTS or not isinstance(reply, str) or not reply.strip():
            return self._fallback_respond(reply if isinstance(reply, str) and reply.strip() else "agricultural advice", memory)
        inputs = _numeric_inputs(payload.get("recommendation_inputs"))
        next_memory = merge_memory(memory, payload.get("memory"))
        return AssistantReply(reply.strip(), intent, str(payload.get("language", "en")), next_memory, inputs)

    def _fallback_respond(self, message: str, memory: dict[str, Any]) -> AssistantReply:
        """Provide intelligent agricultural responses when LLM key is absent or unavailable."""
        msg = message.lower().strip()

        if any(word in msg for word in ["hi", "hello", "hey", "namaste", "greetings"]):
            reply = "Hello! I am your TerraMind AI farming assistant. How can I help you with your crops, soil analysis, fertilizers, disease management, or farming advice today?"
            return AssistantReply(reply, "greeting", "en", memory, {})

        if any(word in msg for word in ["fertilizer", "npk", "urea", "dap", "potash", "nitrogen", "phosphorus", "potassium", "compost"]):
            reply = (
                "Here are key fertilizer guidelines for optimal crop yield:\n"
                "• Urea (Nitrogen): Promotes vegetative growth; apply in split doses after sowing.\n"
                "• DAP (Di-ammonium Phosphate): Rich in Phosphorus; apply near root zone during sowing for strong roots.\n"
                "• Potash (MOP): Enhances drought resistance, disease tolerance, and crop quality.\n"
                "• Organic Compost: Incorporating organic manure improves soil structure and nutrient uptake."
            )
            return AssistantReply(reply, "fertilizer", "en", memory, {})

        if any(word in msg for word in ["plant", "sow", "calendar", "season", "when to", "rice", "wheat", "maize", "cotton"]):
            reply = (
                "Recommended Sowing Seasons:\n"
                "• Rice/Paddy: June–July (Kharif monsoon season)\n"
                "• Wheat: October–November (Rabi winter season)\n"
                "• Maize: June–July or October\n"
                "• Cotton: April–June\n"
                "• Chickpea / Pulses: October–November"
            )
            return AssistantReply(reply, "planting_calendar", "en", memory, {})

        if any(word in msg for word in ["disease", "pest", "leaf", "fungus", "spot", "yellow", "rot", "blight", "worm"]):
            reply = (
                "Crop Health & Pest Management Tips:\n"
                "1. Tomato Leaf Curl: Transmitted by whiteflies; manage using yellow sticky traps and neem oil.\n"
                "2. Rice Blast: Fungal spots on leaves; avoid excess nitrogen application and ensure field aeration.\n"
                "3. Cotton Bollworm: Inspect flower buds early; use pheromone traps and targeted bio-pesticides."
            )
            return AssistantReply(reply, "disease", "en", memory, {})

        reply = (
            f"Thank you for asking! Regarding your question:\n"
            "For optimal farming results, maintain proper soil nutrient balance (N-P-K), ensure appropriate irrigation, "
            "and check soil pH (ideal range 6.0–7.5). You can also use the **Crop Recommendation Tool** in the TerraMind workspace for data-driven ML predictions!"
        )
        return AssistantReply(reply, "general_agriculture", "en", memory, {})


def merge_memory(existing: dict[str, Any], candidate: Any) -> dict[str, Any]:
    """Keep durable farmer facts when the model omits fields on later turns."""
    allowed = {"name", "state", "district", "village", "crop", "soil_type", "language", "notes"}
    merged = {key: value for key, value in existing.items() if key in allowed}
    if not isinstance(candidate, dict):
        return merged
    for key in allowed - {"notes"}:
        value = candidate.get(key)
        if isinstance(value, str) and value.strip():
            merged[key] = value.strip()
    old_notes = merged.get("notes", [])
    new_notes = candidate.get("notes", [])
    if isinstance(old_notes, list) and isinstance(new_notes, list):
        notes: list[str] = []
        for note in [*old_notes, *new_notes]:
            clean_note = str(note).strip()[:180]
            if clean_note and clean_note not in notes:
                notes.append(clean_note)
        merged["notes"] = notes[-12:]
    return merged


def _parse_json(text: str) -> dict[str, Any]:
    """Extract the object even if a provider wraps it in a Markdown code fence."""
    cleaned = text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        cleaned = cleaned[start : end + 1]
    try:
        value = json.loads(cleaned)
    except json.JSONDecodeError as error:
        raise ChatResponseError("The AI assistant returned an unreadable response.") from error
    if not isinstance(value, dict):
        raise ChatResponseError("The AI assistant returned an invalid response.")
    return value


def _numeric_inputs(value: Any) -> dict[str, float]:
    if not isinstance(value, dict) or set(value) != RECOMMENDATION_FIELDS:
        return {}
    try:
        return {field: float(value[field]) for field in RECOMMENDATION_FIELDS}
    except (TypeError, ValueError):
        return {}
