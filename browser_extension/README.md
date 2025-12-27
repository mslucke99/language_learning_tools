# Browser extension for the language_learning_tools repo

A browser extension that allows you to import words and sentences into the language learning tools app for further study.

## What It Does

**Two simple features:**
1. 📝 **Add as Word** - Save a word for later study
2. 💬 **Add as Sentence** - Save a sentence for later study

That's it. Simple, focused, debuggable.

## How to Use

### Method 1: Selection Popup (Recommended)
1. Select any text on a webpage
2. Two buttons appear: "📝 Add as Word" or "💬 Add as Sentence"
3. Click the one you want
4. Done! Notification confirms it was saved

### Method 2: Right-Click Menu
1. Right-click on selected text
2. Choose "Add as Word" or "Add as Sentence"
3. Content is saved to your app

### Popup Interface
- Shows if the API is connected
- Shows basic instructions
- That's all you need!

## What Gets Saved

For each import, the app receives:
- The text you selected
- The webpage URL (so you know where it came from)
- The webpage title (for context)
- Whether it's a word or sentence

## System Requirements

- Chrome/Chromium browser
- Flask API running on `http://localhost:5000`
- API must have `/api/health` and `/api/imported` endpoints

## Installation

1. Open Chrome Extensions (chrome://extensions/)
2. Enable "Developer mode" (top right)
3. Click "Load unpacked"
4. Select this folder
5. Done!

## Architecture

```
┌─────────────────────────────────────────┐
│      Webpage (Any Website)              │
│  ┌───────────────────────────────────┐  │
│  │ Select Text → Two Buttons Appear  │  │
│  │  [📝 Add as Word] [💬 Add as Sentence] │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
         ↓ User Clicks Button
┌─────────────────────────────────────────┐
│   Browser Extension (This Code)         │
│  - Detects selection                    │
│  - Shows options                        │
│  - Sends to API                         │
└─────────────────────────────────────────┘
         ↓ POST /api/imported
┌─────────────────────────────────────────┐
│   Your Language Learning App (Flask)    │
│  - Stores the content                   │
│  - Can add definitions, explanations    │
│  - Manages flashcards, study plans      │
└─────────────────────────────────────────┘
```

## File Structure

```
browser_extension/
├── manifest.json          # Extension configuration
├── background.js          # Context menu & API handler
├── content.js             # Detects selection, shows buttons
├── popup.html             # Popup interface
├── popup.js               # Popup logic (API health check)
├── styles.css             # Minimal styling
└── images/                # Extension icons
```

## Code Highlights

### Total: ~463 lines (80% reduction from before)
- **popup.html**: 60 lines - minimal popup UI
- **popup.js**: 33 lines - just API health check
- **content.js**: 170 lines - selection detection and buttons
- **background.js**: 110 lines - API communication
- **styles.css**: 90 lines - basic styling

## Technical Details

See documentation files:
- **SIMPLIFICATION_SUMMARY.md** - What was removed and why
- **REFACTORING_DETAILS.md** - Code comparison, testing checklist
- **API_INTEGRATION.md** - API requirements, database schema, troubleshooting

## Troubleshooting

### Nothing happens when I select text
- Make sure the extension is enabled in chrome://extensions/
- Reload the webpage (sometimes needed after install)
- Check browser console (F12) for errors

### "API Offline" in popup
- Start your Flask API: `python api_server.py`
- Verify it's running on http://localhost:5000
- Check `/api/health` endpoint in your API

### Buttons don't appear
- Try reloading the webpage
- Check that extension has permission for that domain
- Verify content.js is listed under Extension Details

### Error notifications appear
- Check Flask API logs for error details
- Verify `/api/imported` endpoint accepts the data format
- Ensure API database is set up

## Future Enhancements

Once content is in the app, the app can:
- ✓ Create flashcards from words
- ✓ Generate definitions and examples
- ✓ Provide grammar analysis for sentences
- ✓ Track learning progress
- ✓ Enable spaced repetition

This extension is just to get the content into the app. The app does the heavy lifting. This is because I work more with python and would rather debug python than try to debug a mess of Javascript which I would likely just have to do pure vibe coding with.

## License

Same as parent project. See LICENSE file.

---

