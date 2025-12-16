"""
Voice AI service integrating Whisper STT, Azure Cognitive Services TTS, and sentiment analysis.
"""

from __future__ import annotations

import io
import logging
import os
from dataclasses import dataclass
from typing import Optional

import numpy as np

try:
    import torch
    import whisper
except ImportError as exc:  # pragma: no cover
    raise RuntimeError("whisper (with PyTorch) is required for speech-to-text") from exc

try:
    from azure.cognitiveservices.speech import AudioDataStream, SpeechConfig, SpeechSynthesizer, SpeechSynthesisOutputFormat
except ImportError as exc:  # pragma: no cover
    raise RuntimeError("azure-cognitiveservices-speech package is required for TTS") from exc

try:
    from textblob import TextBlob
except ImportError as exc:  # pragma: no cover
    raise RuntimeError("TextBlob is required for sentiment analysis") from exc

LOGGER = logging.getLogger("voice.azure_voice_service")


@dataclass
class VoiceResponse:
    transcript: str
    sentiment: float
    synthesized_audio_wav: bytes
    sentiment_label: str


class AzureVoiceService:
    """Provides end-to-end voice understanding and generation capabilities."""

    def __init__(
        self,
        whisper_model: str = "base",
        azure_region: Optional[str] = None,
        azure_key: Optional[str] = None,
        voice_name: str = "en-US-JennyNeural",
    ) -> None:
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.stt_model = whisper.load_model(whisper_model, device=self.device)
        LOGGER.info("Loaded Whisper model '%s' on device '%s'", whisper_model, self.device)

        key = azure_key or os.getenv("AZURE_SPEECH_KEY")
        region = azure_region or os.getenv("AZURE_SPEECH_REGION")
        if not key or not region:
            raise RuntimeError("Azure speech key/region not configured in environment variables")
        self.speech_config = SpeechConfig(subscription=key, region=region)
        self.speech_config.speech_synthesis_voice_name = voice_name
        self.speech_config.set_speech_synthesis_output_format(SpeechSynthesisOutputFormat.Riff16Khz16BitMonoPcm)
        self.voice_name = voice_name

    # ------------------------------------------------------------------ #
    def transcribe(self, audio_buffer: bytes, language: str = "en") -> str:
        audio = whisper.load_audio(io.BytesIO(audio_buffer))
        audio = whisper.pad_or_trim(audio)
        mel = whisper.log_mel_spectrogram(audio).to(self.device)
        options = whisper.DecodingOptions(language=language, fp16=self.device == "cuda", without_timestamps=True)
        result = whisper.decode(self.stt_model, mel, options)
        LOGGER.debug("Transcription complete (avg log prob %.4f)", result.avg_logprob)
        return result.text.strip()

    @staticmethod
    def _sentiment_score(text: str) -> float:
        return float(TextBlob(text).sentiment.polarity)

    def synthesize(self, text: str) -> bytes:
        synthesizer = SpeechSynthesizer(speech_config=self.speech_config, audio_config=None)
        result = synthesizer.speak_text_async(text).get()
        if result.audio_data is None:
            raise RuntimeError(f"Azure TTS synthesis failed: {result.reason}")
        stream = AudioDataStream(result)
        data = stream.readall()
        LOGGER.debug("Synthesis complete (%d bytes)", len(data))
        return data

    def respond(self, audio_buffer: bytes) -> VoiceResponse:
        transcript = self.transcribe(audio_buffer)
        sentiment = self._sentiment_score(transcript)
        sentiment_label = "positive" if sentiment >= 0.15 else "negative" if sentiment <= -0.15 else "neutral"
        response_text = self._generate_response(transcript, sentiment_label)
        audio = self.synthesize(response_text)
        return VoiceResponse(
            transcript=transcript,
            sentiment=sentiment,
            synthesized_audio_wav=audio,
            sentiment_label=sentiment_label,
        )

    @staticmethod
    def _generate_response(transcript: str, sentiment_label: str) -> str:
        if sentiment_label == "negative":
            prefix = "I hear your concern. Let me help right away."
        elif sentiment_label == "positive":
            prefix = "Great to hear! I'll keep monitoring."
        else:
            prefix = "Thanks for the update."
        return f"{prefix} Regarding your message: {transcript}"