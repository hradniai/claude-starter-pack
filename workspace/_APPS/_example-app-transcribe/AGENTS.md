<purpose>
**Transcribe** — convert local audio/video files into markdown transcripts via an LLM API.

This is a STUB shipped with the starter pack as an example app. The actual API call is not yet implemented. Treat it as a structure skeleton you fill in.
</purpose>

<product>
- **Status:** stub / not implemented
- **Intended provider:** Google Gemini (multimodal API, supports direct audio input)
- **Alternative:** OpenAI Whisper (audio-only) or local whisper.cpp
- **Input:** local audio (.mp3, .wav, .m4a) or video (.mp4, .mov) file
- **Output:** markdown transcript next to the input file
</product>

<usage>
## Intended usage (once implemented)

```bash
~/Documents/_APPS/_example-app-transcribe/transcribe.sh path/to/audio.mp3
```

Output: `path/to/audio.transcript.md`

## What you need to provide

1. A working LLM API key (Gemini recommended for audio input)
2. The actual API call in `transcribe.sh`
3. Optionally: speaker diarization, timestamps, summary post-processing
</usage>

<implementation_notes>
## Why no working code shipped

- Multi-vendor APIs change frequently (model names, request formats)
- Local whisper.cpp requires per-platform setup we can't predict
- Audio file size limits and chunking strategies vary

The stub gives you the directory structure and naming convention. You implement the actual work for your preferred provider.
</implementation_notes>

<scope>
## What this stub IS
- Directory layout: `src/`, `examples/`, `notes.md`
- Documentation convention (this AGENTS.md)
- Placeholder `transcribe.sh` with documented arguments

## What this stub is NOT
- A working transcription tool — you implement the API call
- A YouTube/Vimeo downloader — that's a different concern (legal grey zone, separate tooling)
- A speaker diarization tool — needs separate model
</scope>
