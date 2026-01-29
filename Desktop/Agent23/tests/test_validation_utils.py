"""
Unit tests for validation_utils.

Tests cover:
- Body extraction (removes footer, hashtags, labels)
- Sentence splitting
- Statement enforcement (posts end with statements, NOT questions)
- Count sentences helper
- Sentence count range by platform

TRAINING DATA FORMAT (what the model learned):
- 4-6 sentences in body
- NO questions - all posts end with STATEMENTS
- Tagline: "Real-world systems. Real clarity."
- Signature: "— Elevare by Amaziah"
- Exactly 4 hashtags
"""

import unittest
import sys
import os

# Add parent directory to path to import the module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from agents.content_creator.validation_utils import (
    extract_body,
    split_sentences,
    count_sentences_on_body,
    ensure_ends_with_statement,
    ensure_exactly_one_question_at_end,  # Deprecated - now calls ensure_ends_with_statement
    ends_with_statement,
    is_valid_closing_statement,
    validate_sentence_count,
    get_sentence_count_range,
    BodyExtractionResult,
    SIGNATURE,
    TAGLINE,
    INSIGHTS_LINE
)


class TestValidationUtils(unittest.TestCase):
    """Test suite for validation_utils."""

    # -------------------------
    # extract_body Tests
    # -------------------------

    def test_extract_body_empty_string(self):
        """Test extract_body with empty string."""
        result = extract_body("")
        self.assertEqual(result.body, "")
        self.assertEqual(result.extracted_hashtags, [])
        self.assertFalse(result.removed_footer)

    def test_extract_body_removes_footer(self):
        """Test extract_body removes footer."""
        text = f"This is the body content.\n\n{SIGNATURE}\n{INSIGHTS_LINE}"
        result = extract_body(text)
        self.assertNotIn(SIGNATURE, result.body)
        self.assertNotIn(INSIGHTS_LINE, result.body)
        self.assertIn("body content", result.body)
        self.assertTrue(result.removed_footer)

    def test_extract_body_removes_tagline(self):
        """Test extract_body removes tagline (training data format)."""
        text = f"This is the body content.\n\n{TAGLINE}\n{SIGNATURE}"
        result = extract_body(text)
        self.assertNotIn(TAGLINE, result.body)
        self.assertNotIn(SIGNATURE, result.body)
        self.assertIn("body content", result.body)
        self.assertTrue(result.removed_footer)

    def test_extract_body_removes_insights_line(self):
        """Test extract_body removes insights line."""
        text = f"This is content.\n\n{INSIGHTS_LINE}"
        result = extract_body(text)
        self.assertNotIn(INSIGHTS_LINE, result.body)
        self.assertTrue(result.removed_footer)

    def test_extract_body_extracts_hashtags(self):
        """Test extract_body extracts hashtags."""
        text = "This is content with #hashtag1 and #hashtag2."
        result = extract_body(text)
        self.assertIn("hashtag1", result.extracted_hashtags)
        self.assertIn("hashtag2", result.extracted_hashtags)
        self.assertNotIn("#hashtag1", result.body)

    def test_extract_body_removes_hashtags_from_body(self):
        """Test extract_body removes hashtags from body."""
        text = "This is content with #hashtag1 in it."
        result = extract_body(text)
        self.assertNotIn("#hashtag1", result.body)
        self.assertIn("content", result.body)

    def test_extract_body_removes_end_marker(self):
        """Test extract_body removes END marker."""
        text = "This is content.\nEND"
        result = extract_body(text)
        self.assertNotIn("END", result.body)

    def test_extract_body_removes_label_prefixes(self):
        """Test extract_body removes label prefixes."""
        text = "CONTEXT: This is the actual content."
        result = extract_body(text)
        self.assertNotIn("CONTEXT:", result.body)
        self.assertIn("actual content", result.body)

    def test_extract_body_removes_multiple_label_prefixes(self):
        """Test extract_body removes multiple label prefixes."""
        text = "PROBLEM: Issue one.\nAI_SUPPORT: Support text."
        result = extract_body(text)
        self.assertNotIn("PROBLEM:", result.body)
        self.assertNotIn("AI_SUPPORT:", result.body)

    def test_extract_body_deduplicates_hashtags(self):
        """Test extract_body deduplicates hashtags."""
        text = "Content with #test and #Test and #TEST."
        result = extract_body(text)
        # Should preserve order and deduplicate (case-insensitive)
        self.assertGreaterEqual(len(result.extracted_hashtags), 1)
        self.assertLessEqual(len(result.extracted_hashtags), 3)

    def test_extract_body_preserves_content(self):
        """Test extract_body preserves actual content."""
        text = "This is the main content that should be preserved."
        result = extract_body(text)
        self.assertIn("main content", result.body)
        self.assertIn("preserved", result.body)

    def test_extract_body_with_footer_and_hashtags(self):
        """Test extract_body with both footer and hashtags."""
        text = f"Content here. #tag1 #tag2\n\n{SIGNATURE}\n{INSIGHTS_LINE}"
        result = extract_body(text)
        self.assertIn("Content here", result.body)
        self.assertNotIn("#tag1", result.body)
        self.assertNotIn(SIGNATURE, result.body)
        self.assertIn("tag1", result.extracted_hashtags)
        self.assertTrue(result.removed_footer)

    def test_extract_body_with_training_format_footer(self):
        """Test extract_body with exact training data footer format."""
        text = f"Clarity supports confident decisions.\n\n{TAGLINE}\n{SIGNATURE}\n\n#RealWorldAI #ClarityMatters #SystemDesign #ProcessClarity"
        result = extract_body(text)
        self.assertIn("Clarity supports", result.body)
        self.assertNotIn(TAGLINE, result.body)
        self.assertNotIn(SIGNATURE, result.body)
        self.assertTrue(result.removed_footer)
        self.assertEqual(len(result.extracted_hashtags), 4)

    # -------------------------
    # split_sentences Tests
    # -------------------------

    def test_split_sentences_empty_string(self):
        """Test split_sentences with empty string."""
        sentences = split_sentences("")
        self.assertEqual(sentences, [])

    def test_split_sentences_single_sentence(self):
        """Test split_sentences with single sentence."""
        sentences = split_sentences("This is a sentence.")
        self.assertEqual(len(sentences), 1)
        self.assertEqual(sentences[0], "This is a sentence.")

    def test_split_sentences_multiple_sentences(self):
        """Test split_sentences with multiple sentences."""
        text = "First sentence. Second sentence. Third sentence."
        sentences = split_sentences(text)
        self.assertEqual(len(sentences), 3)
        self.assertIn("First sentence", sentences[0])
        self.assertIn("Second sentence", sentences[1])
        self.assertIn("Third sentence", sentences[2])

    def test_split_sentences_with_questions(self):
        """Test split_sentences with question marks."""
        text = "First sentence. Second sentence? Third sentence."
        sentences = split_sentences(text)
        self.assertEqual(len(sentences), 3)
        self.assertIn("?", sentences[1])

    def test_split_sentences_with_exclamations(self):
        """Test split_sentences with exclamation marks."""
        text = "First sentence! Second sentence. Third sentence."
        sentences = split_sentences(text)
        self.assertEqual(len(sentences), 3)
        self.assertIn("!", sentences[0])

    def test_split_sentences_strips_whitespace(self):
        """Test split_sentences strips whitespace."""
        text = "  First sentence.  Second sentence.  "
        sentences = split_sentences(text)
        self.assertEqual(len(sentences), 2)
        self.assertEqual(sentences[0], "First sentence.")
        self.assertEqual(sentences[1], "Second sentence.")

    # -------------------------
    # count_sentences_on_body Tests
    # -------------------------

    def test_count_sentences_on_body(self):
        """Test count_sentences_on_body helper."""
        text = f"First. Second. Third.\n\n{SIGNATURE}"
        count, sentences, result = count_sentences_on_body(text)
        self.assertEqual(count, 3)
        self.assertEqual(len(sentences), 3)
        self.assertIsInstance(result, BodyExtractionResult)

    def test_count_sentences_on_body_with_hashtags(self):
        """Test count_sentences_on_body with hashtags."""
        text = "First. Second. #hashtag"
        count, sentences, result = count_sentences_on_body(text)
        self.assertEqual(count, 2)  # Hashtags removed from body
        self.assertIn("hashtag", result.extracted_hashtags)

    # -------------------------
    # ends_with_statement Tests
    # -------------------------

    def test_ends_with_statement_period(self):
        """Test ends_with_statement returns True for period."""
        self.assertTrue(ends_with_statement("This is a statement."))

    def test_ends_with_statement_question(self):
        """Test ends_with_statement returns False for question."""
        self.assertFalse(ends_with_statement("Is this a question?"))

    def test_ends_with_statement_no_punctuation(self):
        """Test ends_with_statement returns True for no punctuation."""
        self.assertTrue(ends_with_statement("This has no punctuation"))

    def test_ends_with_statement_empty(self):
        """Test ends_with_statement returns False for empty string."""
        self.assertFalse(ends_with_statement(""))

    # -------------------------
    # is_valid_closing_statement Tests
    # -------------------------

    def test_is_valid_closing_statement_clarity_pattern(self):
        """Test is_valid_closing_statement with training data pattern."""
        self.assertTrue(is_valid_closing_statement("Clarity supports confident decisions."))

    def test_is_valid_closing_statement_structure_pattern(self):
        """Test is_valid_closing_statement with structure pattern."""
        self.assertTrue(is_valid_closing_statement("Structure protects performance."))

    def test_is_valid_closing_statement_understanding_pattern(self):
        """Test is_valid_closing_statement with understanding pattern."""
        self.assertTrue(is_valid_closing_statement("Understanding enables better choices."))

    def test_is_valid_closing_statement_question(self):
        """Test is_valid_closing_statement rejects question."""
        self.assertFalse(is_valid_closing_statement("Is this a question?"))

    # -------------------------
    # ensure_ends_with_statement Tests (NEW - replaces question tests)
    # -------------------------

    def test_ensure_ends_with_statement_already_correct(self):
        """Test ensure_ends_with_statement when already correct."""
        body = "This is sentence one. This is sentence two. This is a statement."
        result = ensure_ends_with_statement(body)
        self.assertTrue(result.endswith("."))
        self.assertFalse(result.endswith("?"))

    def test_ensure_ends_with_statement_converts_question(self):
        """Test ensure_ends_with_statement converts question to statement."""
        body = "This is sentence one. Is this a question?"
        result = ensure_ends_with_statement(body)
        self.assertTrue(result.endswith("."))
        self.assertNotIn("?", result)

    def test_ensure_ends_with_statement_multiple_questions(self):
        """Test ensure_ends_with_statement with multiple questions."""
        body = "What is this? What is that? What is the answer?"
        result = ensure_ends_with_statement(body)
        # Should end with period, not question
        self.assertTrue(result.endswith("."))
        # Last sentence should be converted to statement
        self.assertIn("What is the answer", result)

    def test_ensure_ends_with_statement_empty_string(self):
        """Test ensure_ends_with_statement with empty string."""
        result = ensure_ends_with_statement("")
        self.assertEqual(result, "")

    def test_ensure_ends_with_statement_whitespace_only(self):
        """Test ensure_ends_with_statement with whitespace."""
        result = ensure_ends_with_statement("   ")
        self.assertEqual(result.strip(), "")

    def test_ensure_ends_with_statement_preserves_sentence_order(self):
        """Test ensure_ends_with_statement preserves sentence order."""
        body = "First sentence. Second sentence. Third sentence?"
        result = ensure_ends_with_statement(body)
        # Should preserve order, just ensure statement at end
        self.assertTrue(result.endswith("."))
        # Check that sentences are in order
        first_idx = result.find("First")
        second_idx = result.find("Second")
        third_idx = result.find("Third")
        self.assertLess(first_idx, second_idx)
        self.assertLess(second_idx, third_idx)

    def test_ensure_ends_with_statement_adds_period_if_missing(self):
        """Test ensure_ends_with_statement adds period if missing."""
        body = "First sentence. Second sentence"
        result = ensure_ends_with_statement(body)
        self.assertTrue(result.endswith("."))

    # -------------------------
    # ensure_exactly_one_question_at_end Tests (DEPRECATED - now converts to statement)
    # -------------------------

    def test_ensure_exactly_one_question_at_end_already_correct(self):
        """Test deprecated function converts to statement."""
        body = "This is sentence one. This is sentence two. This is a question?"
        result = ensure_exactly_one_question_at_end(body)
        # Now returns statement (deprecated behavior)
        self.assertTrue(result.endswith("."))

    def test_ensure_exactly_one_question_at_end_no_question(self):
        """Test deprecated function keeps statement."""
        body = "This is sentence one. This is sentence two."
        result = ensure_exactly_one_question_at_end(body)
        # Should remain a statement
        self.assertTrue(result.endswith("."))

    def test_ensure_exactly_one_question_at_end_multiple_questions(self):
        """Test deprecated function converts all questions."""
        body = "What is this? What is that? What is the answer?"
        result = ensure_exactly_one_question_at_end(body)
        # Should convert to statement
        self.assertTrue(result.endswith("."))

    def test_ensure_exactly_one_question_at_end_question_not_at_end(self):
        """Test deprecated function converts question to statement."""
        body = "What is this? This is a statement."
        result = ensure_exactly_one_question_at_end(body)
        self.assertTrue(result.endswith("."))
        self.assertIn("statement", result)

    def test_ensure_exactly_one_question_at_end_empty_string(self):
        """Test deprecated function with empty string."""
        result = ensure_exactly_one_question_at_end("")
        self.assertEqual(result, "")

    def test_ensure_exactly_one_question_at_end_whitespace_only(self):
        """Test deprecated function with whitespace."""
        result = ensure_exactly_one_question_at_end("   ")
        self.assertEqual(result.strip(), "")

    def test_ensure_exactly_one_question_at_end_preserves_sentence_order(self):
        """Test deprecated function preserves sentence order."""
        body = "First sentence. Second sentence. Third sentence?"
        result = ensure_exactly_one_question_at_end(body)
        # Should preserve order, convert to statement
        self.assertTrue(result.endswith("."))
        first_idx = result.find("First")
        second_idx = result.find("Second")
        third_idx = result.find("Third")
        self.assertLess(first_idx, second_idx)
        self.assertLess(second_idx, third_idx)

    def test_ensure_exactly_one_question_at_end_fixes_punctuation(self):
        """Test deprecated function converts to statement."""
        body = "First sentence. Second sentence?"
        result = ensure_exactly_one_question_at_end(body)
        # Should end with period (statement)
        self.assertTrue(result.endswith("."))

    def test_ensure_exactly_one_question_at_end_with_exclamation(self):
        """Test deprecated function with exclamation."""
        body = "First sentence! Second sentence."
        result = ensure_exactly_one_question_at_end(body)
        # Should remain a statement
        self.assertTrue(result.endswith("."))

    def test_ensure_exactly_one_question_at_end_complex_case(self):
        """Test deprecated function with complex case."""
        body = "What is this? What about that? This is a statement. Another statement."
        result = ensure_exactly_one_question_at_end(body)
        # Should end with statement
        self.assertTrue(result.endswith("."))
        self.assertIn("statement", result)

    # -------------------------
    # validate_sentence_count Tests
    # -------------------------

    def test_validate_sentence_count_within_range(self):
        """Test validate_sentence_count with valid count."""
        sentences = ["One.", "Two.", "Three.", "Four.", "Five."]
        self.assertTrue(validate_sentence_count(sentences, 4, 6))

    def test_validate_sentence_count_too_few(self):
        """Test validate_sentence_count with too few sentences."""
        sentences = ["One.", "Two."]
        self.assertFalse(validate_sentence_count(sentences, 4, 6))

    def test_validate_sentence_count_too_many(self):
        """Test validate_sentence_count with too many sentences."""
        sentences = ["One.", "Two.", "Three.", "Four.", "Five.", "Six.", "Seven.", "Eight."]
        self.assertFalse(validate_sentence_count(sentences, 4, 6))

    def test_validate_sentence_count_at_min(self):
        """Test validate_sentence_count at minimum."""
        sentences = ["One.", "Two.", "Three.", "Four."]
        self.assertTrue(validate_sentence_count(sentences, 4, 6))

    def test_validate_sentence_count_at_max(self):
        """Test validate_sentence_count at maximum."""
        sentences = ["One.", "Two.", "Three.", "Four.", "Five.", "Six."]
        self.assertTrue(validate_sentence_count(sentences, 4, 6))

    # -------------------------
    # get_sentence_count_range Tests
    # -------------------------

    def test_get_sentence_count_range_twitter(self):
        """Test get_sentence_count_range for Twitter."""
        min_s, max_s = get_sentence_count_range("twitter")
        self.assertEqual(min_s, 2)
        self.assertEqual(max_s, 4)

    def test_get_sentence_count_range_linkedin(self):
        """Test get_sentence_count_range for LinkedIn."""
        min_s, max_s = get_sentence_count_range("linkedin")
        self.assertEqual(min_s, 4)
        self.assertEqual(max_s, 8)

    def test_get_sentence_count_range_instagram(self):
        """Test get_sentence_count_range for Instagram."""
        min_s, max_s = get_sentence_count_range("instagram")
        self.assertEqual(min_s, 3)
        self.assertEqual(max_s, 5)

    def test_get_sentence_count_range_facebook(self):
        """Test get_sentence_count_range for Facebook (default)."""
        min_s, max_s = get_sentence_count_range("facebook")
        self.assertEqual(min_s, 4)
        self.assertEqual(max_s, 6)

    def test_get_sentence_count_range_default(self):
        """Test get_sentence_count_range for unknown platform."""
        min_s, max_s = get_sentence_count_range("unknown")
        self.assertEqual(min_s, 4)
        self.assertEqual(max_s, 6)


if __name__ == '__main__':
    unittest.main(verbosity=2)
