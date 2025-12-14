"""
Agent Tools - Functions exposed to the AI agent for data retrieval and computation.

This module contains all the tools the AI agent can use to answer questions.
Each tool is a self-contained function that:
- Takes well-defined inputs
- Performs a specific operation (query or calculation)
- Returns structured results
- Handles errors gracefully

Design Principles:
- Single Responsibility: Each tool does one thing well
- Clear Contracts: Explicit inputs and outputs
- Error Handling: Never crash, return informative errors
- Idempotent: Same inputs always give same outputs
- Self-Documenting: Detailed docstrings for LLM understanding
"""

from __future__ import annotations

from typing import Optional, Any
from dataclasses import dataclass
import logging

from src.database import FinancialDatabase

logger = logging.getLogger(__name__)

# Global database instance - initialized once and reused
_db: Optional[FinancialDatabase] = None


def get_database() -> FinancialDatabase:
    """Get or create the database connection."""
    global _db
    if _db is None:
        _db = FinancialDatabase("data/financials.db")
    return _db


def set_database(db: FinancialDatabase) -> None:
    """Set the database instance (useful for testing)."""
    global _db
    _db = db


def normalize_company_name(company: str, db: FinancialDatabase) -> tuple[str, str | None]:
    """
    Normalize company name with case-insensitive matching.
    
    Args:
        company: The company name provided by user
        db: Database instance to check available companies
    
    Returns:
        Tuple of (normalized_name, error_message).
        If match found: (correct_name, None)
        If no match: (original_name, error_message)
    """
    available_companies = db.get_all_companies()
    
    # Exact match
    if company in available_companies:
        return company, None
    
    # Case-insensitive match
    company_lower = company.lower()
    matches = [c for c in available_companies if c.lower() == company_lower]
    if matches:
        return matches[0], None
    
    # No match found
    return company, f"Company '{company}' not found. Available companies: {', '.join(available_companies)}"


# =============================================================================
# TOOL 1: Execute SQL Query
# =============================================================================

def execute_sql_query(sql_query: str) -> str:
    """
    Execute a SQL query against the financial database and return results.
    
    This tool allows you to run SELECT queries to retrieve financial data.
    The database contains a 'financials' table with columns:
    - company (text): Company name
    - fiscal_year (integer): Year (2019-2023)
    - revenue (integer): Revenue in dollars
    - net_income (integer): Net income in dollars
    - total_assets (integer): Total assets in dollars
    - total_equity (integer): Total equity in dollars
    
    Args:
        sql_query: A valid SQL SELECT query. Only SELECT statements are allowed.
    
    Returns:
        A formatted string with the query results, or an error message.
    
    Examples:
        execute_sql_query("SELECT revenue FROM financials WHERE company = 'Alpha Corp' AND fiscal_year = 2022")
        execute_sql_query("SELECT company, revenue FROM financials WHERE fiscal_year = 2023 ORDER BY revenue DESC")
        execute_sql_query("SELECT * FROM financials WHERE company = 'Beta Inc'")
    """
    db = get_database()
    
    logger.info(f"Executing SQL: {sql_query}")
    
    result = db.execute_sql(sql_query)
    
    if not result['success']:
        error_msg = f"Query failed: {result['error']}"
        logger.error(error_msg)
        return error_msg
    
    if result['row_count'] == 0:
        return "No results found for this query."
    
    # Format results as a readable table
    data = result['data']
    if not data:
        return "No results found."
    
    # Build formatted output
    lines = [f"Query returned {result['row_count']} result(s):\n"]
    
    for i, row in enumerate(data, 1):
        formatted_values = []
        for key, value in row.items():
            if isinstance(value, int) and value > 1000:
                # Format large numbers with commas
                formatted_values.append(f"{key}: ${value:,}")
            else:
                formatted_values.append(f"{key}: {value}")
        lines.append(f"  {i}. " + ", ".join(formatted_values))
    
    return "\n".join(lines)


# =============================================================================
# TOOL 2: Get Company Financials
# =============================================================================

def get_company_financials(company: str, year: Optional[int] = None) -> str:
    """
    Get financial data for a specific company, optionally filtered by year.
    
    Use this tool to retrieve all financial metrics for a company.
    
    Args:
        company: The company name (e.g., 'Alpha Corp', 'Beta Inc').
                 Case-insensitive matching is supported.
        year: Optional fiscal year (2019-2023). If not provided, returns all years.
    
    Returns:
        Formatted financial data for the company, or an error message.
    
    Examples:
        get_company_financials("Alpha Corp", 2022)  # Specific year
        get_company_financials("Beta Inc")  # All years
    """
    db = get_database()
    
    logger.info(f"Getting financials for {company}, year={year}")
    
    # Normalize company name (case-insensitive matching)
    company, error = normalize_company_name(company, db)
    if error:
        return error
    
    # Build and execute query
    if year:
        sql = f"SELECT * FROM financials WHERE company = '{company}' AND fiscal_year = {year}"
    else:
        sql = f"SELECT * FROM financials WHERE company = '{company}' ORDER BY fiscal_year"
    
    result = db.execute_sql(sql)
    
    if not result['success']:
        return f"Error retrieving data: {result['error']}"
    
    if result['row_count'] == 0:
        if year:
            return f"No data found for {company} in {year}."
        return f"No data found for {company}."
    
    # Format nicely
    lines = [f"Financial data for {company}:\n"]
    
    for row in result['data']:
        lines.append(f"  Year {row['fiscal_year']}:")
        lines.append(f"    Revenue:      ${row['revenue']:,}")
        lines.append(f"    Net Income:   ${row['net_income']:,}")
        lines.append(f"    Total Assets: ${row['total_assets']:,}")
        lines.append(f"    Total Equity: ${row['total_equity']:,}")
    
    return "\n".join(lines)


# =============================================================================
# TOOL 3: Calculate Growth Rate
# =============================================================================

def calculate_growth_rate(
    company: str,
    metric: str,
    start_year: int,
    end_year: int
) -> str:
    """
    Calculate the growth rate of a financial metric between two years.
    
    Use this tool to compute how much a metric grew (or declined) over time.
    Growth rate is calculated as: ((end_value - start_value) / start_value) * 100
    
    Args:
        company: Company name (e.g., 'Alpha Corp')
        metric: The metric to calculate growth for.
                Options: 'revenue', 'net_income', 'total_assets', 'total_equity'
        start_year: Starting year (e.g., 2019)
        end_year: Ending year (e.g., 2023)
    
    Returns:
        Formatted growth rate with the underlying values, or an error message.
    
    Example:
        calculate_growth_rate("Alpha Corp", "revenue", 2019, 2023)
        # Returns: "Alpha Corp's revenue grew from $125,000,000 (2019) to $185,000,000 (2023), a growth of 48.0%"
    """
    db = get_database()
    
    logger.info(f"Calculating {metric} growth for {company} from {start_year} to {end_year}")
    
    # Normalize company name (case-insensitive matching)
    company, error = normalize_company_name(company, db)
    if error:
        return error
    
    # Validate metric
    valid_metrics = ['revenue', 'net_income', 'total_assets', 'total_equity']
    if metric.lower() not in valid_metrics:
        return f"Invalid metric '{metric}'. Valid options: {', '.join(valid_metrics)}"
    
    metric = metric.lower()
    
    # Validate years
    if start_year >= end_year:
        return f"Start year ({start_year}) must be before end year ({end_year})"
    
    # Get start and end values
    sql = f"""
        SELECT fiscal_year, {metric} 
        FROM financials 
        WHERE company = '{company}' 
        AND fiscal_year IN ({start_year}, {end_year})
        ORDER BY fiscal_year
    """
    
    result = db.execute_sql(sql)
    
    if not result['success']:
        return f"Error retrieving data: {result['error']}"
    
    if result['row_count'] != 2:
        return f"Could not find data for both {start_year} and {end_year}. Make sure both years are available."
    
    # Extract values
    data = result['data']
    start_value = data[0][metric]
    end_value = data[1][metric]
    
    # Calculate growth rate
    if start_value == 0:
        return f"Cannot calculate growth rate: {metric} was $0 in {start_year}"
    
    growth_rate = ((end_value - start_value) / abs(start_value)) * 100
    
    # Determine growth direction
    if growth_rate > 0:
        direction = "grew"
    elif growth_rate < 0:
        direction = "declined"
    else:
        direction = "remained unchanged"
    
    return (
        f"{company}'s {metric.replace('_', ' ')} {direction} from "
        f"${start_value:,} ({start_year}) to ${end_value:,} ({end_year}), "
        f"a {'growth' if growth_rate >= 0 else 'decline'} of {abs(growth_rate):.1f}%"
    )


# =============================================================================
# TOOL 4: Calculate Net Margin
# =============================================================================

def calculate_net_margin(company: str, year: int) -> str:
    """
    Calculate the net profit margin for a company in a specific year.
    
    Net Margin = (Net Income / Revenue) * 100
    
    This shows what percentage of revenue becomes profit after all expenses.
    
    Args:
        company: Company name (e.g., 'Alpha Corp')
        year: Fiscal year (2019-2023)
    
    Returns:
        Formatted net margin with underlying values.
    
    Example:
        calculate_net_margin("Alpha Corp", 2022)
        # Returns: "Alpha Corp's net margin in 2022 was 14.0% (Net Income: $23,500,000, Revenue: $168,000,000)"
    """
    db = get_database()
    
    logger.info(f"Calculating net margin for {company} in {year}")
    
    # Normalize company name (case-insensitive matching)
    company, error = normalize_company_name(company, db)
    if error:
        return error
    
    sql = f"""
        SELECT revenue, net_income
        FROM financials
        WHERE company = '{company}' AND fiscal_year = {year}
    """
    
    result = db.execute_sql(sql)
    
    if not result['success']:
        return f"Error: {result['error']}"
    
    if result['row_count'] == 0:
        available_companies = db.get_all_companies()
        return f"No data found for {company} in {year}. Available companies: {', '.join(available_companies)}"
    
    data = result['data'][0]
    revenue = data['revenue']
    net_income = data['net_income']
    
    if revenue == 0:
        return f"{company} had $0 revenue in {year}, cannot calculate margin."
    
    margin = (net_income / revenue) * 100
    
    return (
        f"{company}'s net margin in {year} was {margin:.1f}% "
        f"(Net Income: ${net_income:,}, Revenue: ${revenue:,})"
    )


# =============================================================================
# TOOL 5: Compare Companies
# =============================================================================

def compare_companies(
    companies: list[str],
    metric: str,
    year: int
) -> str:
    """
    Compare a specific metric across multiple companies for a given year.
    
    Use this tool to rank companies by a financial metric.
    
    Args:
        companies: List of company names to compare.
                   Use ["all"] to compare all companies.
        metric: The metric to compare.
                Options: 'revenue', 'net_income', 'total_assets', 'total_equity'
        year: Fiscal year for comparison (2019-2023)
    
    Returns:
        Ranked comparison of companies by the specified metric.
    
    Example:
        compare_companies(["Alpha Corp", "Beta Inc"], "revenue", 2023)
        compare_companies(["all"], "net_income", 2022)
    """
    db = get_database()
    
    logger.info(f"Comparing {companies} by {metric} in {year}")
    
    # Validate metric
    valid_metrics = ['revenue', 'net_income', 'total_assets', 'total_equity']
    if metric.lower() not in valid_metrics:
        return f"Invalid metric '{metric}'. Valid options: {', '.join(valid_metrics)}"
    
    metric = metric.lower()
    
    # Handle "all" companies
    if companies == ["all"] or "all" in [c.lower() for c in companies]:
        sql = f"""
            SELECT company, {metric}
            FROM financials
            WHERE fiscal_year = {year}
            ORDER BY {metric} DESC
        """
    else:
        # Normalize company names (case-insensitive matching)
        normalized_companies = []
        for comp in companies:
            normalized, error = normalize_company_name(comp, db)
            if error:
                return error
            normalized_companies.append(normalized)
        
        # Build IN clause
        company_list = "', '".join(normalized_companies)
        sql = f"""
            SELECT company, {metric}
            FROM financials
            WHERE fiscal_year = {year}
            AND company IN ('{company_list}')
            ORDER BY {metric} DESC
        """
    
    result = db.execute_sql(sql)
    
    if not result['success']:
        return f"Error: {result['error']}"
    
    if result['row_count'] == 0:
        return f"No data found for year {year}."
    
    # Format as ranked list
    lines = [f"Comparison of {metric.replace('_', ' ')} in {year} (highest to lowest):\n"]
    
    for i, row in enumerate(result['data'], 1):
        lines.append(f"  {i}. {row['company']}: ${row[metric]:,}")
    
    # Add summary
    highest = result['data'][0]
    lowest = result['data'][-1]
    
    if len(result['data']) > 1:
        lines.append(f"\nHighest: {highest['company']} (${highest[metric]:,})")
        lines.append(f"Lowest: {lowest['company']} (${lowest[metric]:,})")
    
    return "\n".join(lines)


# =============================================================================
# TOOL 6: Get Schema Info
# =============================================================================

def get_available_data() -> str:
    """
    Get information about what data is available in the database.
    
    Use this tool to find out:
    - Which companies are in the database
    - What years are covered
    - What metrics are available
    
    This is useful when you need to validate user input or understand
    the scope of available data.
    
    Args:
        None
    
    Returns:
        Summary of available data.
    """
    db = get_database()
    
    companies = db.get_all_companies()
    years = db.get_all_years()
    metrics = db.get_metrics()
    record_count = db.get_record_count()
    
    return f"""Available Data Summary:

Companies ({len(companies)}):
  {', '.join(companies)}

Years ({len(years)}):
  {', '.join(map(str, years))}

Metrics:
  {', '.join(metrics)}

Total Records: {record_count}

Note: Each company has data for each year, so there are {len(companies)} × {len(years)} = {len(companies) * len(years)} records.
"""


# =============================================================================
# TOOL 7: Compare Net Margins Over Time
# =============================================================================

def compare_net_margins_over_time(
    companies: list[str],
    start_year: int,
    end_year: int
) -> str:
    """
    Compare net profit margins for multiple companies across a range of years.
    
    This shows how profitability has changed over time for each company.
    
    Args:
        companies: List of company names to compare
        start_year: Starting year (e.g., 2020)
        end_year: Ending year (e.g., 2023)
    
    Returns:
        Table showing net margins for each company across years.
    
    Example:
        compare_net_margins_over_time(["Beta Inc", "Gamma Ltd"], 2020, 2023)
    """
    db = get_database()
    
    logger.info(f"Comparing net margins for {companies} from {start_year} to {end_year}")
    
    # Normalize company names (case-insensitive matching)
    normalized_companies = []
    for comp in companies:
        normalized, error = normalize_company_name(comp, db)
        if error:
            return error
        normalized_companies.append(normalized)
    
    company_list = "', '".join(normalized_companies)
    
    sql = f"""
        SELECT company, fiscal_year, revenue, net_income
        FROM financials
        WHERE company IN ('{company_list}')
        AND fiscal_year BETWEEN {start_year} AND {end_year}
        ORDER BY company, fiscal_year
    """
    
    result = db.execute_sql(sql)
    
    if not result['success']:
        return f"Error: {result['error']}"
    
    if result['row_count'] == 0:
        return "No data found for the specified companies and years."
    
    # Organize by company
    by_company: dict[str, list[dict]] = {}
    for row in result['data']:
        company = row['company']
        if company not in by_company:
            by_company[company] = []
        
        margin = (row['net_income'] / row['revenue'] * 100) if row['revenue'] > 0 else 0
        by_company[company].append({
            'year': row['fiscal_year'],
            'margin': margin,
        })
    
    # Format output
    lines = [f"Net Margin Comparison ({start_year}-{end_year}):\n"]
    
    for company, data in by_company.items():
        lines.append(f"  {company}:")
        for entry in data:
            lines.append(f"    {entry['year']}: {entry['margin']:.1f}%")
        
        # Calculate change
        if len(data) >= 2:
            first = data[0]['margin']
            last = data[-1]['margin']
            change = last - first
            direction = "improved" if change > 0 else "declined" if change < 0 else "unchanged"
            lines.append(f"    Change: {'+' if change >= 0 else ''}{change:.1f}pp ({direction})")
        lines.append("")
    
    return "\n".join(lines)


# =============================================================================
# Tool Registry - For CrewAI Integration
# =============================================================================

def get_all_tools():
    """
    Return all tools in a format suitable for CrewAI.
    
    This function is used by the agent to discover available tools.
    """
    return [
        execute_sql_query,
        get_company_financials,
        calculate_growth_rate,
        calculate_net_margin,
        compare_companies,
        get_available_data,
        compare_net_margins_over_time,
    ]
