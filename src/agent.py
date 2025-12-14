"""
Agent Implementation - LangChain-based Financial Analyst Agent

This module provides a Windows-compatible agent using LangChain
instead of CrewAI (which has signal issues on Windows).

The agent uses Google Gemini as the LLM and can call our financial tools.
"""

from __future__ import annotations

import os
import logging
from typing import Optional, Annotated
from dotenv import load_dotenv

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver

# Import our custom tools
from src.tools import (
    execute_sql_query,
    get_company_financials,
    calculate_growth_rate,
    calculate_net_margin,
    compare_companies,
    get_available_data,
    compare_net_margins_over_time,
)
from src.database import FinancialDatabase

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# =============================================================================
# Tool Wrappers for LangChain
# =============================================================================

@tool
def sql_query_tool(sql_query: str) -> str:
    """
    Execute a SQL SELECT query against the financial database.
    
    Use this to retrieve specific financial data using SQL.
    
    Table: financials
    Columns: company, fiscal_year, revenue, net_income, total_assets, total_equity
    
    Example: SELECT revenue FROM financials WHERE company = 'Alpha Corp' AND fiscal_year = 2022
    
    Args:
        sql_query: A valid SQL SELECT query
    
    Returns:
        Query results or error message
    """
    return execute_sql_query(sql_query)


@tool
def company_financials_tool(company: str, year: str = "") -> str:
    """
    Get all financial data for a specific company.
    
    Args:
        company: Company name (e.g., 'Alpha Corp')
        year: Optional year (e.g., '2022'). Leave empty for all years.
    
    Returns:
        Financial data including revenue, net income, assets, and equity
    """
    year_int = int(year) if year and year.isdigit() else None
    return get_company_financials(company, year_int)


@tool
def growth_rate_tool(company: str, metric: str, start_year: str, end_year: str) -> str:
    """
    Calculate the growth rate of a metric between two years.
    
    Args:
        company: Company name (e.g., 'Alpha Corp')
        metric: One of: revenue, net_income, total_assets, total_equity
        start_year: Starting year (e.g., '2019')
        end_year: Ending year (e.g., '2023')
    
    Returns:
        Growth rate percentage with underlying values
    """
    return calculate_growth_rate(
        company=company,
        metric=metric,
        start_year=int(start_year),
        end_year=int(end_year)
    )


@tool
def net_margin_tool(company: str, year: str) -> str:
    """
    Calculate net profit margin (Net Income / Revenue) for a company in a year.
    
    Args:
        company: Company name (e.g., 'Alpha Corp')
        year: Fiscal year (e.g., '2022')
    
    Returns:
        Net margin percentage with underlying values
    """
    return calculate_net_margin(company=company, year=int(year))


@tool
def compare_companies_tool(companies: str, metric: str, year: str) -> str:
    """
    Compare a metric across multiple companies for a specific year.
    
    Args:
        companies: Comma-separated list of companies, or 'all' for all companies
        metric: One of: revenue, net_income, total_assets, total_equity
        year: Fiscal year (e.g., '2023')
    
    Returns:
        Ranked comparison of companies
    """
    if companies.lower() == 'all':
        company_list = ['all']
    else:
        company_list = [c.strip() for c in companies.split(',')]
    
    return compare_companies(
        companies=company_list,
        metric=metric,
        year=int(year)
    )


@tool
def available_data_tool() -> str:
    """
    Get information about available companies, years, and metrics in the database.
    
    Use this when you need to know what data is available before querying.
    
    Returns:
        Summary of available data
    """
    return get_available_data()


@tool
def margins_over_time_tool(companies: str, start_year: str, end_year: str) -> str:
    """
    Compare net profit margins for multiple companies across a range of years.
    
    Args:
        companies: Comma-separated list of company names
        start_year: Starting year (e.g., '2020')
        end_year: Ending year (e.g., '2023')
    
    Returns:
        Table of net margins by company and year
    """
    company_list = [c.strip() for c in companies.split(',')]
    return compare_net_margins_over_time(
        companies=company_list,
        start_year=int(start_year),
        end_year=int(end_year)
    )


# =============================================================================
# Agent Creation
# =============================================================================

def get_system_prompt() -> str:
    """Generate the system prompt with database schema context."""
    db = FinancialDatabase("data/financials.db")
    
    try:
        schema_info = db.get_schema_description()
    except Exception:
        schema_info = "Database not initialized. Available tools will help you explore the data."
    
    return f"""You are a Senior Financial Analyst AI assistant. Your job is to answer questions about company financials using ONLY the data in the database.

CRITICAL RULES:
1. NEVER make up or hallucinate financial numbers
2. ALWAYS use the provided tools to get data
3. If data is not available, say so clearly
4. Show source numbers when answering questions
5. Format currency with dollar signs and commas (e.g., $125,000,000)

{schema_info}

When answering questions:
1. First understand what data you need
2. Use the appropriate tool to retrieve the data
3. If calculations are needed, use the calculation tools
4. Provide a clear answer with supporting numbers
"""


def create_agent():
    """
    Create the LangChain financial analyst agent.
    
    Returns:
        A configured ReAct agent with memory
    """
    # Get API key
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY not found in environment variables")
    
    # Create the Gemini model  
    model = ChatGoogleGenerativeAI(
        model=os.getenv("GEMINI_MODEL", "gemini-2.0-flash-exp"),
        google_api_key=api_key,
        temperature=0.1,  # Low temperature for factual responses
    )
    
    # Define available tools
    tools = [
        sql_query_tool,
        company_financials_tool,
        growth_rate_tool,
        net_margin_tool,
        compare_companies_tool,
        available_data_tool,
        margins_over_time_tool,
    ]
    
    # Create memory for conversation
    memory = MemorySaver()
    
    # Create the ReAct agent
    agent = create_react_agent(
        model=model,
        tools=tools,
        checkpointer=memory,
    )
    
    return agent


# Global agent instance
_agent = None
_config = {"configurable": {"thread_id": "main"}}


def get_agent():
    """Get or create the agent instance."""
    global _agent
    if _agent is None:
        _agent = create_agent()
    return _agent


def answer_question(question: str) -> str:
    """
    Answer a financial question using the agent.
    
    Args:
        question: Natural language question about company financials
    
    Returns:
        Agent's response with data-grounded answer
    """
    logger.info(f"Processing question: {question}")
    
    try:
        agent = get_agent()
        
        # Build messages with system prompt
        messages = [
            {"role": "user", "content": f"{get_system_prompt()}\n\nQuestion: {question}"}
        ]
        
        # Run the agent
        result = agent.invoke(
            {"messages": messages},
            config=_config
        )
        
        # Extract the final response
        if result and "messages" in result:
            for msg in reversed(result["messages"]):
                if hasattr(msg, 'content') and msg.content:
                    return msg.content
        
        return "I couldn't generate a response. Please try rephrasing your question."
        
    except Exception as e:
        logger.exception("Error during agent execution")
        return f"Error processing question: {str(e)}"


def reset_conversation():
    """Reset the conversation memory."""
    global _agent, _config
    _agent = None
    _config = {"configurable": {"thread_id": f"main_{id(_config)}"}}


# =============================================================================
# CLI Testing
# =============================================================================

if __name__ == "__main__":
    import sys
    
    # Ensure database is initialized
    from src.ingest import DataIngestionPipeline
    
    print("Initializing database...")
    try:
        db = FinancialDatabase("data/financials.db")
        if db.get_record_count() == 0:
            pipeline = DataIngestionPipeline()
            pipeline.run()
    except Exception as e:
        print(f"Database init: {e}")
        pipeline = DataIngestionPipeline()
        pipeline.run()
    
    # Test question
    if len(sys.argv) > 1:
        question = " ".join(sys.argv[1:])
    else:
        question = "What was Alpha Corp's revenue in 2022?"
    
    print(f"\nQuestion: {question}")
    print("=" * 60)
    
    response = answer_question(question)
    
    print("\nAnswer:")
    print(response)
