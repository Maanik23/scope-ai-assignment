"""
Test Suite - Tests for agent tools.

These tests verify that our financial analysis tools:
- Return correct values
- Handle edge cases
- Provide helpful error messages
"""

import pytest
import tempfile
import os
from pathlib import Path

from src.database import FinancialDatabase
from src.tools import (
    execute_sql_query,
    get_company_financials,
    calculate_growth_rate,
    calculate_net_margin,
    compare_companies,
    get_available_data,
    compare_net_margins_over_time,
    set_database,
)


@pytest.fixture
def populated_db():
    """Create a temporary database with test data."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        db = FinancialDatabase(db_path)
        db.initialize()
        
        # Insert test data
        test_records = [
            # Alpha Corp - consistent growth
            {"company": "Alpha Corp", "fiscal_year": 2019, "revenue": 100000000, "net_income": 10000000, "total_assets": 150000000, "total_equity": 80000000},
            {"company": "Alpha Corp", "fiscal_year": 2020, "revenue": 110000000, "net_income": 12000000, "total_assets": 165000000, "total_equity": 88000000},
            {"company": "Alpha Corp", "fiscal_year": 2021, "revenue": 125000000, "net_income": 15000000, "total_assets": 180000000, "total_equity": 100000000},
            {"company": "Alpha Corp", "fiscal_year": 2022, "revenue": 140000000, "net_income": 18000000, "total_assets": 200000000, "total_equity": 115000000},
            {"company": "Alpha Corp", "fiscal_year": 2023, "revenue": 160000000, "net_income": 22000000, "total_assets": 225000000, "total_equity": 132000000},
            # Beta Inc - smaller company
            {"company": "Beta Inc", "fiscal_year": 2019, "revenue": 50000000, "net_income": 4000000, "total_assets": 70000000, "total_equity": 35000000},
            {"company": "Beta Inc", "fiscal_year": 2020, "revenue": 55000000, "net_income": 4500000, "total_assets": 75000000, "total_equity": 38000000},
            {"company": "Beta Inc", "fiscal_year": 2021, "revenue": 60000000, "net_income": 5000000, "total_assets": 82000000, "total_equity": 42000000},
            {"company": "Beta Inc", "fiscal_year": 2022, "revenue": 65000000, "net_income": 5500000, "total_assets": 88000000, "total_equity": 46000000},
            {"company": "Beta Inc", "fiscal_year": 2023, "revenue": 72000000, "net_income": 6500000, "total_assets": 95000000, "total_equity": 52000000},
        ]
        
        db.insert_records(test_records)
        set_database(db)
        
        yield db


class TestExecuteSQLQuery:
    """Tests for the execute_sql_query tool."""
    
    def test_simple_select(self, populated_db):
        """Test simple SELECT query."""
        result = execute_sql_query(
            "SELECT revenue FROM financials WHERE company = 'Alpha Corp' AND fiscal_year = 2023"
        )
        
        assert "160,000,000" in result or "160000000" in result
    
    def test_select_all(self, populated_db):
        """Test SELECT * query."""
        result = execute_sql_query(
            "SELECT * FROM financials WHERE company = 'Beta Inc' AND fiscal_year = 2022"
        )
        
        assert "Beta Inc" in result
        assert "65,000,000" in result or "65000000" in result
    
    def test_no_results(self, populated_db):
        """Test query with no results."""
        result = execute_sql_query(
            "SELECT * FROM financials WHERE company = 'Nonexistent Corp'"
        )
        
        assert "No results" in result
    
    def test_invalid_sql(self, populated_db):
        """Test handling of invalid SQL."""
        result = execute_sql_query("SELECT * FROM wrong_table")
        
        assert "failed" in result.lower() or "error" in result.lower()
    
    def test_non_select_rejected(self, populated_db):
        """Test that non-SELECT queries are rejected."""
        result = execute_sql_query("DROP TABLE financials")
        
        assert "SELECT" in result or "not allowed" in result.lower()


class TestGetCompanyFinancials:
    """Tests for the get_company_financials tool."""
    
    def test_specific_year(self, populated_db):
        """Test getting financials for specific year."""
        result = get_company_financials("Alpha Corp", 2023)
        
        assert "Alpha Corp" in result
        assert "160,000,000" in result or "160000000" in result
    
    def test_all_years(self, populated_db):
        """Test getting all years for a company."""
        result = get_company_financials("Alpha Corp")
        
        assert "2019" in result
        assert "2023" in result
    
    def test_nonexistent_company(self, populated_db):
        """Test handling of nonexistent company."""
        result = get_company_financials("Nonexistent Corp", 2023)
        
        assert "not found" in result.lower() or "Available companies" in result
    
    def test_case_insensitive_match(self, populated_db):
        """Test that company names are matched case-insensitively."""
        result = get_company_financials("alpha corp", 2023)  # lowercase
        
        # Should either find it or suggest the correct name
        assert "Alpha Corp" in result or "revenue" in result.lower()


class TestCalculateGrowthRate:
    """Tests for the calculate_growth_rate tool."""
    
    def test_positive_growth(self, populated_db):
        """Test calculating positive growth."""
        result = calculate_growth_rate("Alpha Corp", "revenue", 2019, 2023)
        
        assert "60" in result  # 100M to 160M = 60% growth
        assert "growth" in result.lower() or "grew" in result.lower()
    
    def test_different_metrics(self, populated_db):
        """Test growth for different metrics."""
        result = calculate_growth_rate("Alpha Corp", "net_income", 2019, 2023)
        
        assert "120" in result  # 10M to 22M = 120% growth
    
    def test_invalid_metric(self, populated_db):
        """Test handling of invalid metric."""
        result = calculate_growth_rate("Alpha Corp", "invalid_metric", 2019, 2023)
        
        assert "Invalid metric" in result or "Valid options" in result
    
    def test_invalid_year_range(self, populated_db):
        """Test handling of invalid year range."""
        result = calculate_growth_rate("Alpha Corp", "revenue", 2023, 2019)  # Reversed
        
        assert "before" in result.lower() or "must be" in result.lower()
    
    def test_nonexistent_company(self, populated_db):
        """Test handling of nonexistent company."""
        result = calculate_growth_rate("Nonexistent", "revenue", 2019, 2023)
        
        assert "not found" in result.lower() or "could not find" in result.lower()


class TestCalculateNetMargin:
    """Tests for the calculate_net_margin tool."""
    
    def test_margin_calculation(self, populated_db):
        """Test correct margin calculation."""
        # 2023: net_income=22M, revenue=160M -> margin = 13.75%
        result = calculate_net_margin("Alpha Corp", 2023)
        
        assert "13" in result or "14" in result  # Approximately 13.75%
        assert "%" in result
    
    def test_shows_underlying_values(self, populated_db):
        """Test that underlying values are shown."""
        result = calculate_net_margin("Alpha Corp", 2023)
        
        assert "Net Income" in result or "net_income" in result.lower()
        assert "Revenue" in result or "revenue" in result.lower()
    
    def test_nonexistent_company(self, populated_db):
        """Test handling of nonexistent company."""
        result = calculate_net_margin("Nonexistent", 2023)
        
        assert "not found" in result.lower() or "No data" in result


class TestCompareCompanies:
    """Tests for the compare_companies tool."""
    
    def test_compare_two_companies(self, populated_db):
        """Test comparing two companies."""
        result = compare_companies(["Alpha Corp", "Beta Inc"], "revenue", 2023)
        
        assert "Alpha Corp" in result
        assert "Beta Inc" in result
        assert "160,000,000" in result or "160000000" in result
    
    def test_compare_all_companies(self, populated_db):
        """Test comparing all companies."""
        result = compare_companies(["all"], "revenue", 2023)
        
        assert "Alpha Corp" in result
        assert "Beta Inc" in result
        assert "Highest" in result or "highest" in result
    
    def test_ranking_order(self, populated_db):
        """Test that companies are ranked correctly."""
        result = compare_companies(["all"], "revenue", 2023)
        
        # Alpha Corp should be #1 (160M vs 72M)
        lines = result.split('\n')
        first_ranking = [l for l in lines if '1.' in l]
        if first_ranking:
            assert 'Alpha Corp' in first_ranking[0]
    
    def test_invalid_metric(self, populated_db):
        """Test handling of invalid metric."""
        result = compare_companies(["Alpha Corp"], "invalid", 2023)
        
        assert "Invalid metric" in result


class TestGetAvailableData:
    """Tests for the get_available_data tool."""
    
    def test_lists_companies(self, populated_db):
        """Test that all companies are listed."""
        result = get_available_data()
        
        assert "Alpha Corp" in result
        assert "Beta Inc" in result
    
    def test_lists_years(self, populated_db):
        """Test that all years are listed."""
        result = get_available_data()
        
        assert "2019" in result
        assert "2023" in result
    
    def test_lists_metrics(self, populated_db):
        """Test that metrics are listed."""
        result = get_available_data()
        
        assert "revenue" in result
        assert "net_income" in result


class TestCompareNetMarginsOverTime:
    """Tests for the compare_net_margins_over_time tool."""
    
    def test_compare_margins(self, populated_db):
        """Test comparing margins over time."""
        result = compare_net_margins_over_time(
            ["Alpha Corp", "Beta Inc"],
            2020,
            2023
        )
        
        assert "Alpha Corp" in result
        assert "Beta Inc" in result
        assert "2020" in result
        assert "2023" in result
        assert "%" in result
    
    def test_shows_change(self, populated_db):
        """Test that change over time is shown."""
        result = compare_net_margins_over_time(
            ["Alpha Corp"],
            2019,
            2023
        )
        
        assert "Change" in result or "change" in result
