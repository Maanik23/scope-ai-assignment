"""
Test Suite - Tests for database operations.

These tests verify that our database layer correctly:
- Creates tables
- Inserts records
- Executes queries
- Handles errors
"""

import pytest
import tempfile
import os
from pathlib import Path

from src.database import FinancialDatabase, Financial, Base


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        db = FinancialDatabase(db_path)
        db.initialize()
        yield db


@pytest.fixture
def sample_records():
    """Sample financial records for testing."""
    return [
        {
            "company": "Alpha Corp",
            "fiscal_year": 2022,
            "revenue": 168000000,
            "net_income": 23500000,
            "total_assets": 235000000,
            "total_equity": 132000000,
        },
        {
            "company": "Alpha Corp",
            "fiscal_year": 2023,
            "revenue": 185000000,
            "net_income": 26000000,
            "total_assets": 258000000,
            "total_equity": 148000000,
        },
        {
            "company": "Beta Inc",
            "fiscal_year": 2022,
            "revenue": 110000000,
            "net_income": 11800000,
            "total_assets": 162000000,
            "total_equity": 83000000,
        },
        {
            "company": "Beta Inc",
            "fiscal_year": 2023,
            "revenue": 118000000,
            "net_income": 13200000,
            "total_assets": 178000000,
            "total_equity": 92000000,
        },
    ]


class TestDatabaseInitialization:
    """Tests for database initialization."""
    
    def test_create_database(self, temp_db):
        """Test that database is created successfully."""
        assert temp_db.db_path.exists()
    
    def test_tables_created(self, temp_db):
        """Test that tables are created."""
        # Should be able to query without error
        result = temp_db.execute_sql("SELECT * FROM financials")
        assert result['success']
        assert result['row_count'] == 0
    
    def test_reset_clears_data(self, temp_db, sample_records):
        """Test that reset clears all data."""
        # Insert some records
        temp_db.insert_records(sample_records)
        assert temp_db.get_record_count() == 4
        
        # Reset
        temp_db.reset()
        
        # Should be empty
        assert temp_db.get_record_count() == 0


class TestRecordInsertion:
    """Tests for inserting records."""
    
    def test_insert_single_record(self, temp_db, sample_records):
        """Test inserting a single record."""
        count = temp_db.insert_records([sample_records[0]])
        assert count == 1
        assert temp_db.get_record_count() == 1
    
    def test_insert_multiple_records(self, temp_db, sample_records):
        """Test inserting multiple records."""
        count = temp_db.insert_records(sample_records)
        assert count == 4
        assert temp_db.get_record_count() == 4
    
    def test_duplicate_rejection(self, temp_db, sample_records):
        """Test that duplicate company+year combinations are rejected."""
        temp_db.insert_records([sample_records[0]])
        
        # Try to insert same record again
        with pytest.raises(Exception):
            temp_db.insert_records([sample_records[0]])


class TestQueryExecution:
    """Tests for SQL query execution."""
    
    def test_select_all(self, temp_db, sample_records):
        """Test selecting all records."""
        temp_db.insert_records(sample_records)
        
        result = temp_db.execute_sql("SELECT * FROM financials")
        
        assert result['success']
        assert result['row_count'] == 4
        assert len(result['data']) == 4
    
    def test_select_with_filter(self, temp_db, sample_records):
        """Test selecting with WHERE clause."""
        temp_db.insert_records(sample_records)
        
        result = temp_db.execute_sql(
            "SELECT * FROM financials WHERE company = 'Alpha Corp'"
        )
        
        assert result['success']
        assert result['row_count'] == 2
        for row in result['data']:
            assert row['company'] == 'Alpha Corp'
    
    def test_select_specific_columns(self, temp_db, sample_records):
        """Test selecting specific columns."""
        temp_db.insert_records(sample_records)
        
        result = temp_db.execute_sql(
            "SELECT company, revenue FROM financials WHERE fiscal_year = 2023"
        )
        
        assert result['success']
        assert 'company' in result['data'][0]
        assert 'revenue' in result['data'][0]
    
    def test_order_by(self, temp_db, sample_records):
        """Test ORDER BY clause."""
        temp_db.insert_records(sample_records)
        
        result = temp_db.execute_sql(
            "SELECT company, revenue FROM financials ORDER BY revenue DESC"
        )
        
        assert result['success']
        revenues = [r['revenue'] for r in result['data']]
        assert revenues == sorted(revenues, reverse=True)
    
    def test_aggregate_functions(self, temp_db, sample_records):
        """Test aggregate functions like SUM, AVG."""
        temp_db.insert_records(sample_records)
        
        result = temp_db.execute_sql(
            "SELECT AVG(revenue) as avg_revenue FROM financials WHERE company = 'Alpha Corp'"
        )
        
        assert result['success']
        assert result['data'][0]['avg_revenue'] is not None
    
    def test_non_select_rejected(self, temp_db):
        """Test that non-SELECT queries are rejected."""
        result = temp_db.execute_sql("DELETE FROM financials")
        
        assert not result['success']
        assert "SELECT" in result['error']
    
    def test_invalid_sql(self, temp_db):
        """Test handling of invalid SQL."""
        result = temp_db.execute_sql("SELECT * FROM nonexistent_table")
        
        assert not result['success']
        assert result['error'] is not None


class TestMetadataQueries:
    """Tests for metadata query methods."""
    
    def test_get_all_companies(self, temp_db, sample_records):
        """Test getting list of companies."""
        temp_db.insert_records(sample_records)
        
        companies = temp_db.get_all_companies()
        
        assert len(companies) == 2
        assert "Alpha Corp" in companies
        assert "Beta Inc" in companies
    
    def test_get_all_years(self, temp_db, sample_records):
        """Test getting list of years."""
        temp_db.insert_records(sample_records)
        
        years = temp_db.get_all_years()
        
        assert 2022 in years
        assert 2023 in years
    
    def test_get_metrics(self, temp_db):
        """Test getting list of available metrics."""
        metrics = temp_db.get_metrics()
        
        assert 'revenue' in metrics
        assert 'net_income' in metrics
        assert 'total_assets' in metrics
        assert 'total_equity' in metrics
    
    def test_get_schema_description(self, temp_db, sample_records):
        """Test schema description generation."""
        temp_db.insert_records(sample_records)
        
        schema = temp_db.get_schema_description()
        
        assert "financials" in schema.lower()
        assert "Alpha Corp" in schema
        assert "revenue" in schema.lower()
    
    def test_get_company_data(self, temp_db, sample_records):
        """Test getting data for a specific company."""
        temp_db.insert_records(sample_records)
        
        data = temp_db.get_company_data("Alpha Corp")
        
        assert len(data) == 2
        assert all(d['company'] == 'Alpha Corp' for d in data)
    
    def test_get_company_data_specific_year(self, temp_db, sample_records):
        """Test getting data for a specific company and year."""
        temp_db.insert_records(sample_records)
        
        data = temp_db.get_company_data("Alpha Corp", 2023)
        
        assert len(data) == 1
        assert data[0]['fiscal_year'] == 2023
        assert data[0]['revenue'] == 185000000
