from database import FlashcardDatabase
from spaced_repetition import get_due_flashcards

def main_menu():
    """Show main menu."""
    print("\n" + "="*50)
    print("FLASHCARD LEARNING APP")
    print("="*50)
    print("1. Launch GUI (Recommended)")
    print("2. Use CLI")
    print("3. Exit")
    return input("Choose an option: ").strip()

def cli_main():
    """CLI version of the app."""
    db = FlashcardDatabase()

    while True:
        print("\n" + "="*50)
        print("FLASHCARD APP - CLI")
        print("="*50)
        print("1. Create Deck")
        print("2. View Decks")
        print("3. Add Flashcard to Deck")
        print("4. Review Flashcards")
        print("5. View Deck Statistics")
        print("6. View All Cards in Deck")
        print("7. Delete Deck")
        print("8. Back to Main Menu")
        choice = input("Choose an option: ").strip()

        if choice == "1":
            name = input("Enter deck name: ").strip()
            desc = input("Enter deck description (optional): ").strip()
            deck_id = db.create_deck(name, desc)
            if deck_id:
                print(f"✓ Deck '{name}' created successfully!")
            else:
                print("✗ A deck with that name already exists")

        elif choice == "2":
            decks = db.get_all_decks()
            if not decks:
                print("No decks found")
            else:
                print("\n" + "-"*50)
                for deck in decks:
                    print(f"Name: {deck['name']}")
                    print(f"  Description: {deck['description']}")
                    print(f"  Total Cards: {deck['total_cards']} | Due: {deck['due_cards']}")
                    print("-"*50)

        elif choice == "3":
            decks = db.get_all_decks()
            if not decks:
                print("No decks available. Create one first.")
                continue
            
            print("\nAvailable decks:")
            for i, deck in enumerate(decks):
                print(f"{i+1}. {deck['name']}")
            
            deck_choice = input("Select deck number: ").strip()
            try:
                deck_idx = int(deck_choice) - 1
                if 0 <= deck_idx < len(decks):
                    deck_id = decks[deck_idx]["id"]
                    question = input("Enter question: ").strip()
                    answer = input("Enter answer: ").strip()
                    if question and answer:
                        db.add_flashcard(deck_id, question, answer)
                        print("✓ Flashcard added!")
                    else:
                        print("✗ Question and answer cannot be empty")
                else:
                    print("✗ Invalid deck number")
            except ValueError:
                print("✗ Invalid input")

        elif choice == "4":
            decks = db.get_all_decks()
            if not decks:
                print("No decks available")
                continue
            
            print("\nAvailable decks:")
            for i, deck in enumerate(decks):
                print(f"{i+1}. {deck['name']} ({deck['due_cards']} due)")
            
            deck_choice = input("Select deck number: ").strip()
            try:
                deck_idx = int(deck_choice) - 1
                if 0 <= deck_idx < len(decks):
                    deck_id = decks[deck_idx]["id"]
                    due_cards = db.get_due_flashcards(deck_id)
                    
                    if not due_cards:
                        print("✓ No cards due for review!")
                        continue
                    
                    print(f"\n{len(due_cards)} cards due for review\n")
                    
                    for i, fc in enumerate(due_cards, 1):
                        print(f"\n--- Card {i}/{len(due_cards)} ---")
                        print(f"Question: {fc.question}")
                        input("Press Enter to reveal answer...")
                        print(f"Answer: {fc.answer}")
                        
                        print("\nHow well did you remember this?")
                        print("0 - Blank (Again)")
                        print("1 - Poor")
                        print("2 - Difficult")
                        print("3 - OK")
                        print("4 - Good")
                        print("5 - Perfect")
                        
                        quality_input = input("Rate (0-5): ").strip()
                        try:
                            quality = int(quality_input)
                            if 0 <= quality <= 5:
                                fc.mark_reviewed(quality)
                                db.update_flashcard(fc)
                                print("✓ Card updated!")
                            else:
                                print("✗ Invalid rating")
                        except ValueError:
                            print("✗ Invalid input")
                    
                    print(f"\n✓ Review session complete! ({len(due_cards)} cards reviewed)")
                else:
                    print("✗ Invalid deck number")
            except ValueError:
                print("✗ Invalid input")

        elif choice == "5":
            decks = db.get_all_decks()
            if not decks:
                print("No decks available")
                continue
            
            print("\nAvailable decks:")
            for i, deck in enumerate(decks):
                print(f"{i+1}. {deck['name']}")
            
            deck_choice = input("Select deck number: ").strip()
            try:
                deck_idx = int(deck_choice) - 1
                if 0 <= deck_idx < len(decks):
                    deck = decks[deck_idx]
                    stats = db.get_deck_statistics(deck["id"])
                    cards = db.get_all_flashcards(deck["id"])
                    
                    # Calculate reviewed count and averages from cards
                    reviewed_count = sum(1 for c in cards if c.total_reviews > 0)
                    avg_easiness = sum(c.easiness for c in cards) / len(cards) if cards else 0.0
                    avg_interval = sum(c.interval for c in cards) / len(cards) if cards else 0.0
                    
                    print("\n" + "="*50)
                    print(f"STATISTICS - {deck['name']}")
                    print("="*50)
                    print(f"Total Cards: {stats['total_cards']}")
                    print(f"New Cards: {stats['total_cards'] - reviewed_count}")
                    print(f"Reviewed: {reviewed_count}")
                    print(f"Due Today: {stats['due_cards']}")
                    print(f"\nTotal Reviews: {stats['total_reviews']}")
                    print(f"Correct Reviews: {stats['correct_reviews']}")
                    print(f"Overall Accuracy: {stats['overall_accuracy']:.1f}%")
                    print(f"\nAverage Easiness: {avg_easiness:.2f}")
                    print(f"Average Interval: {avg_interval:.1f} days")
                    print("="*50)
                else:
                    print("✗ Invalid deck number")
            except ValueError:
                print("✗ Invalid input")

        elif choice == "6":
            decks = db.get_all_decks()
            if not decks:
                print("No decks available")
                continue
            
            print("\nAvailable decks:")
            for i, deck in enumerate(decks):
                print(f"{i+1}. {deck['name']}")
            
            deck_choice = input("Select deck number: ").strip()
            try:
                deck_idx = int(deck_choice) - 1
                if 0 <= deck_idx < len(decks):
                    deck_id = decks[deck_idx]["id"]
                    cards = db.get_all_flashcards(deck_id)
                    
                    if not cards:
                        print("No cards in this deck")
                    else:
                        print("\n" + "-"*80)
                        for i, card in enumerate(cards, 1):
                            from spaced_repetition import get_next_review_date
                            accuracy = f"{card.get_accuracy():.1f}%" if card.total_reviews > 0 else "N/A"
                            next_review = get_next_review_date(card).strftime("%Y-%m-%d") if card.last_reviewed else "Today"
                            print(f"{i}. Q: {card.question}")
                            print(f"   A: {card.answer}")
                            print(f"   Accuracy: {accuracy} | Next Review: {next_review}")
                            print("-"*80)
                else:
                    print("✗ Invalid deck number")
            except ValueError:
                print("✗ Invalid input")

        elif choice == "7":
            decks = db.get_all_decks()
            if not decks:
                print("No decks available")
                continue
            
            print("\nAvailable decks:")
            for i, deck in enumerate(decks):
                print(f"{i+1}. {deck['name']}")
            
            deck_choice = input("Select deck number: ").strip()
            try:
                deck_idx = int(deck_choice) - 1
                if 0 <= deck_idx < len(decks):
                    deck = decks[deck_idx]
                    confirm = input(f"Delete '{deck['name']}' and all its cards? (yes/no): ").strip().lower()
                    if confirm == "yes":
                        db.delete_deck(deck["id"])
                        print("✓ Deck deleted!")
                    else:
                        print("Cancelled")
                else:
                    print("✗ Invalid deck number")
            except ValueError:
                print("✗ Invalid input")

        elif choice == "8":
            return

        else:
            print("✗ Invalid choice")

    db.close()

def main():
    while True:
        choice = main_menu()
        
        if choice == "1":
            try:
                from gui import main
                main()
            except ImportError:
                print("✗ GUI module not found. Please ensure gui.py is in the same directory.")
        elif choice == "2":
            cli_main()
        elif choice == "3":
            print("Goodbye!")
            break
        else:
            print("✗ Invalid choice")

if __name__ == "__main__":
    main()