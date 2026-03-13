# Tests for Phase 1 Critical Bug Fixes

This directory contains unit and integration tests for the Phase 1 fixes addressing Issues #6, #9, and #10.

## Test Files

### `test_phase1_fixes.py`
Unit tests for individual components:
- `TestChatErrorFix`: Verifies the chat error fix (Issue #6)
- `TestSentenceRelatedItemsFix`: Verifies sentence suggestions display (Issue #9)
- `TestWordsRelatedItemsFix`: Verifies words suggestions handling (Issue #10)

### `test_worker_loop.py`
Integration tests for the background worker:
- Tests that `current_history` is fetched and passed to `send_chat_message`
- Tests that task results include `suggestions` in the correct format

## Running Tests

```bash
# Run all tests
python -m unittest discover tests

# Run specific test file
python -m unittest tests.test_phase1_fixes

# Run specific test class
python -m unittest tests.test_phase1_fixes.TestChatErrorFix

# Run with verbose output
python -m unittest discover tests -v
```

## Test Coverage

### Issue #6: Chat Error Fix
- ✅ Worker loop fetches `current_history` when processing chat tasks
- ✅ `send_chat_message` receives and uses the history parameter

### Issue #9: Sentence Related Items
- ✅ Task status includes `suggestions` with correct structure
- ✅ UI extracts suggestions using the correct key (`suggestions` not `result_extra`)

### Issue #10: Word Related Items
- ✅ `_handle_completed_task` extracts suggestions from task status
- ⚠️ Full UI implementation (similar to sentences) is pending

## Notes

- Tests use mocking to avoid dependencies on actual database or LLM connections
- Integration tests include small sleeps to allow worker thread processing
- UI tests (tkinter) are conceptual/structural due to GUI testing complexity
