"""
CLI Interface - Simple command-line interface for testing.

This provides a basic way to interact with the agent without
starting the web UI. Useful for:
- Quick testing
- Scripted queries
- Debugging

Usage:
    python cli.py                           # Interactive mode
    python cli.py "What was Alpha Corp's revenue in 2022?"  # Single query
"""

from __future__ import annotations

import sys
import argparse
import logging
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.WARNING,  # Quiet mode for CLI
    format='%(message)s'
)


def ensure_database():
    """Initialize database if needed."""
    from src.database import FinancialDatabase
    from src.ingest import DataIngestionPipeline
    
    db = FinancialDatabase("data/financials.db")
    
    try:
        count = db.get_record_count()
        if count == 0:
            print("📦 Database empty, running data ingestion...")
            pipeline = DataIngestionPipeline()
            result = pipeline.run()
            print(f"✅ Loaded {len(result.valid_records)} records\n")
    except Exception:
        print("📦 Initializing database...")
        pipeline = DataIngestionPipeline()
        result = pipeline.run()
        print(f"✅ Loaded {len(result.valid_records)} records\n")


def show_welcome():
    """Display welcome message with available data."""
    from src.database import FinancialDatabase
    
    db = FinancialDatabase("data/financials.db")
    companies = db.get_all_companies()
    years = db.get_all_years()
    
    print("""
╔══════════════════════════════════════════════════════════════╗
║           📊 FINANCIAL AI ASSISTANT 📊                        ║
╠══════════════════════════════════════════════════════════════╣
║  I answer questions about company financials using real data  ║
╚══════════════════════════════════════════════════════════════╝
""")
    print(f"📁 Companies: {', '.join(companies)}")
    print(f"📅 Years: {', '.join(map(str, years))}")
    print(f"📈 Metrics: revenue, net_income, total_assets, total_equity")
    print()
    print("💡 Example questions:")
    print("   • What was Alpha Corp's revenue in 2022?")
    print("   • Which company had the highest net income in 2023?")
    print("   • Compare net margins of Beta Inc and Gamma Ltd over time")
    print()
    print("Type 'quit' to exit, 'help' for more examples.\n")


def show_help():
    """Display help with more example questions."""
    print("""
📖 EXAMPLE QUESTIONS:

Basic Lookups:
  • What was Alpha Corp's revenue in 2022?
  • Show me Beta Inc's financials for 2023
  • Get all data for Gamma Ltd

Comparisons:
  • Which company had the highest revenue in 2023?
  • Compare net income of Delta PLC and Epsilon Holdings in 2022
  • Rank all companies by total assets in 2021

Growth & Trends:
  • How did Alpha Corp's revenue grow from 2019 to 2023?
  • What's the revenue growth rate for all companies?

Margins & Ratios:
  • What was Beta Inc's net margin in 2023?
  • Compare net margins of Gamma Ltd and Delta PLC from 2020 to 2023

Advanced:
  • Which company improved its net margin the most?
  • What's the average revenue across all companies in 2023?
""")


def single_query(question: str):
    """Process a single query and exit."""
    from src.agent import answer_question
    
    ensure_database()
    print(f"❓ Question: {question}\n")
    print("🔍 Analyzing...\n")
    
    response = answer_question(question)
    print("📊 Answer:")
    print("-" * 40)
    print(response)
    print("-" * 40)


def interactive_mode():
    """Run interactive CLI mode."""
    from src.agent import answer_question
    
    ensure_database()
    show_welcome()
    
    while True:
        try:
            # Get user input
            question = input("You: ").strip()
            
            if not question:
                continue
            
            # Handle special commands
            if question.lower() in ['quit', 'exit', 'q']:
                print("\n👋 Goodbye!\n")
                break
            
            if question.lower() in ['help', '?']:
                show_help()
                continue
            
            if question.lower() == 'clear':
                print("\033c", end="")  # Clear terminal
                show_welcome()
                continue
            
            # Process the question
            print("\n🔍 Analyzing...\n")
            response = answer_question(question)
            
            print("📊 Answer:")
            print("-" * 50)
            print(response)
            print("-" * 50)
            print()
            
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!\n")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}\n")
            print("Please try rephrasing your question.\n")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Financial AI Assistant - CLI Interface",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python cli.py                                    # Interactive mode
  python cli.py "What was Alpha Corp's revenue?"  # Single query
  python cli.py --init                             # Just initialize database
        """
    )
    
    parser.add_argument(
        'question',
        nargs='?',
        help='Question to ask (omit for interactive mode)'
    )
    
    parser.add_argument(
        '--init',
        action='store_true',
        help='Initialize database and exit'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.INFO)
    
    # Initialize only mode
    if args.init:
        ensure_database()
        print("✅ Database initialized successfully!")
        return
    
    # Single query mode
    if args.question:
        single_query(args.question)
        return
    
    # Interactive mode
    interactive_mode()


if __name__ == "__main__":
    main()
