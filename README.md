🌐 Ler em: [English](README.md) | [Português](README.pt.md)

# ComfyUI-TrdHiggsV3

**Local European Portuguese TTS with voice cloning — a custom ComfyUI node**

## Background

I recently moved to Portugal, and while waiting on my visa paperwork to clear (finally had my AIMA interview — all set now), I picked up some freelance work to keep busy (side note: if you've got an interesting AI, audio, or ComfyUI project, I'm currently available for hire — feel free to reach out! I'm a fullstack developer with solid experience integrating AI into production projects).

One project stood out: a client wanted to convert text to speech using his own voice, entirely locally — no cloud uploads, for privacy reasons. Sounded straightforward at first, but he's a European Portuguese speaker, and it turned out most TTS models are trained heavily on Brazilian Portuguese. The accent, rhythm, and cadence just didn't match what he needed.

To solve this properly, I ended up writing this custom ComfyUI node. It handles European Portuguese reliably, and it also chunks long text intelligently to avoid the quality degradation you typically get when feeding TTS models large blocks of text at once.

I think this approach — and honestly the node itself — could be useful for anyone working with non-English languages where "the model technically supports it" doesn't mean it actually sounds right.

## Why Most TTS Pipelines Struggle with European Portuguese

Most open-source TTS models advertise "Portuguese support," but in practice that means Brazilian Portuguese. European Portuguese has distinct vowel reduction, different prosody, and a cadence that Brazilian-trained models consistently get wrong. The result is output that sounds foreign to a native PT-PT listener.

Higgs Audio v3 handles this significantly better, especially when paired with a voice cloning reference recorded by a native European Portuguese speaker. The reference audio anchors the model to the correct accent, rhythm, and intonation.

## How the Chunking Strategy Works

Feeding a TTS model a large block of text typically causes quality to degrade — pacing drifts, pronunciation gets sloppy, and the model can lose coherence entirely past a certain length.

This node splits input text into chunks of roughly 250 characters at sentence boundaries (splitting on `.`, `!`, `?`, and newlines). Short sentences are merged together until the next one would exceed the limit. Each chunk is synthesized independently, then the resulting waveforms are stitched together along the time axis.

This keeps each individual generation short enough for the model to handle cleanly, while producing a seamless final output.

## Features

- Connects to a locally running Higgs Audio v3 server — nothing leaves your machine
- Automatically splits long text into sentence-level chunks and stitches the output
- Supports voice cloning via reference audio + transcript
- Configurable temperature and max token length
- Works well with European Portuguese and other underrepresented locales

## Prerequisites

You need a running [Higgs Audio v3](https://huggingface.co/bosonai/higgs-tts-3-4b) inference server. For this project, I am specifically using [**sglang-omni**](https://github.com/sgl-project/sglang-omni) as the backend server. The node connects to it via HTTP (default: `http://127.0.0.1:8000`).

> **Note:** Getting the audio models properly served can be tricky. If requested, I can create a full deployment setup of ComfyUI and sglang-omni for your specific use case.

Make sure the server is started before running any workflows that use this node.

## Installation

Clone into your ComfyUI custom nodes directory:

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/YOUR_USERNAME/ComfyUI-TrdHiggsV3.git
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Restart ComfyUI. The node will appear under **Audio/TTS** as "TrdHiggsV3 Audio".

## Setting Up Step by Step

1. **Start the Higgs server** on your local machine (default port 8000).
2. **Open ComfyUI** and add the "TrdHiggsV3 Audio" node from the Audio/TTS category.
3. **Enter your text** in the `text` input. Emotion tags like `<|emotion:enthusiasm|>` are supported.
4. **Set `server_url`** to point at your running server (default: `http://127.0.0.1:8000`).
5. **Adjust generation parameters:**
   - `temperature` — controls randomness (0.8 is a good starting point)
   - `max_new_tokens` — upper limit per chunk (1024 default, increase for longer sentences)
6. **Queue the prompt.** The node will split your text, generate audio for each chunk, and return a single stitched AUDIO output.

## Voice Cloning

To clone a voice:

1. **Record a reference clip** — a clean 5-15 second WAV of the target speaker. Minimal background noise, natural pacing.
2. **Connect it** to the `reference_audio` input on the node (use a LoadAudio node or any node that outputs AUDIO).
3. **Provide the transcript** of exactly what was said in the reference clip via the `reference_text` input. Accuracy matters here — the model uses it to align the voice characteristics.
4. **Run the workflow.** All generated chunks will use the reference voice.

For European Portuguese specifically, using a reference clip from a native PT-PT speaker is what makes the difference between "technically Portuguese" and "actually sounds right."

> **Note:** The reference audio file path is passed to the Higgs server as a local filesystem path. Both ComfyUI and the Higgs server must be running on the same machine, or have access to the same filesystem.

## Node Reference

**Node name:** TrdHiggsV3 Audio

**Inputs:**

| Input           | Type   | Required | Description                                |
| --------------- | ------ | -------- | ------------------------------------------ |
| text            | STRING | Yes      | Text to synthesize (supports emotion tags) |
| server_url      | STRING | Yes      | Higgs API server URL                       |
| temperature     | FLOAT  | Yes      | Sampling temperature (0.1 - 2.0)           |
| max_new_tokens  | INT    | Yes      | Max tokens per chunk (128 - 4096)          |
| reference_audio | AUDIO  | No       | Reference audio for voice cloning          |
| reference_text  | STRING | No       | Transcript of the reference audio          |

**Output:** AUDIO — a dict containing `waveform` (Tensor) and `sample_rate` (int).

## Known Limitations & Possible Improvements

- **No request timeout.** If the Higgs server hangs, ComfyUI blocks indefinitely. Adding a configurable timeout (e.g. 120s) would fix this.
- **Reference audio requires local filesystem access.** The reference WAV is saved to a temp file and the path is sent to the server. This only works when both run on the same machine.
- **Oversized sentences are not sub-split.** A single sentence longer than 250 characters is sent whole, which may exceed the model's effective context. A word-boundary fallback split would help.
- **`top_k` is hardcoded to 50.** Could be exposed as an optional node input for more control over generation.
- **No retry logic.** A transient network error fails the entire generation. Retry with backoff would improve reliability.
- **Channel count assumption.** The stitching step assumes all chunks return the same number of audio channels (mono or stereo). A mismatch would cause a runtime error.

## License

MIT
