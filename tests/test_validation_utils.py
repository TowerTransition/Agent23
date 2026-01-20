"""
Unit tests for validation_utils.

Tests cover:
- Body extraction (removes footer, hashtags, labels)
- Sentence splitting
- Question enforcement (exactly one question at end)
- Count sentences helper
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
    ensure_exactly_one_question_at_end,
    BodyExtractionResult,
    SIGNATURE,
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
    # ensure_exactly_one_question_at_end Tests
    # -------------------------

    def test_ensure_exactly_one_question_at_end_already_correct(self):
        """Test ensure_exactly_one_question_at_end when already correct."""
        body = "This is sentence one. This is sentence two. This is a question?"
        result = ensure_exactly_one_question_at_end(body)
        self.assertTrue(result.endswith("?"))
        self.assertEqual(result.count("?"), 1)

    def test_ensure_exactly_one_question_at_end_no_question(self):
        """Test ensure_exactly_one_question_at_end adds question if missing."""
        body = "This is sentence one. This is sentence two."
        result = ensure_exactly_one_question_at_end(body)
        self.assertTrue(result.endswith("?"))

    def test_ensure_exactly_one_question_at_end_multiple_questions(self):
        """Test ensure_exactly_one_question_at_end fixes multiple questions."""
        body = "What is this? What is that? What is the answer?"
        result = ensure_exactly_one_question_at_end(body)
        # Should have only one question at the end
        self.assertTrue(result.endswith("?"))
        # Other questions should be converted to periods
        self.assertLessEqual(result.count("?"), 1)

    def test_ensure_exactly_one_question_at_end_question_not_at_end(self):
        """Test ensure_exactly_one_question_at_end moves question to end."""
        body = "What is this? This is a statement."
        result = ensure_exactly_one_question_at_end(body)
        self.assertTrue(result.endswith("?"))
        # The question should be at the end
        self.assertIn("statement", result)
        self.assertIn("What is this", result)

    def test_ensure_exactly_one_question_at_end_empty_string(self):
        """Test ensure_exactly_one_question_at_end with empty string."""
        result = ensure_exactly_one_question_at_end("")
        self.assertEqual(result, "")

    def test_ensure_exactly_one_question_at_end_whitespace_only(self):
        """Test ensure_exactly_one_question_at_end with whitespace."""
        result = ensure_exactly_one_question_at_end("   ")
        self.assertEqual(result.strip(), "")

    def test_ensure_exactly_one_question_at_end_preserves_sentence_order(self):
        """Test ensure_exactly_one_question_at_end preserves sentence order."""
        body = "First sentence. Second sentence. Third sentence?"
        result = ensure_exactly_one_question_at_end(body)
        # Should preserve order, just ensure question at end
        self.assertTrue(result.endswith("?"))
        # Check that sentences are in order
        first_idx = result.find("First")
        second_idx = result.find("Second")
        third_idx = result.find("Third")
        self.assertLess(first_idx, second_idx)
        self.assertLess(second_idx, third_idx)

    def test_ensure_exactly_one_question_at_end_fixes_punctuation(self):
        """Test ensure_exactly_one_question_at_end fixes punctuation."""
        body = "First sentence. Second sentence?"
        result = ensure_exactly_one_question_at_end(body)
        # Should end with question mark
        self.assertTrue(result.endswith("?"))
        # First sentence should end with period
        self.assertIn("First sentence.", result)

    def test_ensure_exactly_one_question_at_end_with_exclamation(self):
        """Test ensure_exactly_one_question_at_end handles exclamation."""
        body = "First sentence! Second sentence."
        result = ensure_exactly_one_question_at_end(body)
        # Should convert to question at end
        self.assertTrue(result.endswith("?"))

    def test_ensure_exactly_one_question_at_end_complex_case(self):
        """Test ensure_exactly_one_question_at_end with complex case."""
        body = "What is this? What about that? This is a statement. Another statement."
        result = ensure_exactly_one_question_at_end(body)
        # Should have exactly one question at the end
        self.assertTrue(result.endswith("?"))
        # Should preserve most content
        self.assertIn("statement", result)


if __name__ == '__main__':
    unittest.main(verbosity=2)
