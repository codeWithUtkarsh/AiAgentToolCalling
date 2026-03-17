"""Tests for retry utility."""

import pytest
from unittest.mock import MagicMock

from src.utils.retry import retry_with_backoff


class TestRetryWithBackoff:
    def test_success_no_retry(self):
        func = MagicMock(return_value="ok")
        decorated = retry_with_backoff(max_retries=3)(func)
        assert decorated() == "ok"
        assert func.call_count == 1

    def test_retry_then_success(self):
        func = MagicMock(side_effect=[ValueError("fail"), ValueError("fail"), "ok"])
        decorated = retry_with_backoff(
            max_retries=3,
            base_delay=0.01,
            retryable_exceptions=(ValueError,),
        )(func)
        assert decorated() == "ok"
        assert func.call_count == 3

    def test_max_retries_exceeded(self):
        func = MagicMock(side_effect=ValueError("always fails"))
        decorated = retry_with_backoff(
            max_retries=2,
            base_delay=0.01,
            retryable_exceptions=(ValueError,),
        )(func)
        with pytest.raises(ValueError, match="always fails"):
            decorated()
        assert func.call_count == 3  # initial + 2 retries

    def test_non_retryable_exception_raises_immediately(self):
        func = MagicMock(side_effect=TypeError("wrong type"))
        decorated = retry_with_backoff(
            max_retries=3,
            base_delay=0.01,
            retryable_exceptions=(ValueError,),
        )(func)
        with pytest.raises(TypeError):
            decorated()
        assert func.call_count == 1

    def test_preserves_function_name(self):
        @retry_with_backoff(max_retries=1)
        def my_function():
            pass

        assert my_function.__name__ == "my_function"
