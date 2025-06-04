# api/async_rate_limiter.py
import asyncio
from collections import deque
from datetime import datetime, timedelta, timezone
import logging

logger = logging.getLogger(__name__)

class AsyncRateLimiter:
    def __init__(self, max_calls: int, period_seconds: int):
        self.max_calls = max_calls
        self.period = timedelta(seconds=period_seconds)
        self.call_timestamps: deque[datetime] = deque()
        self._lock = asyncio.Lock()
        self.total_calls_made_through_limiter = 0
        logger.info(f"AsyncRateLimiter initialized: Max {self.max_calls} calls per {self.period.total_seconds()} seconds.")

    async def wait_if_needed(self) -> int:
        async with self._lock:
            now = datetime.now(timezone.utc)

            # Remove timestamps older than the rate limit period
            while self.call_timestamps and self.call_timestamps[0] <= now - self.period:
                self.call_timestamps.popleft()

            if len(self.call_timestamps) >= self.max_calls:
                oldest_call_in_window = self.call_timestamps[0] # Should exist if len >= max_calls > 0
                wait_until = oldest_call_in_window + self.period
                wait_duration = (wait_until - now).total_seconds()

                if wait_duration > 0:
                    logger.warning(
                        f"[RateLimiter] Limit reached ({len(self.call_timestamps)}/{self.max_calls}). "
                        f"Waiting for {wait_duration:.2f} seconds."
                    )
                    await asyncio.sleep(wait_duration)
                    # Re-evaluate 'now' after waiting
                    now = datetime.now(timezone.utc)
                    # Clean up again in case other tasks also waited and passed
                    while self.call_timestamps and self.call_timestamps[0] <= now - self.period:
                        self.call_timestamps.popleft()

            # Record the current call timestamp
            self.call_timestamps.append(now)
            self.total_calls_made_through_limiter += 1
            logger.debug(
                f"Call allowed. Current calls in period: {len(self.call_timestamps)}/{self.max_calls}. "
                f"Total calls via limiter: {self.total_calls_made_through_limiter}"
            )
            return self.total_calls_made_through_limiter

RATE_LIMIT_CALLS_DSPY = 8  # Example: Max calls for DSPy interactions
RATE_LIMIT_PERIOD_DSPY = timedelta(minutes=1)

# Global instance (or you can manage instantiation elsewhere)
dspy_rate_limiter = AsyncRateLimiter(max_calls=RATE_LIMIT_CALLS_DSPY, period_seconds=int(RATE_LIMIT_PERIOD_DSPY.total_seconds()))