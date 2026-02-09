"""Tests pour src/utils/retry.py."""

import time

import pytest

from src.utils.retry import retry_with_backoff


class TestRetryWithBackoff:
    """Tests du décorateur retry."""

    def test_success_first_try(self):
        call_count = 0

        @retry_with_backoff(max_retries=3, initial_delay=0.01)
        def succeed():
            nonlocal call_count
            call_count += 1
            return "ok"

        assert succeed() == "ok"
        assert call_count == 1

    def test_success_after_failures(self):
        call_count = 0

        @retry_with_backoff(max_retries=3, initial_delay=0.01, backoff_factor=1.0)
        def fail_twice():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("fail")
            return "ok"

        assert fail_twice() == "ok"
        assert call_count == 3

    def test_all_retries_exhausted(self):
        @retry_with_backoff(max_retries=2, initial_delay=0.01)
        def always_fail():
            raise RuntimeError("boom")

        with pytest.raises(RuntimeError, match="boom"):
            always_fail()

    def test_only_catches_specified_exceptions(self):
        @retry_with_backoff(max_retries=3, initial_delay=0.01, exceptions=(ValueError,))
        def raise_type_error():
            raise TypeError("wrong type")

        with pytest.raises(TypeError):
            raise_type_error()

    def test_backoff_increases_delay(self):
        call_times = []

        @retry_with_backoff(max_retries=3, initial_delay=0.05, backoff_factor=2.0)
        def track_time():
            call_times.append(time.time())
            if len(call_times) < 3:
                raise ValueError("fail")
            return "ok"

        track_time()
        assert len(call_times) == 3
        # Deuxième délai devrait être ~2x le premier
        delay1 = call_times[1] - call_times[0]
        delay2 = call_times[2] - call_times[1]
        assert delay2 > delay1 * 1.5  # Tolérance pour timing OS
