"""
TTS (Text-to-Speech) output module.

Provides abstract interface for text-to-speech with support for:
- Fish Speech (priority - low latency, voice cloning)
- Edge TTS (free, good quality)
- OpenAI TTS

Features:
- Streaming synthesis for low latency
- Hard interruption support
- Voice configuration

Usage:
    # Create TTS output
    tts = FishSpeechTTS(voice_id="default")

    # Speak text
    await tts.speak("Hello, world!")

    # Stream text as it arrives
    async for chunk in text_stream:
        await tts.stream(chunk)
    await tts.flush()

    # Interrupt current speech
    await tts.interrupt()
"""

import asyncio
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, AsyncIterator

from kohakuterrarium.modules.output.base import OutputModule
from kohakuterrarium.utils.logging import get_logger

logger = get_logger(__name__)


class TTSState(Enum):
    """TTS module state."""

    IDLE = "idle"
    SPEAKING = "speaking"
    BUFFERING = "buffering"
    ERROR = "error"


@dataclass
class TTSConfig:
    """
    Configuration for TTS modules.

    Attributes:
        voice_id: Voice identifier (varies by backend)
        language: Target language code
        speed: Speaking speed multiplier (1.0 = normal)
        pitch: Pitch adjustment (-1.0 to 1.0)
        volume: Volume level (0.0 to 1.0)
        sample_rate: Output sample rate
        streaming: Enable streaming synthesis
        buffer_size: Text buffer size before synthesis
    """

    voice_id: str = "default"
    language: str = "en"
    speed: float = 1.0
    pitch: float = 0.0
    volume: float = 1.0
    sample_rate: int = 24000
    streaming: bool = True
    buffer_size: int = 50  # Characters before starting synthesis
    options: dict[str, Any] = field(default_factory=dict)


@dataclass
class AudioChunk:
    """
    Audio data chunk from TTS.

    Attributes:
        data: Raw audio bytes
        sample_rate: Audio sample rate
        channels: Number of audio channels
        is_final: Whether this is the last chunk
        text: Text that was synthesized (for logging)
    """

    data: bytes
    sample_rate: int = 24000
    channels: int = 1
    is_final: bool = False
    text: str = ""


class TTSModule(OutputModule, ABC):
    """
    Abstract base class for TTS output modules.

    Subclasses must implement:
    - _synthesize(): Convert text to audio
    - _play_audio(): Play audio data
    - _stop_playback(): Stop current playback

    The base class handles:
    - State management
    - Text buffering for streaming
    - Interruption logic
    """

    def __init__(self, config: TTSConfig | None = None):
        """
        Initialize TTS module.

        Args:
            config: TTS configuration
        """
        self.config = config or TTSConfig()
        self._state = TTSState.IDLE
        self._running = False
        self._text_buffer = ""
        self._interrupted = False

    @property
    def state(self) -> TTSState:
        """Get current TTS state."""
        return self._state

    @property
    def is_speaking(self) -> bool:
        """Check if currently speaking."""
        return self._state == TTSState.SPEAKING

    async def start(self) -> None:
        """Start the TTS module."""
        if self._running:
            return

        self._running = True
        self._state = TTSState.IDLE
        await self._initialize()
        logger.info("TTS started", voice=self.config.voice_id)

    async def stop(self) -> None:
        """Stop the TTS module."""
        if not self._running:
            return

        await self.interrupt()
        self._running = False
        self._state = TTSState.IDLE
        await self._cleanup()
        logger.info("TTS stopped")

    async def speak(self, text: str) -> None:
        """
        Speak complete text.

        Synthesizes and plays the entire text.

        Args:
            text: Text to speak
        """
        if not text.strip():
            return

        self._interrupted = False
        self._state = TTSState.SPEAKING

        try:
            async for chunk in self._synthesize(text):
                if self._interrupted:
                    break
                await self._play_audio(chunk)

            if not self._interrupted:
                logger.debug("TTS completed", text_length=len(text))
        except Exception as e:
            logger.error("TTS speak error", error=str(e))
            self._state = TTSState.ERROR
        finally:
            if not self._interrupted:
                self._state = TTSState.IDLE

    async def stream(self, text_chunk: str) -> None:
        """
        Stream text for synthesis.

        Buffers text and synthesizes when buffer is full or on punctuation.

        Args:
            text_chunk: Text chunk to add to buffer
        """
        self._text_buffer += text_chunk
        self._state = TTSState.BUFFERING

        # Check if we should synthesize
        should_synthesize = len(
            self._text_buffer
        ) >= self.config.buffer_size or self._ends_with_sentence(self._text_buffer)

        if should_synthesize and self._text_buffer.strip():
            text = self._text_buffer
            self._text_buffer = ""
            await self.speak(text)

    async def flush(self) -> None:
        """
        Flush remaining buffered text.

        Call after streaming is complete to speak any remaining text.
        """
        if self._text_buffer.strip():
            text = self._text_buffer
            self._text_buffer = ""
            await self.speak(text)

    async def interrupt(self) -> None:
        """
        Interrupt current speech (hard cut).

        Immediately stops playback.
        """
        if self._state != TTSState.SPEAKING:
            return

        self._interrupted = True
        await self._stop_playback()
        self._text_buffer = ""
        self._state = TTSState.IDLE
        logger.debug("TTS interrupted")

    def _ends_with_sentence(self, text: str) -> bool:
        """Check if text ends with sentence-ending punctuation."""
        text = text.rstrip()
        if not text:
            return False
        return text[-1] in ".!?。！？"

    # === OutputModule interface ===

    async def write(self, text: str) -> None:
        """Write text to TTS (implements OutputModule)."""
        await self.stream(text)

    async def write_stream(self, chunk: str) -> None:
        """Write streaming chunk to TTS (implements OutputModule)."""
        await self.stream(chunk)

    # === Abstract methods for subclasses ===

    async def _initialize(self) -> None:
        """Initialize TTS backend. Override if needed."""
        pass

    async def _cleanup(self) -> None:
        """Cleanup TTS backend. Override if needed."""
        pass

    @abstractmethod
    async def _synthesize(self, text: str) -> AsyncIterator[AudioChunk]:
        """
        Synthesize text to audio.

        Should yield AudioChunk objects as they're generated.

        Args:
            text: Text to synthesize

        Yields:
            AudioChunk with audio data
        """
        ...

    @abstractmethod
    async def _play_audio(self, chunk: AudioChunk) -> None:
        """
        Play an audio chunk.

        Args:
            chunk: Audio data to play
        """
        ...

    @abstractmethod
    async def _stop_playback(self) -> None:
        """Stop current audio playback immediately."""
        ...


# =============================================================================
# Placeholder Implementations
# =============================================================================


class DummyTTS(TTSModule):
    """
    Dummy TTS for testing.

    Logs text instead of speaking.
    """

    def __init__(self, config: TTSConfig | None = None):
        super().__init__(config)
        self.spoken_texts: list[str] = []

    async def _synthesize(self, text: str) -> AsyncIterator[AudioChunk]:
        """Fake synthesis - just yield empty chunks."""
        # Simulate synthesis delay based on text length
        delay = len(text) * 0.01  # ~10ms per character
        await asyncio.sleep(min(delay, 0.5))

        self.spoken_texts.append(text)
        logger.info("DummyTTS speaking", text=text[:50])

        # Yield single chunk
        yield AudioChunk(
            data=b"",
            is_final=True,
            text=text,
        )

    async def _play_audio(self, chunk: AudioChunk) -> None:
        """No-op for dummy."""
        pass

    async def _stop_playback(self) -> None:
        """No-op for dummy."""
        pass


class ConsoleTTS(TTSModule):
    """
    Console TTS for testing.

    Prints text to console with typing effect.
    """

    def __init__(
        self,
        config: TTSConfig | None = None,
        char_delay: float = 0.02,
    ):
        super().__init__(config)
        self.char_delay = char_delay
        self._current_text = ""

    async def _synthesize(self, text: str) -> AsyncIterator[AudioChunk]:
        """Yield chunks for each character."""
        self._current_text = text

        for char in text:
            if self._interrupted:
                break
            yield AudioChunk(
                data=char.encode(),
                is_final=False,
                text=char,
            )

        yield AudioChunk(data=b"", is_final=True, text="")

    async def _play_audio(self, chunk: AudioChunk) -> None:
        """Print character with delay."""
        if chunk.text:
            sys.stdout.write(chunk.text)
            sys.stdout.flush()
            await asyncio.sleep(self.char_delay)

        if chunk.is_final:
            sys.stdout.write("\n")
            sys.stdout.flush()

    async def _stop_playback(self) -> None:
        """Print newline on interrupt."""
        sys.stdout.write(" [interrupted]\n")
        sys.stdout.flush()
