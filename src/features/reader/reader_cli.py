"""
Command-line interface for Adventure Graded Reader.

This module provides an interactive CLI for playing Choose Your Own Adventure
stories with vocabulary constraints for language learning.
"""

import sys
import argparse
from typing import Optional
import logging

from src.core.database import FlashcardDatabase
from src.services.llm_service import get_ai_client
from .session_manager import StorySessionManager
from .vocabulary_service import VocabularyService
from .story_generator import StoryGenerator
from .template_engine import TemplateEngine
from .llm_agent import AdventureReaderAgent
from .models import GenerationMode, StoryPassage
from .exceptions import (
    InvalidChoiceError,
    SessionNotFoundError,
    InsufficientVocabularyError,
    TemplateNotFoundError,
    LLMGenerationError
)


logger = logging.getLogger(__name__)


class ReaderCLI:
    """
    Interactive command-line interface for the Adventure Graded Reader.
    
    Provides commands for:
    - Starting new story sessions
    - Resuming existing sessions
    - Managing sessions (list, delete)
    - Exporting session history
    """
    
    def __init__(self, database_path: str = "flashcards.db"):
        """
        Initialize the CLI.
        
        Args:
            database_path: Path to the flashcards database
        """
        self.database = FlashcardDatabase(database_path)
        self.vocabulary_service = VocabularyService(self.database)
        
        # Initialize components (will be configured based on mode)
        self.template_engine = TemplateEngine(self.database)
        self.llm_agent = None
        self.story_generator = None
        self.session_manager = None
        
        logger.info("ReaderCLI initialized")
    
    def run(self):
        """Main entry point for the CLI."""
        parser = argparse.ArgumentParser(
            description="Adventure Graded Reader - Interactive language learning stories"
        )
        
        subparsers = parser.add_subparsers(dest='command', help='Available commands')
        
        # New session command
        new_parser = subparsers.add_parser('new', help='Start a new story session')
        new_parser.add_argument('--language', '-l', required=True, help='Target language (e.g., korean, spanish)')
        new_parser.add_argument('--genre', '-g', required=True, help='Story genre (mystery, adventure, fantasy)')
        new_parser.add_argument('--mode', '-m', choices=['template', 'llm'], default='template',
                               help='Generation mode (template=offline, llm=high-quality)')
        
        # Resume session command
        resume_parser = subparsers.add_parser('resume', help='Resume an existing session')
        resume_parser.add_argument('session_id', type=int, help='Session ID to resume')
        
        # List sessions command
        subparsers.add_parser('list', help='List all story sessions')
        
        # Delete session command
        delete_parser = subparsers.add_parser('delete', help='Delete a story session')
        delete_parser.add_argument('session_id', type=int, help='Session ID to delete')
        
        # Export history command
        export_parser = subparsers.add_parser('export', help='Export session history')
        export_parser.add_argument('session_id', type=int, help='Session ID to export')
        
        args = parser.parse_args()
        
        if not args.command:
            parser.print_help()
            return
        
        # Execute command
        try:
            if args.command == 'new':
                self.start_new_session(args.language, args.genre, args.mode)
            elif args.command == 'resume':
                self.resume_session(args.session_id)
            elif args.command == 'list':
                self.list_sessions()
            elif args.command == 'delete':
                self.delete_session(args.session_id)
            elif args.command == 'export':
                self.export_session(args.session_id)
        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            sys.exit(0)
        except Exception as e:
            logger.error(f"CLI error: {e}", exc_info=True)
            print(f"\n❌ Error: {e}")
            sys.exit(1)
    
    def start_new_session(self, language: str, genre: str, mode: str):
        """
        Start a new story session.
        
        Args:
            language: Target language
            genre: Story genre
            mode: Generation mode ('template' or 'llm')
        """
        print(f"\n📖 Starting new {genre} story in {language}...")
        print(f"   Mode: {mode}")
        print()
        
        # Initialize components based on mode
        generation_mode = GenerationMode.from_string(mode)
        self._initialize_components(generation_mode)
        
        try:
            # Create session
            session_id = self.session_manager.create_session(
                language=language,
                genre=genre,
                generation_mode=generation_mode
            )
            
            print(f"✓ Created session {session_id}")
            print()
            
            # Start interactive story
            self._play_session(session_id)
            
        except InsufficientVocabularyError as e:
            print(f"\n⚠️  {e}")
            print("\n💡 Tip: Study more flashcards before using the reader.")
        except TemplateNotFoundError as e:
            print(f"\n⚠️  {e}")
            self._suggest_available_genres()
        except Exception as e:
            print(f"\n❌ Failed to start session: {e}")
            logger.error(f"Session creation failed: {e}", exc_info=True)
    
    def resume_session(self, session_id: int):
        """
        Resume an existing story session.
        
        Args:
            session_id: ID of session to resume
        """
        print(f"\n📖 Resuming session {session_id}...")
        print()
        
        try:
            # Load session to get mode
            session = self.session_manager.load_session(session_id) if self.session_manager else None
            
            if not session:
                # Initialize with default mode to load session
                self._initialize_components(GenerationMode.TEMPLATE)
                session = self.session_manager.load_session(session_id)
            
            # Re-initialize with correct mode
            self._initialize_components(session.generation_mode)
            
            # Show session info
            print(f"Language: {session.language}")
            print(f"Genre: {session.genre}")
            print(f"Words learned: {len(session.vocabulary_introduced)}")
            print()
            
            # Show history
            history = self.session_manager.get_session_history(session_id)
            if history:
                print(f"📚 Story so far ({len(history)} passages):")
                for i, passage in enumerate(history[-3:], start=max(1, len(history) - 2)):
                    print(f"   {i}. {passage.story_text[:60]}...")
                print()
            
            # Continue story
            self._play_session(session_id)
            
        except SessionNotFoundError:
            print(f"\n❌ Session {session_id} not found.")
            print("\n💡 Use 'list' command to see available sessions.")
        except Exception as e:
            print(f"\n❌ Failed to resume session: {e}")
            logger.error(f"Session resume failed: {e}", exc_info=True)
    
    def list_sessions(self):
        """List all story sessions."""
        print("\n📚 Story Sessions:")
        print()
        
        cursor = self.database.conn.cursor()
        cursor.execute("""
            SELECT id, language, genre, generation_mode, created_at, 
                   vocabulary_introduced, completed
            FROM story_sessions
            ORDER BY last_updated DESC
        """)
        
        sessions = cursor.fetchall()
        
        if not sessions:
            print("   No sessions found.")
            print("\n💡 Use 'new' command to start a story.")
            return
        
        for row in sessions:
            session_id, language, genre, mode, created, vocab_json, completed = row
            
            import json
            vocab_count = len(json.loads(vocab_json or "[]"))
            status = "✓ Completed" if completed else "⏸ In Progress"
            
            print(f"   [{session_id}] {language.title()} - {genre.title()}")
            print(f"       {status} | {vocab_count} words | Mode: {mode}")
            print(f"       Created: {created[:10]}")
            print()
    
    def delete_session(self, session_id: int):
        """
        Delete a story session.
        
        Args:
            session_id: ID of session to delete
        """
        # Initialize components
        self._initialize_components(GenerationMode.TEMPLATE)
        
        try:
            # Confirm deletion
            response = input(f"⚠️  Delete session {session_id}? This cannot be undone. (y/N): ")
            
            if response.lower() != 'y':
                print("Cancelled.")
                return
            
            if self.session_manager.delete_session(session_id):
                print(f"\n✓ Deleted session {session_id}")
            else:
                print(f"\n❌ Session {session_id} not found")
                
        except Exception as e:
            print(f"\n❌ Failed to delete session: {e}")
            logger.error(f"Session deletion failed: {e}", exc_info=True)
    
    def export_session(self, session_id: int):
        """
        Export session history to a file.
        
        Args:
            session_id: ID of session to export
        """
        # Initialize components
        self._initialize_components(GenerationMode.TEMPLATE)
        
        try:
            from .recovery import SessionRecovery
            
            recovery = SessionRecovery(self.database)
            history = self.session_manager.get_session_history(session_id)
            
            if not history:
                print(f"\n❌ No history found for session {session_id}")
                return
            
            filepath = recovery.export_readable_history(session_id, history)
            
            print(f"\n✓ Exported session history to:")
            print(f"   {filepath}")
            
        except SessionNotFoundError:
            print(f"\n❌ Session {session_id} not found")
        except Exception as e:
            print(f"\n❌ Failed to export session: {e}")
            logger.error(f"Session export failed: {e}", exc_info=True)
    
    def _play_session(self, session_id: int):
        """
        Interactive story playthrough.
        
        Args:
            session_id: ID of session to play
        """
        try:
            while True:
                # Generate next passage
                print("⏳ Generating story...")
                
                try:
                    # Get current passage or generate first one
                    session = self.session_manager.load_session(session_id)
                    
                    if session.current_passage_id:
                        # Load current passage
                        history = self.session_manager.get_session_history(session_id)
                        current_passage = history[-1] if history else None
                        
                        if current_passage:
                            self._display_passage(current_passage)
                            choice_id = self._get_user_choice(current_passage)
                            
                            if choice_id is None:
                                break
                            
                            # Generate next passage
                            next_passage = self.session_manager.process_choice(session_id, choice_id)
                            print()
                            self._display_passage(next_passage)
                        else:
                            # Generate first passage
                            passage = self.session_manager.process_choice(session_id, 0)
                            self._display_passage(passage)
                    else:
                        # Generate first passage
                        passage = self.session_manager.process_choice(session_id, 0)
                        self._display_passage(passage)
                    
                    # Ask if user wants to continue
                    print()
                    continue_choice = input("Continue story? (Y/n): ").strip().lower()
                    
                    if continue_choice == 'n':
                        print("\n📖 Story paused. Use 'resume' command to continue later.")
                        break
                    
                    print()
                    
                except InvalidChoiceError as e:
                    print(f"\n⚠️  {e}")
                    print("Please select a valid choice.")
                    continue
                    
                except LLMGenerationError as e:
                    print(f"\n⚠️  LLM generation failed: {e}")
                    print("Falling back to template mode...")
                    continue
                    
        except KeyboardInterrupt:
            print("\n\n📖 Story paused. Use 'resume' command to continue later.")
    
    def _display_passage(self, passage: StoryPassage):
        """Display a story passage with formatting."""
        print("─" * 60)
        print()
        print(passage.story_text)
        print()
        
        if passage.new_words:
            print("📝 New Words:")
            for word in passage.new_words:
                print(f"   • {word.word} - {word.translation}")
                if word.context_sentence != passage.story_text:
                    print(f"     \"{word.context_sentence}\"")
            print()
        
        if passage.choices:
            print("🔀 What do you do?")
            for i, choice in enumerate(passage.choices, 1):
                print(f"   {i}. {choice.text}")
                if choice.description:
                    print(f"      ({choice.description})")
            print()
    
    def _get_user_choice(self, passage: StoryPassage) -> Optional[int]:
        """
        Get user's choice selection.
        
        Returns:
            Choice ID, or None to quit
        """
        while True:
            try:
                response = input("Your choice (1-{}, or 'q' to quit): ".format(len(passage.choices)))
                
                if response.lower() == 'q':
                    return None
                
                choice_num = int(response)
                
                if 1 <= choice_num <= len(passage.choices):
                    return passage.choices[choice_num - 1].id
                else:
                    print(f"⚠️  Please enter a number between 1 and {len(passage.choices)}")
                    
            except ValueError:
                print("⚠️  Please enter a valid number or 'q' to quit")
    
    def _initialize_components(self, mode: GenerationMode):
        """Initialize story generation components based on mode."""
        if mode == GenerationMode.LLM:
            try:
                llm_service = get_ai_client()
                self.llm_agent = AdventureReaderAgent(llm_service)
                self.story_generator = StoryGenerator(
                    mode=mode,
                    database=self.database,
                    llm_service=llm_service
                )
            except Exception as e:
                logger.warning(f"Failed to initialize LLM mode: {e}, falling back to template")
                mode = GenerationMode.TEMPLATE
                self.story_generator = StoryGenerator(
                    mode=mode,
                    database=self.database
                )
        else:
            self.story_generator = StoryGenerator(
                mode=mode,
                database=self.database
            )
        
        self.session_manager = StorySessionManager(
            database=self.database,
            vocabulary_service=self.vocabulary_service,
            story_generator=self.story_generator
        )
    
    def _suggest_available_genres(self):
        """Suggest available genres to the user."""
        try:
            genres = self.story_generator.get_available_genres()
            if genres:
                print("\n💡 Available genres:")
                for genre in genres:
                    print(f"   • {genre}")
        except Exception:
            pass


def main():
    """Main entry point for the CLI."""
    # Configure logging
    logging.basicConfig(
        level=logging.WARNING,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    cli = ReaderCLI()
    cli.run()


if __name__ == '__main__':
    main()
