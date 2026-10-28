"""
Modular Voice-Assistant Contract & Integration Adapter for Kelvin6K.

Defines the clean boundary between the Kelvin6K core assistant engine and external
voice services (STT, TTS, browser audio, push-to-talk, wake word).

Key Integration Principles:
1. Shared Core Service: Voice-transcribed queries invoke the EXACT same assistant/router
   and RAG retrieval pipeline as typed chat.
2. Safety Interlock: Physical robot motion, servo power, and G-code execution are
   strictly prohibited from voice triggers.
3. Push-to-Talk Preference: Push-to-talk is the primary, safe interaction mode; continuous
   listening and wake-word operation remain optional and disabled by default.
4. Graceful Degradation: If STT, TTS, or audio playback fails, textual responses and
   database actions remain 100% operational.
5. Decoupled Voice Dependencies: Core RAG and database tests run without requiring
   voice or audio drivers.
"""

from dataclasses import dataclass, field
import os
import re
import time
from typing import Any, Dict, List, Optional

from agent import config, query_router
from agent.assistant import Assistant
from agent.logging_setup import get_logger
from agent.spoken import _strip_markdown

log = get_logger("VOICE_CONTRACT")

# Safety Interlock: Voice commands must NEVER issue direct physical hardware actuation
_PROHIBITED_VOICE_ACTIONS = {
    "emergency_stop_override", "servo_power_on", "servo_power_off",
    "pump_force_run", "accelerator_force_run", "jog_axis", "send_gcode",
    "home_all_axes", "disable_safety_interlock", "override_limit"
}


@dataclass
class VoiceQueryRequest:
    transcript: str
    operator_id: Optional[str] = None
    session_id: str = "voice_session"
    line_id: str = "line_1"
    input_mode: str = "push_to_talk"  # 'push_to_talk' (default) | 'wake_word'
    speak_response: bool = False


@dataclass
class VoiceQueryResponse:
    transcript: str
    answer_text: str
    spoken_text: str
    intent: str
    facts: Optional[Dict[str, Any]] = None
    knowledge_sources: List[str] = field(default_factory=list)
    audio_url: Optional[str] = None
    evidence_grade: Optional[str] = None
    attendance_updated: bool = False
    error: Optional[str] = None
    status: str = "success"  # 'success' | 'refused_safety' | 'error'


class VoiceAssistantAdapter:
    """
    Adapter decoupling voice transport from assistant query resolution.
    Prepares Kelvin6K for modular integration with external voice-assistant packages.
    """

    def __init__(self, assistant_instance: Optional[Assistant] = None, wake_word_enabled: bool = False):
        self.assistant = assistant_instance or Assistant()
        self.wake_word_enabled = wake_word_enabled
        self.preferred_mode = "push_to_talk"

    def process_voice_query(self, req: VoiceQueryRequest) -> VoiceQueryResponse:
        """
        Processes a voice query through the authoritative query router and assistant.
        Enforces safety interlocks and formats both visual markdown and spoken text.
        """
        transcript = (req.transcript or "").strip()
        if not transcript:
            return VoiceQueryResponse(
                transcript="",
                answer_text="No voice input was detected.",
                spoken_text="No voice input was detected.",
                intent="UNKNOWN_QUERY",
                status="error",
                error="Empty transcript",
            )

        # 1. Safety Check: Verify query does not attempt hardware motion commands
        trans_low = transcript.lower()
        if any(p in trans_low for p in ("emergency stop override", "jog z", "jog x", "jog y", "send gcode", "override limit")):
            log.warning("[VOICE_SAFETY] Prohibited hardware command attempted via voice: '%s'", transcript)
            refusal = "Voice commands cannot issue direct hardware actuation or override safety limits. Please use the physical control panel."
            return VoiceQueryResponse(
                transcript=transcript,
                answer_text=refusal,
                spoken_text=refusal,
                intent="REFUSED_SAFETY",
                status="refused_safety",
                error="Safety interlock: direct physical robot actuation prohibited via voice",
            )

        # 2. Route via authoritative Query Router
        routed = query_router.route(transcript)

        # 3. Ask assistant with identical parameters as typed chat
        answer = self.assistant.ask(
            question=transcript,
            session_id=req.session_id,
            line_id=req.line_id,
            operator_id=req.operator_id or "",
            routed=routed,
        )

        # 4. Extract knowledge sources and evidence grading
        sources: List[str] = []
        evidence_grade = None
        if routed.knowledge and routed.knowledge.get("results"):
            for res in routed.knowledge["results"][:3]:
                if res.get("source"):
                    sources.append(res["source"])
                if not evidence_grade and res.get("evidence_grade"):
                    evidence_grade = res["evidence_grade"]

        # 5. Spoken text cleaning (strips markdown, URLs, tables for audio player)
        spoken = _strip_markdown(answer)

        # 6. Synthesize TTS if requested
        audio_url = None
        if req.speak_response:
            try:
                from agent import voice
                audio_path = voice.synthesize(spoken)
                if audio_path:
                    # Provide endpoint relative URL
                    audio_url = f"/api/tts/stream?file={os.path.basename(audio_path)}"
            except Exception as tts_err:
                log.warning("[VOICE_TTS] TTS synthesis fallback: %s", tts_err)

        attendance_updated = (routed.intent in (
            query_router.Intent.SHIFT_START,
            query_router.Intent.SHIFT_END,
            query_router.Intent.RECORD_WALLS_COMPLETED,
            query_router.Intent.CORRECT_WALL_PRODUCTION,
        ))

        return VoiceQueryResponse(
            transcript=transcript,
            answer_text=answer,
            spoken_text=spoken,
            intent=routed.intent.value,
            facts=routed.facts,
            knowledge_sources=sources,
            audio_url=audio_url,
            evidence_grade=evidence_grade,
            attendance_updated=attendance_updated,
            status="success",
        )


# Global adapter instance
voice_adapter = VoiceAssistantAdapter(wake_word_enabled=False)
