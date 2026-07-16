# ComfyUI-HiggsV3-v02

A ComfyUI custom node for text-to-speech using the Higgs Audio v3 API.

## Features

- Connects to a running Higgs Audio v3 server for TTS generation
- Automatically splits long text into chunks and stitches the output
- Supports reference audio for voice cloning
- Configurable temperature and max token length

## Installation

Clone into your ComfyUI custom nodes directory:

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/YOUR_USERNAME/ComfyUI-HiggsV3-v02.git
```

Install dependencies:

```bash
pip install -r requirements.txt
```

## Prerequisites

You need a running Higgs Audio v3 inference server. The node connects to it via HTTP (default: `http://127.0.0.1:8000`).

## Node: Higgs Audio v3

**Inputs:**

| Input | Type | Description |
|---|---|---|
| text | STRING | Text to synthesize (supports emotion tags) |
| server_url | STRING | Higgs API server URL |
| temperature | FLOAT | Sampling temperature (0.1 - 2.0) |
| max_new_tokens | INT | Max tokens per chunk (128 - 4096) |
| reference_audio | AUDIO (optional) | Reference audio for voice cloning |
| reference_text | STRING (optional) | Transcript of the reference audio |

**Output:** AUDIO

## License

MIT
