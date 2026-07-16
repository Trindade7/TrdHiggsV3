"""ComfyUI custom node for text-to-speech using the Higgs Audio v3 API.

This module provides a single ComfyUI node ("Higgs Audio v3") that sends text
to a running Higgs Audio v3 inference server over HTTP and returns synthesized
speech as a ComfyUI AUDIO output.

How it works:
    1. Long input text is split into sentence-level chunks (default <= 250 chars)
       to stay within the model's token budget.
    2. Each chunk is sent as an individual request to the Higgs ``/v1/audio/speech``
       endpoint.
    3. The returned audio waveforms are concatenated along the time axis and
       packaged into ComfyUI's standard AUDIO format
       (``{"waveform": Tensor[B,C,T], "sample_rate": int}``).

Voice cloning is supported by providing an optional reference audio input
together with its transcript.

Dependencies:
    - ``requests`` (installed via requirements.txt)
    - ``torch`` and ``torchaudio`` (provided by ComfyUI at runtime)

Limitations & Possible Improvements:
    - No request timeout: ``requests.post()`` has no timeout, so a hung server
      blocks ComfyUI indefinitely. Add a timeout parameter (e.g. 120s).
    - ``audio_path`` assumes local filesystem: Reference audio is saved to a
      temp file and the local path is sent in the JSON payload. This only works
      if the Higgs server runs on the same machine.
    - Oversized sentences are not sub-split: A single sentence longer than
      ``max_length`` is passed through whole, which may exceed API token limits.
      A word-boundary fallback split would help.
    - ``top_k`` is hardcoded to 50: Consider exposing as an optional node input.
    - No retry logic: Transient network errors will fail the entire generation.
      Basic retry with backoff would improve reliability.
    - Bare ``Exception``: Could be replaced with ``RuntimeError`` for more
      specific error handling.
    - Channel count assumption: ``torch.cat`` assumes all chunks return the same
      number of audio channels. A mono/stereo mismatch would cause a runtime
      error.
"""

import io
import os
import re
import tempfile

import requests
import torch
import torchaudio


class HiggsV3API:
    """ComfyUI node that generates speech via the Higgs Audio v3 API.

    Registers under the ``Audio/TTS`` category with the display name
    "Higgs Audio v3".

    Required inputs:
        text, server_url, temperature, max_new_tokens

    Optional inputs:
        reference_audio, reference_text — used together for voice cloning.

    Output:
        A single AUDIO output (dict with ``waveform`` Tensor[B,C,T] and
        ``sample_rate`` int).
    """

    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        """Define the node's input slots for the ComfyUI graph editor.

        Required:
            text (STRING): The text to synthesize. Supports Higgs emotion tags
                such as ``<|emotion:enthusiasm|>``.
            server_url (STRING): Base URL of the Higgs Audio v3 server.
            temperature (FLOAT): Sampling temperature controlling randomness
                (0.1 = deterministic, 2.0 = very random).
            max_new_tokens (INT): Maximum number of tokens the model may
                generate per chunk.

        Optional:
            reference_audio (AUDIO): A ComfyUI AUDIO input used as a voice
                cloning reference. Must be paired with ``reference_text``.
            reference_text (STRING): Transcript of the reference audio, so
                the model knows what was said.
        """
        return {
            "required": {
                "text": (
                    "STRING",
                    {
                        "multiline": True,
                        "default": "<|emotion:enthusiasm|> Hello! This is Higgs Audio v3 speaking. I can now handle very long texts.",
                    },
                ),
                "server_url": ("STRING", {"default": "http://127.0.0.1:8000"}),
                "temperature": (
                    "FLOAT",
                    {"default": 0.8, "min": 0.1, "max": 2.0, "step": 0.1},
                ),
                "max_new_tokens": (
                    "INT",
                    {"default": 1024, "min": 128, "max": 4096, "step": 64},
                ),
            },
            "optional": {
                "reference_audio": ("AUDIO",),
                "reference_text": ("STRING", {"multiline": True, "default": ""}),
            },
        }

    RETURN_TYPES = ("AUDIO",)
    RETURN_NAMES = ("audio",)
    FUNCTION = "generate_speech"
    CATEGORY = "Audio/TTS"

    def _split_text_into_chunks(self, text, max_length=250):
        """Split text into chunks at sentence boundaries.

        Breaks the input text into pieces of at most ``max_length`` characters
        by splitting on sentence-ending punctuation (``.``, ``!``, ``?``) and
        newlines, then greedily merging consecutive sentences until the next
        one would exceed the limit.

        Args:
            text (str): The input text to split.
            max_length (int): Maximum character length per chunk. Defaults
                to 250.

        Returns:
            list[str]: Ordered list of text chunks. Note that a single
            sentence longer than ``max_length`` is passed through unsplit.
        """
        # Lookbehind regex: split after sentence-ending punctuation followed
        # by whitespace, keeping the punctuation attached to the preceding
        # sentence.
        sentences = re.split(r"(?<=[.!?\n])\s+", text.strip())

        chunks = []
        current_chunk = ""

        for sentence in sentences:
            if not sentence.strip():
                continue

            if len(sentence) > max_length:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = ""
                chunks.append(sentence.strip())

            elif len(current_chunk) + len(sentence) > max_length:
                chunks.append(current_chunk.strip())
                current_chunk = sentence

            else:
                current_chunk += " " + sentence

        if current_chunk:
            chunks.append(current_chunk.strip())

        return chunks

    def generate_speech(
        self,
        text,
        server_url,
        temperature,
        max_new_tokens,
        reference_audio=None,
        reference_text="",
    ):
        """Generate speech audio from text via the Higgs Audio v3 API.

        Splits the input text into sentence-level chunks, sends each chunk
        to the Higgs server as a separate HTTP request, and concatenates
        the returned waveforms into a single audio output.

        If ``reference_audio`` is provided, the waveform is written to a
        temporary WAV file whose path is included in every request payload
        for voice cloning. The temp file is cleaned up after all chunks are
        processed (or on error).

        Args:
            text (str): The text to synthesize.
            server_url (str): Base URL of the Higgs server
                (e.g. ``http://127.0.0.1:8000``).
            temperature (float): Sampling temperature (0.1 - 2.0).
            max_new_tokens (int): Maximum tokens the model may generate
                per chunk (128 - 4096).
            reference_audio (dict | None): Optional ComfyUI AUDIO dict
                (``{"waveform": Tensor, "sample_rate": int}``) used as a
                voice cloning reference.
            reference_text (str): Transcript of the reference audio. Only
                used when ``reference_audio`` is provided.

        Returns:
            tuple: Single-element tuple containing an AUDIO dict
            ``{"waveform": Tensor[B,C,T], "sample_rate": int}``.

        Raises:
            Exception: If the API returns a non-200 status code, or if
                no audio is generated (e.g. empty input text).
        """
        # Normalize server URL and build the full endpoint path.
        url = f"{server_url.rstrip('/')}/v1/audio/speech"

        text_chunks = self._split_text_into_chunks(text)
        print(f"Divided input text into {len(text_chunks)} chunk(s).")

        # Prepare the reference audio if provided (we only need to save the temp file once)
        ref_path = None
        if reference_audio is not None:
            # Index [0] selects the first batch item from the [B, C, T] tensor.
            waveform = reference_audio["waveform"][0]
            sample_rate = reference_audio["sample_rate"]
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                ref_path = tmp.name
            torchaudio.save(ref_path, waveform, sample_rate)

        all_waveforms = []
        final_sample_rate = 24000  # Default Higgs output SR

        for i, chunk in enumerate(text_chunks):
            print(f"Processing chunk {i+1}/{len(text_chunks)}...")

            payload = {
                "input": chunk,
                "temperature": temperature,
                "top_k": 50,  # Hardcoded; not exposed as a node input.
                "max_new_tokens": max_new_tokens,
            }

            if ref_path is not None:
                payload["references"] = [
                    {"audio_path": ref_path, "text": reference_text}
                ]

            response = requests.post(url, json=payload)

            if response.status_code != 200:
                # Clean up before crashing
                if ref_path and os.path.exists(ref_path):
                    os.remove(ref_path)
                raise Exception(
                    f"Higgs API Error {response.status_code} on chunk {i+1}: {response.text}"
                )

            # Convert API response to tensor.
            audio_stream = io.BytesIO(response.content)
            # Note: final_sample_rate is overwritten on each iteration; the
            # last chunk's sample rate is used for the stitched output.
            waveform, final_sample_rate = torchaudio.load(audio_stream)
            all_waveforms.append(waveform)

        # Clean up the temporary reference file
        if ref_path and os.path.exists(ref_path):
            os.remove(ref_path)

        if not all_waveforms:
            raise Exception("No audio was generated. Check your text input.")

        # Concatenate along the time dimension (dim=-1).
        # Assumes all chunks share the same number of channels.
        stitched_waveform = torch.cat(all_waveforms, dim=-1)

        # Package back into ComfyUI's standard AUDIO format [Batch, Channels, Time]
        out_waveform = stitched_waveform.unsqueeze(0)

        print("Successfully stitched audio chunks together!")
        return ({"waveform": out_waveform, "sample_rate": final_sample_rate},)


NODE_CLASS_MAPPINGS = {"HiggsV3API": HiggsV3API}

NODE_DISPLAY_NAME_MAPPINGS = {"HiggsV3API": "Higgs Audio v3"}
