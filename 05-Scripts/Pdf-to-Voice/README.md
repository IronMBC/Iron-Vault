# PDF to Cloned-Voice Narrator

Turns any text-based PDF into an audiobook narrated in a cloned voice — free, no paid TTS API required.

Built as a working example of an end-to-end audio pipeline — PDF parsing, text chunking for model limits, voice cloning, and resumable batch generation.

> **Note:** XTTS v2 does real per-chunk voice-cloning inference, not fast rule-based TTS. A full book (1000+ chunks) can take several sessions on free-tier Colab, since the daily GPU quota cuts runs off partway through. The pipeline is resumable, so nothing is lost between sessions — Colab Pro or a smaller/faster TTS model are the options if you need it quicker.

## How it works

1. **Extract** — pulls raw text out of the PDF (PyMuPDF)
2. **Section** — splits the text into ~1200-character concept sections
3. **Chunk** — further splits into ~250-character pieces (XTTS's per-call limit)
4. **Clone + generate** — XTTS v2 clones a voice from a short sample and narrates each chunk
5. **Merge** — stitches every chunk into one final `.wav`

Resumable by design: if generation stops partway (e.g. hits a Colab quota), re-running skips chunks that already exist.

## Usage

### Locally
```bash
pip install -r requirements.txt
python narrate.py --pdf book.pdf --voice voice_sample.wav --out output.wav
```

### On Colab
Use `colab_demo.ipynb` — mounts Google Drive for storage/model caching and calls `narrate.py`.

## Requirements
- A text-based PDF (scanned/image-only PDFs need OCR first — not included here)
- A short, clean voice sample (a few seconds of clear speech, wav or m4a)
- GPU recommended (Colab free tier works fine) but not required

## Roadmap
- [ ] Add an explanation-agent pass so it can teach concepts, not just read text verbatim
- [ ] OCR fallback for scanned PDFs
- [ ] True offline/on-device version
