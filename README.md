# Language Learning Tools

A comprehensive Python-based language learning application with AI-powered features for vocabulary study, sentence mining, grammar learning, and immersive reading.

## Features

### Core Learning Features

- **📚 Flashcard Decks**: Create and study flashcard decks with spaced repetition
- **📖 Immersive Reading Mode**: Import and read full articles, stories, or books with AI assistance
- **📝 Study Tools**: Comprehensive vocabulary and sentence study interface
- **📊 Practice Quiz**: Generate and take adaptive quizzes based on your knowledge
- **✍️ Writing Lab**: Practice writing with AI feedback and corrections
- **💬 AI Tutor Chat**: Have conversations with an AI tutor in your target language
- **🎙️ Pronunciation Lab**: Practice pronunciation with audio feedback
- **🕸️ Knowledge Graph**: Visualize your vocabulary as a semantic network

### Advanced Features

- **Sentence Mining**: Extract sentences from various sources for study
- **Grammar Book**: Organized grammar reference with examples
- **Audio Review**: Review vocabulary with audio pronunciation
- **Reading Analytics**: Track reading speed, comprehension, and vocabulary growth
- **Vocabulary Extraction**: Automatically extract and track new words from reading
- **Cloud Sync**: Sync your progress across devices with Firestore
- **Browser Extension**: Mine sentences directly from web pages

## Quick Start

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd language_learning_tools
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
python src/main.py
```

### First Steps

1. **Set Your Study Language**: Choose your target language in Settings
2. **Configure AI**: Set up your preferred AI provider (Gemini, OpenAI, or Ollama)
3. **Create a Deck**: Start with a flashcard deck or import content
4. **Try Reading Mode**: Import an article or story to practice reading

## Reading Mode Guide

The Immersive Reading Mode is a powerful feature for language learners:

### Importing Content

1. Click **📖 Reading Mode** from the home dashboard (or press Ctrl+R)
2. Go to the **📥 Import Content** tab
3. Choose to paste content or import from a file
4. **Important**: Confirm you have legal rights to the content
5. Click Import

### Reading Your Content

1. Open the **📚 My Library** tab to see imported content
2. Double-click any item to start reading
3. Use the **📖 Read** tab to:
   - Look up word definitions
   - Add bookmarks and notes
   - Track your reading progress
   - View comprehension statistics

### Vocabulary Extraction

- Words you look up are automatically tracked
- Add looked-up words to flashcards with one click
- Export vocabulary for use in other study tools
- Track your reading streaks and statistics

### Legal Requirements

**Important**: You are responsible for ensuring you have legal rights to import content.

Acceptable sources:
- ✓ Content you created yourself
- ✓ Public domain works (Project Gutenberg, Internet Archive)
- ✓ Creative Commons licensed content
- ✓ Content with explicit permission

Prohibited:
- ✗ Copyrighted material without permission
- ✗ Commercial use of imported content

See [Legal Compliance Guide](docs/legal/reading_mode_compliance.md) for details.

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| Ctrl+D | Flashcard Decks |
| Ctrl+S | Study Tools |
| Ctrl+C | AI Tutor Chat |
| Ctrl+W | Writing Lab |
| Ctrl+Q | Practice Quiz |
| Ctrl+R | Reading Mode |

## Documentation

- **[User Guide](docs/user_guides/reading_mode.md)**: Complete guide to Reading Mode features
- **[Legal Compliance](docs/legal/reading_mode_compliance.md)**: Legal requirements and fair use guidelines
- **[Developer Documentation](docs/developer/reading_mode_architecture.md)**: Architecture and technical details
- **[Requirements Document](.kiro/specs/immersive-reading-mode/requirements.md)**: Detailed feature requirements
- **[Design Document](.kiro/specs/immersive-reading-mode/design.md)**: Technical design and database schema

## Configuration

### AI Provider Setup

The app supports multiple AI providers:

**Gemini (Google)**
- Set `LLM_PROVIDER=gemini` in config
- Requires `GEMINI_API_KEY` environment variable

**OpenAI**
- Set `LLM_PROVIDER=openai` in config
- Requires `OPENAI_API_KEY` environment variable

**Ollama (Local)**
- Set `LLM_PROVIDER=ollama` in config
- Requires Ollama running locally on port 11434

### Database

- Default database: `flashcards.db` (SQLite)
- Supports cloud sync with Firestore
- Automatic schema migrations

## Testing

Run the test suite:

```bash
# All tests
pytest tests/

# Unit tests only
pytest tests/unit/

# Property-based tests
pytest tests/property/

# Integration tests
pytest tests/integration/
```

## Project Structure

```
language_learning_tools/
├── src/
│   ├── features/
│   │   ├── reader/              # Reading Mode implementation
│   │   │   ├── ui/              # Tkinter UI components
│   │   │   ├── content_manager.py
│   │   │   ├── reading_assistant.py
│   │   │   ├── analytics_engine.py
│   │   │   └── ...
│   │   ├── dashboard/           # Main dashboard UI
│   │   ├── study_center/        # Study tools
│   │   ├── writing_lab/         # Writing practice
│   │   ├── mining/              # Sentence mining
│   │   └── ...
│   ├── core/
│   │   ├── database.py          # Database management
│   │   └── localization.py      # Multi-language support
│   ├── services/
│   │   ├── llm_service.py       # AI integration
│   │   └── ...
│   └── main.py                  # Application entry point
├── tests/
│   ├── unit/                    # Unit tests
│   ├── property/                # Property-based tests
│   └── integration/             # Integration tests
├── docs/
│   ├── user_guides/             # User documentation
│   ├── legal/                   # Legal compliance docs
│   ├── developer/               # Developer documentation
│   └── ...
└── README.md                    # This file
```

## Privacy & Data

- All data is stored locally in your SQLite database
- Reading content is private and not shared by default
- Cloud sync is optional and requires explicit sign-in
- No data is sent to external servers without your consent
- See [Privacy Policy](docs/legal/reading_mode_compliance.md) for details

## Troubleshooting

### Reading Mode Issues

**Can't import content?**
- Ensure you've checked the legal attestation box
- Verify the file is in UTF-8, UTF-16, or Latin-1 encoding
- Check that content is at least 100 characters

**Words not being looked up?**
- Verify AI provider is configured and online
- Check that the word exists in the dictionary
- Try a different word to test

**Slow performance?**
- Split large files into smaller reading sessions
- Check your AI provider's rate limits
- Clear the definition cache if it grows too large

### General Issues

**App won't start?**
- Ensure Python 3.8+ is installed
- Run `pip install -r requirements.txt` to install dependencies
- Check that `flashcards.db` is not corrupted

**Database errors?**
- Delete `flashcards.db` to reset (you'll lose data)
- Check file permissions in the directory
- Ensure disk space is available

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new features
5. Submit a pull request

## License

[Add your license here]

## Support

For issues, questions, or suggestions:
- Check the [documentation](docs/)
- Review [existing issues](../../issues)
- Create a new issue with details

## Acknowledgments

- Built with Python and Tkinter
- AI powered by Gemini, OpenAI, or Ollama
- Database: SQLite with Firestore sync
- Community contributions and feedback

---

**Happy Learning!** 🎓📚
