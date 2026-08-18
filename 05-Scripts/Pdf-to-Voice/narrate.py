"""
narrate.py — PDF to cloned-voice audiobook narrator.

Pipeline:
  1. Extract text from a PDF
  2. Split into concept-sized sections, then into TTS-safe chunks
  3. Generate narration for each chunk using a cloned voice (XTTS v2)
  4. Merge all chunks into a single .wav audiobook

Usage:
    python narrate.py --pdf path/to/book.pdf --voice path/to/voice_sample.wav --out output.wav

Notes:
  - First run downloads the XTTS v2 model (~2GB). Set TTS_HOME to cache it
    somewhere persistent (e.g. a mounted Drive folder) so it doesn't
    re-download every session.
  - Designed to be resumable: chunks already generated in the output
    directory are skipped on re-run.
"""

import argparse
import glob
import json
import os
import re
import wave

import torch
from TTS.api import TTS

os.environ.setdefault("COQUI_TOS_AGREED", "1")  # auto-accept model license


def extract_text(pdf_path: str) -> str:
    import fitz  # PyMuPDF

    doc = fitz.open(pdf_path)
    text = " ".join(page.get_text() for page in doc)
    text = re.sub(r"\s+", " ", text).strip()
    doc.close()

    if len(text) < 200:
        raise ValueError(
            "Almost no text extracted — this PDF is probably scanned images, "
            "not real text. Run OCR on it first."
        )
    return text


def split_into_sections(text: str, max_chars: int = 1200) -> list[str]:
    """Split into concept-sized sections sized for an LLM to explain one idea
    at a time (used if you add an explanation-agent step later)."""
    sentences = re.split(r"(?<=[.!?])\s+", text)
    sections, current = [], ""
    for s in sentences:
        if len(current) + len(s) + 1 <= max_chars:
            current = (current + " " + s).strip()
        else:
            if current:
                sections.append(current)
            current = s
    if current:
        sections.append(current)
    return sections


def split_into_tts_chunks(sections: list[str], max_chars: int = 250) -> list[str]:
    """Split into chunks under the TTS model's character limit per call."""
    chunks = []
    for block in sections:
        words = re.split(r"(?<=[.!?\u3002\uff0c;:])\s+", block)
        current = ""
        for w in words:
            if len(current) + len(w) + 1 <= max_chars:
                current = (current + " " + w).strip()
            else:
                if current:
                    chunks.append(current)
                current = w
        if current:
            chunks.append(current)
    return chunks


def generate_audio(
    chunks: list[str],
    voice_path: str,
    out_dir: str,
    language: str = "en",
    temperature: float = 0.65,
    repetition_penalty: float = 2.0,
) -> list[str]:
    os.makedirs(out_dir, exist_ok=True)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(device)

    chunk_paths = []
    for i, chunk in enumerate(chunks):
        chunk_path = os.path.join(out_dir, f"_chunk_{i}.wav")
        chunk_paths.append(chunk_path)

        if os.path.exists(chunk_path):
            continue  # resume support — skip already-generated chunks

        tts.tts_to_file(
            text=chunk,
            speaker_wav=voice_path,
            language=language,
            file_path=chunk_path,
            temperature=temperature,
            repetition_penalty=repetition_penalty,
        )
        print(f"Saved chunk {i + 1}/{len(chunks)}")

    return chunk_paths


def merge_chunks(chunk_paths: list[str], output_path: str) -> None:
    with wave.open(chunk_paths[0], "rb") as first:
        params = first.getparams()

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with wave.open(output_path, "wb") as out_f:
        out_f.setparams(params)
        for path in chunk_paths:
            with wave.open(path, "rb") as w:
                out_f.writeframes(w.readframes(w.getnframes()))

    print(f"Done. Full narration saved to: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="PDF to cloned-voice audiobook narrator")
    parser.add_argument("--pdf", required=True, help="Path to the source PDF")
    parser.add_argument("--voice", required=True, help="Path to a voice sample (wav/m4a) to clone")
    parser.add_argument("--out", default="output.wav", help="Path for the final merged audio")
    parser.add_argument("--chunks-dir", default="chunks", help="Directory to store per-chunk audio")
    parser.add_argument("--language", default="en")
    args = parser.parse_args()

    text = extract_text(args.pdf)
    sections = split_into_sections(text)
    chunks = split_into_tts_chunks(sections)
    print(f"{len(chunks)} chunks ready for narration")

    chunk_paths = generate_audio(chunks, args.voice, args.chunks_dir, language=args.language)
    merge_chunks(chunk_paths, args.out)


if __name__ == "__main__":
    main()
