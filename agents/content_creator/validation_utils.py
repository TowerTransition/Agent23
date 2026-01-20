# agents/content_creator/validation_utils.py
"""
Simplified validation utilities that lean on the fine-tuned model.
Minimal post-processing - trust the model output more.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional, Tuple


SIGNATURE = "— Elevare by Amaziah"
INSIGHTS_LINE = "Insights from Elevare by Amaziah, building real-world systems with AI."


@dataclass
class BodyExtractionResult:
    """Result of extracting body text from full post."""
    body: str
    extracted_hashtags: List[str]
    removed_footer: bool


def extract_body(full_post_text: str) -> BodyExtractionResult:
    """
    Extract body text from full post (for validation only).
    Removes footer/hashtags that are added in code, not by model.
    Minimal processing - trust the fine-tuned model output.
    """
    text = (full_post_text or "").strip()
    if not text:
        return BodyExtractionResult(body="", extracted_hashtags=[], removed_footer=False)

    removed_footer = False

    # 1) Remove obvious END markers (model shouldn't output these)
    text = re.sub(r"(?im)^\s*END\s*$", "", text).strip()

    # 2) Extract hashtags before removing them (for metadata)
    extracted_hashtags = list(dict.fromkeys(re.findall(r"#([A-Za-z0-9_]+)", text)))  # Preserve order, de-dupe

    # 3) Remove footer (added in code, not by model)
    if SIGNATURE in text:
        text = text.split(SIGNATURE, 1)[0].strip()
        removed_footer = True
    if INSIGHTS_LINE in text:
        text = text.split(INSIGHTS_LINE, 1)[0].strip()
        removed_footer = True

    # 4) Remove hashtags from body (they're added separately in code)
    text = re.sub(r"#\w+", "", text)

    # 5) Remove obvious label prefixes (model shouldn't output these)
    text = re.sub(r"(?im)^(CONTEXT|PROBLEM|AI_SUPPORT|REINFORCEMENT|FOOTER|HASHTAGS)\s*[:.]\s*", "", text)

    # 6) Normalize whitespace
    text = re.sub(r"\s+", " ", text).strip()

    return BodyExtractionResult(body=text, extracted_hashtags=extracted_hashtags, removed_footer=removed_footer)


def split_sentences(body: str) -> List[str]:
    """
    Split into sentences for validation. Works on BODY ONLY.
    """
    body = (body or "").strip()
    if not body:
        return []
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", body) if s.strip()]
    return sentences


def count_sentences_on_body(full_post_text: str) -> Tuple[int, List[str], BodyExtractionResult]:
    """
    Convenience helper: extract body -> split -> count.
    Returns: (sentence_count, sentences, extraction_result)
    """
    extracted = extract_body(full_post_text)
    sentences = split_sentences(extracted.body)
    return len(sentences), sentences, extracted


def ensure_exactly_one_question_at_end(body: str) -> str:
    """
    Ensure body ends with exactly one question mark.
    Simplified - trust the fine-tuned model more, minimal intervention.
    Operates on BODY ONLY. Call this before adding footer/hashtags.
    """
    body = (body or "").strip()
    if not body:
        return body

    q_count = body.count("?")
    
    # Already has exactly one question at the end - perfect!
    if q_count == 1 and body.endswith("?"):
        return body

    # No question - add one at the end
    if q_count == 0:
        return body.rstrip(".!") + "?"

    # Multiple questions - keep the last one, remove others
    # Trust the model's sentence structure, just fix punctuation
    sentences = split_sentences(body)
    if not sentences:
        return body.rstrip(".!") + "?"

    # Find the last sentence with a question
    last_q_idx: Optional[int] = None
    for i in range(len(sentences) - 1, -1, -1):
        if "?" in sentences[i]:
            last_q_idx = i
            break

    if last_q_idx is not None:
        # Extract the question sentence, remove extra ? and ensure it ends with exactly one ?
        question_sentence = sentences[last_q_idx].replace("?", "").rstrip(".!") + "?"
        
        # Keep all other sentences (convert their ? to .)
        fixed: List[str] = []
        for i, s in enumerate(sentences):
            if i != last_q_idx:
                # Remove all ? and ensure it ends with .
                cleaned = s.replace("?", "").rstrip(".!")
                if cleaned:
                    fixed.append(cleaned + ".")
        
        # Append the question sentence at the end
        fixed.append(question_sentence)
        return " ".join(fixed).strip()
    
    # No question found in any sentence - add ? to last sentence
    if sentences:
        sentences[-1] = sentences[-1].rstrip(".!") + "?"
        return " ".join(sentences).strip()
    
    return body.rstrip(".!") + "?"
