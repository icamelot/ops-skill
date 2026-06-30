from skills.ops_skill.tools.executor.rate_limiter import RateLimiter


class TestRateLimiter:
    def test_initial_state_not_locked(self):
        limiter = RateLimiter(max_per_hour=10)
        assert limiter.is_locked() is False
        assert limiter.get_remaining() == 10

    def test_check_and_increment_allows_up_to_limit(self):
        limiter = RateLimiter(max_per_hour=5)
        for _ in range(5):
            assert limiter.check_and_increment() is True
        assert limiter.get_remaining() == 0

    def test_exceeded_limit_returns_false(self):
        limiter = RateLimiter(max_per_hour=3)
        for _ in range(3):
            limiter.check_and_increment()
        assert limiter.check_and_increment() is False
        assert limiter.is_locked() is True

    def test_reset_unlocks_and_resets_count(self):
        limiter = RateLimiter(max_per_hour=3)
        for _ in range(3):
            limiter.check_and_increment()
        assert limiter.is_locked() is True

        limiter.reset()
        assert limiter.is_locked() is False
        assert limiter.get_remaining() == 3

    def test_get_remaining_decreases(self):
        limiter = RateLimiter(max_per_hour=5)
        limiter.check_and_increment()
        assert limiter.get_remaining() == 4
        limiter.check_and_increment()
        assert limiter.get_remaining() == 3

    def test_window_expires(self):
        import time

        # Use a very short window for testing
        limiter = RateLimiter(max_per_hour=5)
        # Override the window start to simulate elapsed time
        limiter._window_start = time.monotonic() - 3601  # force expiry

        limiter.check_and_increment()
        assert limiter.get_remaining() == 4  # window should have reset


class TestRateLimiterPersistence:
    def test_save_and_load_state(self, tmp_path):
        """Round-trip: save state, create a new limiter, load state."""
        limiter = RateLimiter(max_per_hour=5)
        limiter.check_and_increment()
        limiter.check_and_increment()
        # 2/5 used, not locked
        state_path = tmp_path / "rate_limit.json"

        limiter.save_state(str(state_path))
        assert state_path.exists()

        # Load into a fresh limiter
        limiter2 = RateLimiter(max_per_hour=5)
        limiter2.load_state(str(state_path))
        assert limiter2.get_remaining() == 3  # 5 - 2
        assert limiter2.is_locked() is False

    def test_load_state_nonexistent_keeps_defaults(self, tmp_path):
        """Loading from a nonexistent file should not change state."""
        limiter = RateLimiter(max_per_hour=5)
        limiter.check_and_increment()
        limiter.load_state(str(tmp_path / "nonexistent.json"))
        assert limiter.get_remaining() == 4  # unchanged

    def test_save_state_preserves_locked(self, tmp_path):
        """When limiter is locked, save/load preserves the lock."""
        limiter = RateLimiter(max_per_hour=3)
        for _ in range(3):
            limiter.check_and_increment()
        assert limiter.is_locked()

        state_path = tmp_path / "locked.json"
        limiter.save_state(str(state_path))

        limiter2 = RateLimiter(max_per_hour=3)
        limiter2.load_state(str(state_path))
        assert limiter2.is_locked() is True
        assert limiter2.get_remaining() == 0

    def test_set_save_path_auto_saves(self, tmp_path):
        """set_save_path triggers auto-save on count changes."""
        state_path = tmp_path / "auto.json"
        limiter = RateLimiter(max_per_hour=5)
        limiter.set_save_path(str(state_path))

        limiter.check_and_increment()
        assert state_path.exists()

        # Verify the content
        import json
        with open(state_path) as f:
            state = json.load(f)
        assert state["count"] == 1
        assert state["locked"] is False

        limiter.check_and_increment()
        with open(state_path) as f:
            state = json.load(f)
        assert state["count"] == 2
