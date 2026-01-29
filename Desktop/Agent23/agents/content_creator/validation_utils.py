# agents/content_creator/validation_utils.py
"""
Validation utilities aligned with PEFT training data format.

TRAINING DATA FORMAT (what the model learned):
- 4-6 sentences in body
- NO questions - all posts end with STATEMENTS
- Structure: Opening thesis → Problem → AI supports... → Closing benefit statement
- Tagline: "Real-world systems. Real clarity."
- Signature: "— Elevare by Amaziah"
- Exactly 4 hashtags
- Tone: Observational, supportive, grounded
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional, Tuple


SIGNATURE = "— Elevare by Amaziah"
# Training data uses this exact tagline before signature
TAGLINE = "Real-world systems. Real clarity."
# Legacy - kept for backward compatibility during extraction
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
    # Order matters: tagline comes before signature in training data
    if TAGLINE in text:
        text = text.split(TAGLINE, 1)[0].strip()
        removed_footer = True
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


def ends_with_statement(sentence: str) -> bool:
    """
    Check if a sentence ends with a statement (period), not a question.
    Training data shows all posts end with statements, never questions.
    """
    sentence = sentence.strip()
    if not sentence:
        return False

    # Statement ends with period (or could be missing punctuation)
    return sentence.endswith(".") or not sentence.endswith("?")


def is_valid_closing_statement(sentence: str) -> bool:
    """
    Validate that the closing sentence matches training data patterns.
    Training data closing statements are typically:
    - Short benefit statements (3-8 words)
    - Pattern: "X supports/protects/enables/strengthens Y."
    - Examples: "Clarity supports confident decisions."
    """
    sentence = sentence.strip().rstrip(".")
    if not sentence:
        return False

    # Valid closing patterns from training data
    valid_patterns = [
        r'^(Clarity|Structure|Understanding|Visibility|Alignment|Consistency|Coordination|Organization|Preparation|Awareness)\s+(supports|protects|enables|strengthens|improves|reduces|maintains|builds|creates|preserves)',
        r'^(Clear|Visible|Organized|Aligned|Consistent|Reduced|Better|Stronger)\s+\w+\s+(support|protect|enable|strengthen|improve|reduce|maintain|build|create|preserve)',
        r'\b(supports|protects|enables|strengthens|improves|reduces|maintains|builds|creates|preserves)\s+\w+\.$',
    ]

    for pattern in valid_patterns:
        if re.search(pattern, sentence, re.IGNORECASE):
            return True

    # Also accept any sentence ending with a period that isn't a question
    return not sentence.endswith("?")


def validate_sentence_count(sentences: List[str], min_count: int = 4, max_count: int = 6) -> bool:
    """
    Validate sentence count matches training data expectations.
    Training data: 4-6 sentences in body (before tagline).
    """
    count = len(sentences)
    return min_count <= count <= max_count


def get_sentence_count_range(platform: str) -> Tuple[int, int]:
    """
    Get expected sentence count range by platform.
    Based on training data analysis: 4-6 sentences is typical.
    """
    # Training data doesn't vary much by platform - all follow same format
    # But we can allow some platform-specific flexibility
    if platform in ("twitter", "x"):
        return (2, 4)  # Shorter for Twitter
    elif platform == "linkedin":
        return (4, 8)  # Can be slightly longer for LinkedIn
    elif platform == "instagram":
        return (3, 5)  # Medium length for Instagram
    else:  # facebook and default
        return (4, 6)  # Standard training format


def ensure_ends_with_statement(body: str, domain: Optional[str] = None) -> str:
    """
    Ensure body ends with a statement (period), NOT a question.
    Training data shows all posts end with declarative statements.

    Args:
        body: The body text to validate/fix
        domain: Optional domain context (for compatibility)

    Returns:
        Body text ending with a statement
    """
    body = (body or "").strip()
    if not body:
        return body

    sentences = split_sentences(body)
    if not sentences:
        return body

    last = sentences[-1].strip()

    # If last sentence ends with question mark, convert to statement
    if last.endswith("?"):
        # Remove question mark and add period
        last = last.rstrip("?").strip() + "."
        sentences[-1] = last

    # Ensure last sentence ends with period
    if not last.endswith("."):
        sentences[-1] = last + "."

    return " ".join(sentences).strip()


def ensure_exactly_one_question_at_end(body: str, domain: Optional[str] = None) -> str:
    """
    DEPRECATED: Training data shows NO questions in posts.
    This function now calls ensure_ends_with_statement for backward compatibility.

    The model was trained on posts that end with STATEMENTS, not questions.
    """
    # Convert any trailing question to statement
    return ensure_ends_with_statement(body, domain)
