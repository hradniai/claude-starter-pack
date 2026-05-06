# Transcribe (stub)

Local audio/video → markdown transcript via LLM API.

> **Status:** stub. The script is documented but the API call is not yet implemented. See AGENTS.md for context.

## Quickstart (after implementation)

```bash
./transcribe.sh path/to/audio.mp3
```

## What you need to do to make this work

1. Pick a provider (Gemini, OpenAI, or local whisper.cpp)
2. Add the relevant API key to `~/.claude/.env` (e.g. `GEMINI_API_KEY=...`)
3. Implement the API call in `transcribe.sh` — see comments in the file for hints
4. Test on a known sample in `examples/`

## Why no working version is shipped

- API formats change frequently across providers
- Local tooling has per-platform setup that this starter pack can't assume
- Implementation forces you to make a deliberate choice instead of inheriting whatever the package author preferred

## Alternatives if you don't want to build this yourself

- `whisper.cpp` — local, free, runs on CPU/GPU, requires per-platform install
- Anthropic Claude or OpenAI Whisper API — easier API but cost per minute
- Google Gemini multimodal API — supports audio directly in chat, often cheapest for casual use

## Removing the stub

If you don't want this app:
```bash
rm -rf ~/Documents/_APPS/_example-app-transcribe
```
