"""Real-time speech-to-text using faster-whisper with voice activity detection."""

from __future__ import annotations

import asyncio
import logging
import queue
import threading
from typing import AsyncIterator, Callable

import numpy as np
import sounddevice as sd
from faster_whisper import WhisperModel

from drone_vla.config import STTConfig

logger = logging.getLogger(__name__)

SAMPLE_RATE = 16000
CHUNK_DURATION_S = 0.5
SILENCE_THRESHOLD = 0.01
MIN_SPEECH_DURATION_S = 0.5
MAX_SPEECH_DURATION_S = 30.0


class WhisperSTT:
    def __init__(self, config: STTConfig):
        device = config.device
        if device == "auto":
            device = "cuda" if self._cuda_available() else "cpu"
        compute_type = "float16" if device == "cuda" else "int8"

        logger.info("Loading Whisper model %s on %s", config.model_size, device)
        self._model = WhisperModel(
            config.model_size,
            device=device,
            compute_type=compute_type,
        )
        self._language = config.language
        self._vad_filter = config.vad_filter
        self._beam_size = config.beam_size
        self._audio_queue: queue.Queue[np.ndarray | None] = queue.Queue()
        self._running = False

    @staticmethod
    def _cuda_available() -> bool:
        try:
            import torch
            return torch.cuda.is_available()
        except ImportError:
            return False

    def _audio_callback(self, indata: np.ndarray, frames: int, time_info, status):
        if status:
            logger.warning("Audio status: %s", status)
        self._audio_queue.put(indata[:, 0].copy())

    def _collect_utterance(self) -> np.ndarray | None:
        """Collect audio chunks until silence is detected after speech."""
        chunks: list[np.ndarray] = []
        speech_started = False
        silence_chunks = 0
        max_silence_chunks = int(1.5 / CHUNK_DURATION_S)
        max_chunks = int(MAX_SPEECH_DURATION_S / CHUNK_DURATION_S)

        while self._running and len(chunks) < max_chunks:
            try:
                chunk = self._audio_queue.get(timeout=1.0)
            except queue.Empty:
                continue
            if chunk is None:
                return None

            rms = float(np.sqrt(np.mean(chunk**2)))
            is_speech = rms > SILENCE_THRESHOLD

            if is_speech:
                speech_started = True
                silence_chunks = 0
                chunks.append(chunk)
            elif speech_started:
                silence_chunks += 1
                chunks.append(chunk)
                if silence_chunks >= max_silence_chunks:
                    break

        if not chunks:
            return None

        audio = np.concatenate(chunks)
        duration = len(audio) / SAMPLE_RATE
        if duration < MIN_SPEECH_DURATION_S:
            return None
        return audio

    def transcribe_audio(self, audio: np.ndarray) -> str:
        segments, info = self._model.transcribe(
            audio,
            language=self._language,
            beam_size=self._beam_size,
            vad_filter=self._vad_filter,
        )
        text = " ".join(seg.text.strip() for seg in segments)
        logger.info("Transcribed (%.1fs, lang=%s, prob=%.2f): %s",
                     info.duration, info.language, info.language_probability, text)
        return text

    async def stream_transcriptions(self) -> AsyncIterator[str]:
        """Yield transcribed utterances from the microphone in real time."""
        loop = asyncio.get_event_loop()
        self._running = True
        chunk_samples = int(SAMPLE_RATE * CHUNK_DURATION_S)

        stream = sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype="float32",
            blocksize=chunk_samples,
            callback=self._audio_callback,
        )
        stream.start()
        logger.info("Microphone stream started — listening...")

        try:
            while self._running:
                audio = await loop.run_in_executor(None, self._collect_utterance)
                if audio is None:
                    continue
                text = await loop.run_in_executor(None, self.transcribe_audio, audio)
                if text.strip():
                    yield text.strip()
        finally:
            self._running = False
            stream.stop()
            stream.close()

    def stop(self):
        self._running = False
        self._audio_queue.put(None)

    async def transcribe_file(self, path: str) -> str:
        """Transcribe an audio file (useful for testing)."""
        loop = asyncio.get_event_loop()
        segments, _ = await loop.run_in_executor(
            None,
            lambda: self._model.transcribe(
                path,
                language=self._language,
                beam_size=self._beam_size,
                vad_filter=self._vad_filter,
            ),
        )
        return " ".join(seg.text.strip() for seg in segments)
