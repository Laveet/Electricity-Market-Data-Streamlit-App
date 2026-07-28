
import asyncio
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent))

from src.energy_data_engine.utils.logger import logger
from src.energy_data_engine.utils.retry import async_retry

# Track retry attempts
attempt_counter = 0

@async_retry(retries=3, backoff_factor=1.2, exceptions=(ValueError,))
async def mock_failing_api_call():
    global attempt_counter
    attempt_counter += 1
    logger.info("Executing mock API call...", attempt=attempt_counter)
    
    if attempt_counter < 3:
        raise ValueError("Simulated network timeout/rate limit")
    return "SUCCESS"

async def main():
    print("\n" + "=" * 50)
    print("      STEP 1.3 & 1.4 LOGGING & RETRY TEST HARNESS     ")
    print("=" * 50 + "\n")
    
    result = await mock_failing_api_call()
    assert result == "SUCCESS", "Retry logic failed to return success"
    assert attempt_counter == 3, f"Expected 3 attempts, got {attempt_counter}"
    
    print("\n✅ LOGGING AND ASYNC RETRY UTILITIES VERIFIED SUCCESSFULLY!")

if __name__ == "__main__":
    asyncio.run(main())