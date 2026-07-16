import io
import os
import re
import tempfile

import requests
import torch
import torchaudio


class HiggsV3API:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
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
        """Splits text into chunks, prioritizing punctuation to avoid cutting words."""
        # Split by common sentence terminators
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
        url = f"{server_url.rstrip('/')}/v1/audio/speech"

        text_chunks = self._split_text_into_chunks(text)
        print(f"Divided input text into {len(text_chunks)} chunk(s).")

        # Prepare the reference audio if provided (we only need to save the temp file once)
        ref_path = None
        if reference_audio is not None:
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
                "top_k": 50,
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

            # Convert API response to tensor
            audio_stream = io.BytesIO(response.content)
            waveform, final_sample_rate = torchaudio.load(audio_stream)
            all_waveforms.append(waveform)

        # Clean up the temporary reference file
        if ref_path and os.path.exists(ref_path):
            os.remove(ref_path)

        if not all_waveforms:
            raise Exception("No audio was generated. Check your text input.")

        # Concatenate along the time dimension (dim=-1)
        stitched_waveform = torch.cat(all_waveforms, dim=-1)

        # Package back into ComfyUI's standard AUDIO format [Batch, Channels, Time]
        out_waveform = stitched_waveform.unsqueeze(0)

        print("Successfully stitched audio chunks together!")
        return ({"waveform": out_waveform, "sample_rate": final_sample_rate},)


NODE_CLASS_MAPPINGS = {"HiggsV3API": HiggsV3API}

NODE_DISPLAY_NAME_MAPPINGS = {"HiggsV3API": "Higgs Audio v3"}
