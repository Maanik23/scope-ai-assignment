"""
Chainlit Web UI - Interactive Chat Interface

This module provides a web-based chat interface using Chainlit.
It visualizes the agent's reasoning process and tool calls.

Running:
    chainlit run app.py
"""

from __future__ import annotations

import os
import sys
import logging
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

import chainlit as cl
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging - reduce noise
logging.basicConfig(level=logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


def ensure_database():
    """Ensure database is initialized before accepting queries."""
    from src.database import FinancialDatabase
    from src.ingest import DataIngestionPipeline
    
    db = FinancialDatabase("data/financials.db")
    
    try:
        count = db.get_record_count()
        if count == 0:
            logger.info("Database empty, running ingestion...")
            pipeline = DataIngestionPipeline()
            pipeline.run()
    except Exception:
        logger.info("Database not initialized, running ingestion...")
        pipeline = DataIngestionPipeline()
        pipeline.run()


@cl.on_chat_start
async def on_chat_start():
    """Initialize the chat session."""
    
    # Ensure database is ready
    ensure_database()
    
    # Get available data for welcome message
    from src.database import FinancialDatabase
    db = FinancialDatabase("data/financials.db")
    
    companies = db.get_all_companies()
    years = db.get_all_years()
    
    # Welcome message
    welcome = f"""# Financial AI Assistant

Welcome! I'm your AI-powered financial analyst. I can answer questions about company financials using real data.

## Available Data
- **Companies**: {', '.join(companies)}
- **Years**: {', '.join(map(str, years))}
- **Metrics**: Revenue, Net Income, Total Assets, Total Equity

## Example Questions
- "What was Alpha Corp's revenue in 2022?"
- "Which company had the highest net income in 2023?"
- "Compare the net margin of Beta Inc and Gamma Ltd from 2020 to 2023"
- "How did Delta PLC's revenue grow between 2019 and 2023?"

**Note**: All answers are based on database data, not AI knowledge.
"""
    
    await cl.Message(content=welcome).send()


@cl.on_message
async def on_message(message: cl.Message):
    """Process user messages and return AI responses."""
    
    user_question = message.content
    
    # Show thinking indicator
    thinking_msg = cl.Message(content="🔍 Analyzing your question...")
    await thinking_msg.send()
    
    try:
        # Import agent here to avoid startup delay
        from src.agent import answer_question
        
        # Get response from agent
        response = answer_question(user_question)
        
        # Update the thinking message with the response
        thinking_msg.content = response
        await thinking_msg.update()
        
    except Exception as e:
        logger.exception("Error processing question")
        thinking_msg.content = f"❌ Error: {str(e)}\n\nPlease try rephrasing your question."
        await thinking_msg.update()


@cl.on_stop
async def on_stop():
    """Handle conversation stop."""
    logger.info("Conversation stopped by user")


# =============================================================================
# Alternative: Direct Execution without Chainlit (for testing)
# =============================================================================

def run_cli_mode():
    """Run in simple CLI mode for quick testing."""
    from src.agent import answer_question
    
    ensure_database()
    
    print("\n" + "=" * 60)
    print("Financial AI Assistant (CLI Mode)")
    print("=" * 60)
    print("Type 'quit' or 'exit' to stop.\n")
    
    while True:
        try:
            question = input("\nYou: ").strip()
            
            if not question:
                continue
            
            if question.lower() in ['quit', 'exit', 'q']:
                print("Goodbye!")
                break
            
            print("\n🔍 Analyzing...")
            response = answer_question(question)
            print(f"\n📊 Answer:\n{response}")
            
        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")


if __name__ == "__main__":
    # When running directly (not via chainlit), use CLI mode
    run_cli_mode()
