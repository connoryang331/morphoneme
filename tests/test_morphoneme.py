"""Unit tests — morph-query core functionality."""

import unittest
import os
import tempfile
import json
from pathlib import Path

from morphoneme import MQ


class TestMQ(unittest.TestCase):
    """All tests share one MQ instance to avoid repeated DB opens."""

    @classmethod
    def setUpClass(cls):
        cls.mq = MQ()

    # ── core search ──────────────────────────────────────

    def test_search_both(self):
        results = self.mq.search("run")
        self.assertIsInstance(results, list)
        for r in results:
            self.assertIn("word", r)
            self.assertIn("umlabeller", r)
            self.assertIn("citylex", r)

    def test_search_umlabeller_source(self):
        """source controls which column to search, seg controls which columns to return (default both=all 3)."""
        results = self.mq.search("run", source="umlabeller")
        self.assertIsInstance(results, list)
        for r in results:
            self.assertIn("word", r)

    def test_search_citylex_only(self):
        results = self.mq.search("run", source="citylex", seg="citylex")
        self.assertIsInstance(results, list)
        for r in results:
            self.assertIn("word", r)
            self.assertIn("citylex", r)
            self.assertNotIn("umlabeller", r)

    def test_search_limit(self):
        results = self.mq.search("ion", limit=5)
        self.assertLessEqual(len(results), 5)

    def test_search_exact(self):
        results = self.mq.search("ch", exact=True)
        self.assertIsInstance(results, list)
        words = [r["word"] for r in results]
        self.assertIn("chad", words)
        self.assertIn("cham", words)
        # Should NOT match words that contain 'ch' as a substring of a larger morpheme (like character)
        self.assertNotIn("characteristic", words)

    def test_search_wildcard(self):
        results = self.mq.search("*ough")
        self.assertIsInstance(results, list)
        words = [r["word"] for r in results]
        self.assertIn("rough", words)
        self.assertIn("cough", words)
        self.assertNotIn("ought", words)

        results_start = self.mq.search("ough*")
        self.assertIsInstance(results_start, list)
        words_start = [r["word"] for r in results_start]
        self.assertIn("ought", words_start)
        self.assertNotIn("rough", words_start)

    # ── semantic aliases ──────────────────────────────────────

    def test_words_with_prefix(self):
        results = self.mq.words_with_prefix("un")
        self.assertIsInstance(results, list)

    def test_words_with_suffix(self):
        results = self.mq.words_with_suffix("ing")
        self.assertIsInstance(results, list)

    def test_words_with_root(self):
        results = self.mq.words_with_root("believe")
        self.assertIsInstance(results, list)

    # ── morpheme-level search ────────────────────────────────────

    def test_words_with_deri(self):
        results = self.mq.words_with_deri("able")
        self.assertIsInstance(results, list)

    def test_words_with_inf(self):
        results = self.mq.words_with_inf("ed")
        self.assertIsInstance(results, list)

    # ── morpheme segmentation ──────────────────────────────────────

    def test_morph_seg_simple(self):
        seg = self.mq.morph_seg("running")
        if seg:
            self.assertIn("run", seg)

    _NOT_A_WORD = "qwertyuioppasdfghjklzxcvbnm"

    def test_morph_seg_not_found(self):
        seg = self.mq.morph_seg(self._NOT_A_WORD)
        self.assertIsNone(seg)

    # ── morpheme count ──────────────────────────────────────

    def test_morph_count(self):
        count = self.mq.morph_count("unbelievable")
        if count is not None:
            self.assertGreater(count, 1)

    def test_morph_count_not_found(self):
        count = self.mq.morph_count(self._NOT_A_WORD)
        self.assertIsNone(count)

    # ── Lemma ─────────────────────────────────────────

    def test_lemma(self):
        lemma = self.mq.lemma("running")
        if lemma:
            self.assertIsInstance(lemma, str)

    def test_lemma_not_found(self):
        lemma = self.mq.lemma(self._NOT_A_WORD)
        self.assertIsNone(lemma)

    # ── full morphology structure ──────────────────────────────────

    def test_word_morph(self):
        r = self.mq.word_morph("cats")
        if r and r.get("seg"):
            self.assertIn("word", r)
            self.assertIn("seg", r)
            self.assertIn("prefixes", r)
            self.assertIn("roots", r)
            self.assertIn("suffixes", r)

    def test_word_morph_not_found(self):
        r = self.mq.word_morph(self._NOT_A_WORD)
        self.assertIsNotNone(r)
        self.assertIsNone(r.get("seg"))

    # ── count ──────────────────────────────────────────

    def test_word_count(self):
        n = self.mq.word_count("ion")
        self.assertIsInstance(n, int)
        self.assertGreater(n, 0)

    # ── random sampling ──────────────────────────────────────

    def test_sample(self):
        results = self.mq.sample(5)
        self.assertEqual(len(results), 5)

    # ── batch processing ──────────────────────────────────────

    def test_batch_words_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            input_file = Path(tmp) / "words.txt"
            input_file.write_text("running\ncats\nunbelievable\n", encoding="utf-8")
            output = self.mq.batch_words(str(input_file), mode="seg", fmt="json")
            self.assertTrue(Path(output).exists())
            data = json.loads(Path(output).read_text(encoding="utf-8"))
            self.assertIsInstance(data, list)
            self.assertEqual(len(data), 3)

    def test_batch_words_csv(self):
        with tempfile.TemporaryDirectory() as tmp:
            input_file = Path(tmp) / "words.txt"
            input_file.write_text("running\ncats\n", encoding="utf-8")
            output = self.mq.batch_words(str(input_file), mode="seg", fmt="csv")
            self.assertTrue(Path(output).exists())

    def test_batch_words_morph(self):
        with tempfile.TemporaryDirectory() as tmp:
            input_file = Path(tmp) / "words.txt"
            input_file.write_text("running\n", encoding="utf-8")
            output = self.mq.batch_words(str(input_file), mode="morph", fmt="json")
            data = json.loads(Path(output).read_text(encoding="utf-8"))
            self.assertIn("root", data[0])

    # ── inflectional suffix filter ──────────────────────────────────

    def test_exclude_inf(self):
        results_with = self.mq.search("ed", limit=20)
        results_without = self.mq.search("ed", limit=20, exclude_inf=True)
        # after filtering should be <= before filtering
        self.assertGreaterEqual(len(results_with), len(results_without))

    # ── _parse_citylex ────────────────────────────────

    def test_parse_citylex_single_root(self):
        p, r, s = self.mq._parse_citylex("{norm--al}")
        self.assertEqual(r, ["norm"])
        self.assertEqual(s, ["al"])

    def test_parse_citylex_compound(self):
        p, r, s = self.mq._parse_citylex("{abs--ent}{mind}>ed>>ly>")
        self.assertEqual(r, ["abs", "mind"])

    # ── segmentation normalisation ────────────────────────────────────

    def test_norm_uml(self):
        result = self.mq._norm_uml("un @@believ @@able")
        self.assertEqual(result, "un-believ-able")

    def test_norm_city(self):
        result = self.mq._norm_city("{un--believ--able}")
        self.assertEqual(result, "un-believ-able")

    # ── connection management ──────────────────────────────────────

    def test_context_manager(self):
        with MQ() as mq:
            n = mq.total
            self.assertIsInstance(n, int)
            self.assertGreater(n, 0)

    def test_total(self):
        n = self.mq.total
        self.assertIsInstance(n, int)
        self.assertGreater(n, 0)

    # ── frequency filter tests ──────────────────────────────────
    def test_search_fq_high(self):
        results = self.mq.search("ion", fq="high")
        self.assertGreater(len(results), 0)
        for r in results:
            freq = r.get("frequency")
            if freq is not None:
                self.assertGreaterEqual(freq, 5.0)

    def test_search_fq_medium(self):
        results = self.mq.search("ion", fq="medium")
        self.assertGreater(len(results), 0)
        for r in results:
            freq = r.get("frequency")
            if freq is not None:
                self.assertGreaterEqual(freq, 1.0)
                self.assertLess(freq, 5.0)

    def test_search_fq_low(self):
        results = self.mq.search("ion", fq="low")
        self.assertGreater(len(results), 0)
        for r in results:
            freq = r.get("frequency")
            if freq is not None:
                self.assertGreaterEqual(freq, 0.1)
                self.assertLess(freq, 1.0)

    def test_search_fq_rare(self):
        results = self.mq.search("ion", fq="rare")
        self.assertGreater(len(results), 0)
        for r in results:
            freq = r.get("frequency")
            if freq is not None:
                self.assertGreater(freq, 0.0)
                self.assertLess(freq, 0.1)

    def test_search_fq_zero(self):
        results = self.mq.search("ion", fq="zero")
        self.assertGreater(len(results), 0)
        for r in results:
            freq = r.get("frequency")
            if freq is not None:
                self.assertEqual(freq, 0.0)

    def test_search_fq_invalid(self):
        with self.assertRaises(ValueError):
            self.mq.search("ion", fq="invalid_value")

    def test_words_with_prefix_fq(self):
        results = self.mq.words_with_prefix("ab", fq="high")
        self.assertGreater(len(results), 0)
        for r in results:
            freq = r.get("frequency")
            if freq is not None:
                self.assertGreaterEqual(freq, 5.0)

    def test_word_count_fq(self):
        total_count = self.mq.word_count("ion")
        high_count = self.mq.word_count("ion", fq="high")
        medium_count = self.mq.word_count("ion", fq="medium")
        low_count = self.mq.word_count("ion", fq="low")
        rare_count = self.mq.word_count("ion", fq="rare")
        zero_count = self.mq.word_count("ion", fq="zero")
        
        self.assertEqual(high_count + medium_count + low_count + rare_count + zero_count, total_count)

    def test_sample_fq(self):
        results = self.mq.sample(5, fq="medium")
        self.assertEqual(len(results), 5)
        for r in results:
            freq = r.get("frequency")
            if freq is not None:
                self.assertGreaterEqual(freq, 1.0)
                self.assertLess(freq, 5.0)


if __name__ == "__main__":
    unittest.main()
