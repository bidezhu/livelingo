import queue
import unittest

from config import PUBLIC_HEALTH_HOT_WORDS, load_config
from live_translate_engine import (
    DualLiveTranslateEngine,
    LiveTranslateEngine,
    count_sentences,
    language_from_text,
    reverse_hot_words,
    text_matches_language,
)
from subtitle_ui import clean_subtitle_text


class LiveTranslateEngineTest(unittest.TestCase):
    def test_count_sentences_handles_chinese_and_english(self):
        text = "大家上午好。欢迎参加会议！We will begin now. Please take your seats."
        self.assertEqual(count_sentences(text), 4)

    def test_session_update_enables_source_transcript_and_translation(self):
        engine = LiveTranslateEngine(
            api_key="test",
            source_language="zh",
            target_language="en",
            hot_words={"人工智能": "Artificial Intelligence"},
        )

        payload = engine._build_session_update()

        self.assertEqual(payload["type"], "session.update")
        session = payload["session"]
        self.assertEqual(session["modalities"], ["text"])
        self.assertEqual(session["input_audio_transcription"]["model"], "qwen3-asr-flash-realtime")
        self.assertEqual(session["input_audio_transcription"]["language"], "zh")
        self.assertEqual(session["translation"]["language"], "en")
        self.assertEqual(
            session["translation"]["corpus"]["phrases"],
            {"人工智能": "Artificial Intelligence"},
        )

    def test_public_health_hot_words_are_enabled_by_default(self):
        cfg = load_config()

        self.assertIn("公共卫生", PUBLIC_HEALTH_HOT_WORDS)
        self.assertEqual(cfg["hot_words"]["公共卫生"], "public health")
        self.assertEqual(cfg["hot_words"]["含糖饮料税"], "sugar-sweetened beverage tax")

    def test_subtitle_cleaner_removes_common_fillers(self):
        self.assertEqual(clean_subtitle_text("嗯，公共卫生政策正在发生变化。"), "公共卫生政策正在发生变化。")
        self.assertEqual(clean_subtitle_text("Um, public health policy is changing."), "public health policy is changing.")
        self.assertEqual(clean_subtitle_text("这个问题很重要。"), "这个问题很重要。")

    def test_emit_result_pairs_chinese_source_with_english_translation(self):
        result_queue = queue.Queue()
        engine = LiveTranslateEngine(
            api_key="test",
            source_language="zh",
            target_language="en",
            result_queue=result_queue,
        )
        with engine._state_lock:
            engine._last_transcript = "大家上午好。欢迎参加会议。"
            engine._last_transcript_language = "zh"
            engine._last_translation = "Good morning, everyone. Welcome to the meeting."

        engine._emit_result()
        result = result_queue.get_nowait()

        self.assertEqual(result["type"], "final")
        self.assertEqual(result["direction"], "zh->en")
        self.assertEqual(result["cn_text"], "大家上午好。欢迎参加会议。")
        self.assertEqual(result["en_text"], "Good morning, everyone. Welcome to the meeting.")

    def test_transcript_delta_emits_streaming_partial(self):
        result_queue = queue.Queue()
        engine = LiveTranslateEngine(
            api_key="test",
            source_language="zh",
            target_language="en",
            result_queue=result_queue,
        )

        engine._handle_transcript_delta({"text": "公共卫生政策正在发生变化"})

        result = result_queue.get_nowait()
        self.assertEqual(result["type"], "partial")
        self.assertEqual(result["direction"], "zh->en")
        self.assertEqual(result["cn_text"], "公共卫生政策正在发生变化")
        self.assertEqual(result["en_text"], "")

    def test_translation_delta_updates_streaming_partial(self):
        result_queue = queue.Queue()
        engine = LiveTranslateEngine(
            api_key="test",
            source_language="en",
            target_language="zh",
            result_queue=result_queue,
        )
        with engine._state_lock:
            engine._last_transcript = "Public health policy is changing."
            engine._last_transcript_language = "en"

        engine._handle_translation_delta({"text": "公共卫生政策正在发生变化。"})

        result = result_queue.get_nowait()
        self.assertEqual(result["type"], "partial")
        self.assertEqual(result["direction"], "en->zh")
        self.assertEqual(result["cn_text"], "公共卫生政策正在发生变化。")
        self.assertEqual(result["en_text"], "Public health policy is changing.")

    def test_emit_result_pairs_english_source_with_chinese_translation(self):
        result_queue = queue.Queue()
        engine = LiveTranslateEngine(
            api_key="test",
            source_language="en",
            target_language="zh",
            result_queue=result_queue,
        )
        with engine._state_lock:
            engine._last_transcript = "Good morning, everyone. Welcome to the meeting."
            engine._last_transcript_language = "en"
            engine._last_translation = "大家上午好。欢迎参加会议。"

        engine._emit_result()
        result = result_queue.get_nowait()

        self.assertEqual(result["direction"], "en->zh")
        self.assertEqual(result["cn_text"], "大家上午好。欢迎参加会议。")
        self.assertEqual(result["en_text"], "Good morning, everyone. Welcome to the meeting.")

    def test_emit_result_ignores_wrong_source_language(self):
        result_queue = queue.Queue()
        engine = LiveTranslateEngine(
            api_key="test",
            source_language="zh",
            target_language="en",
            result_queue=result_queue,
        )
        with engine._state_lock:
            engine._last_transcript = "Good morning, everyone."
            engine._last_transcript_language = "en"
            engine._last_translation = "大家上午好。"

        engine._emit_result()

        self.assertTrue(result_queue.empty())

    def test_emit_result_rejects_chinese_text_from_english_direction_even_if_server_says_en(self):
        result_queue = queue.Queue()
        engine = LiveTranslateEngine(
            api_key="test",
            source_language="en",
            target_language="zh",
            result_queue=result_queue,
        )
        with engine._state_lock:
            engine._last_transcript = "什么是超导体？它为什么重要？"
            engine._last_transcript_language = "en"
            engine._last_translation = "What is a superconductor? Why does it matter?"

        engine._emit_result()

        self.assertTrue(result_queue.empty())

    def test_emit_result_waits_for_translation_before_final_output(self):
        result_queue = queue.Queue()
        engine = LiveTranslateEngine(
            api_key="test",
            source_language="en",
            target_language="zh",
            result_queue=result_queue,
        )
        with engine._state_lock:
            engine._last_transcript = "Good morning, everyone."
            engine._last_transcript_language = "en"
            engine._last_translation = ""

        engine._emit_result()

        self.assertTrue(result_queue.empty())

    def test_language_detection_allows_english_with_small_chinese_insert(self):
        text = "The Qwen 模型 is useful for bilingual meetings."

        self.assertEqual(language_from_text(text), "en")
        self.assertTrue(text_matches_language(text, "en"))
        self.assertFalse(text_matches_language(text, "zh"))

    def test_language_mode_limits_active_direction(self):
        engine = DualLiveTranslateEngine(api_key="test", language_mode="en")

        active = engine._active_pairs()

        self.assertEqual(len(active), 1)
        self.assertIs(active[0][0], engine.en_to_zh)

    def test_reverse_hot_words_for_english_to_chinese_session(self):
        self.assertEqual(
            reverse_hot_words({"含糖饮料": "sugar-sweetened beverages"}),
            {"sugar-sweetened beverages": "含糖饮料"},
        )


if __name__ == "__main__":
    unittest.main()
