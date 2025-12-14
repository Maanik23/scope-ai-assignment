"""
Test Suite - Tests for data models and validation logic.

These tests verify that our Pydantic models correctly handle:
- Valid data
- Type coercion
- Edge cases
- Invalid data rejection
"""

import pytest
from pydantic import ValidationError

from src.models import (
    FinancialRecord,
    ValidationResult,
    DataQualityFlag,
    QueryResult,
)


class TestFinancialRecord:
    """Tests for the FinancialRecord Pydantic model."""
    
    def test_valid_record(self):
        """Test creating a valid financial record."""
        record = FinancialRecord(
            company="Alpha Corp",
            fiscal_year=2023,
            revenue=185000000,
            net_income=26000000,
            total_assets=258000000,
            total_equity=148000000,
        )
        
        assert record.company == "Alpha Corp"
        assert record.fiscal_year == 2023
        assert record.revenue == 185000000
        assert record.net_income == 26000000
    
    def test_string_number_coercion(self):
        """Test that string numbers are converted to integers."""
        record = FinancialRecord(
            company="Test Corp",
            fiscal_year=2023,
            revenue="185000000",  # String 
            net_income="26000000",
            total_assets="258000000",
            total_equity="148000000",
        )
        
        assert record.revenue == 185000000
        assert isinstance(record.revenue, int)
    
    def test_float_to_int_coercion(self):
        """Test that floats are converted to integers."""
        record = FinancialRecord(
            company="Test Corp",
            fiscal_year=2023,
            revenue=185000000.0,  # Float
            net_income=26000000.5,
            total_assets=258000000,
            total_equity=148000000,
        )
        
        assert record.revenue == 185000000
        assert isinstance(record.revenue, int)
    
    def test_company_name_stripping(self):
        """Test that company names are stripped of whitespace."""
        record = FinancialRecord(
            company="  Alpha Corp  ",  # Whitespace
            fiscal_year=2023,
            revenue=100,
            net_income=10,
            total_assets=100,
            total_equity=50,
        )
        
        assert record.company == "Alpha Corp"
    
    def test_negative_net_income_allowed(self):
        """Test that negative net income (losses) is allowed."""
        record = FinancialRecord(
            company="Loss Corp",
            fiscal_year=2023,
            revenue=100000,
            net_income=-50000,  # Loss
            total_assets=100000,
            total_equity=50000,
        )
        
        assert record.net_income == -50000
    
    def test_negative_revenue_rejected(self):
        """Test that negative revenue is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            FinancialRecord(
                company="Bad Corp",
                fiscal_year=2023,
                revenue=-100000,  # Invalid
                net_income=10000,
                total_assets=100000,
                total_equity=50000,
            )
        
        assert "revenue" in str(exc_info.value).lower()
    
    def test_zero_assets_rejected(self):
        """Test that zero assets is rejected (must be positive)."""
        with pytest.raises(ValidationError):
            FinancialRecord(
                company="No Assets Corp",
                fiscal_year=2023,
                revenue=100000,
                net_income=10000,
                total_assets=0,  # Invalid - must be > 0
                total_equity=50000,
            )
    
    def test_empty_company_rejected(self):
        """Test that empty company name is rejected."""
        with pytest.raises(ValidationError):
            FinancialRecord(
                company="",  # Invalid
                fiscal_year=2023,
                revenue=100000,
                net_income=10000,
                total_assets=100000,
                total_equity=50000,
            )
    
    def test_year_range_validation(self):
        """Test that year must be in valid range."""
        # Valid year
        record = FinancialRecord(
            company="Test",
            fiscal_year=2023,
            revenue=100,
            net_income=10,
            total_assets=100,
            total_equity=50,
        )
        assert record.fiscal_year == 2023
        
        # Invalid year - too old
        with pytest.raises(ValidationError):
            FinancialRecord(
                company="Test",
                fiscal_year=1800,  # Too old
                revenue=100,
                net_income=10,
                total_assets=100,
                total_equity=50,
            )
    
    def test_net_margin_calculation(self):
        """Test the net_margin property."""
        record = FinancialRecord(
            company="Test",
            fiscal_year=2023,
            revenue=1000000,
            net_income=150000,  # 15% margin
            total_assets=500000,
            total_equity=300000,
        )
        
        assert record.net_margin == 15.0
    
    def test_net_margin_zero_revenue(self):
        """Test net_margin handles zero revenue."""
        record = FinancialRecord(
            company="Pre-Revenue",
            fiscal_year=2023,
            revenue=0,
            net_income=-50000,
            total_assets=100000,
            total_equity=50000,
        )
        
        assert record.net_margin == 0.0
    
    def test_to_dict(self):
        """Test conversion to dictionary."""
        record = FinancialRecord(
            company="Test",
            fiscal_year=2023,
            revenue=100000,
            net_income=10000,
            total_assets=100000,
            total_equity=50000,
        )
        
        d = record.to_dict()
        
        assert d['company'] == "Test"
        assert d['fiscal_year'] == 2023
        assert d['revenue'] == 100000
        assert 'quality_flag' not in d  # Should not be in dict


class TestValidationResult:
    """Tests for the ValidationResult model."""
    
    def test_empty_result(self):
        """Test empty validation result."""
        result = ValidationResult()
        
        assert result.total_processed == 0
        assert result.success_rate == 0.0
        assert result.is_successful
    
    def test_with_valid_records(self):
        """Test result with valid records."""
        records = [
            FinancialRecord(
                company=f"Company {i}",
                fiscal_year=2023,
                revenue=100000,
                net_income=10000,
                total_assets=100000,
                total_equity=50000,
            )
            for i in range(5)
        ]
        
        result = ValidationResult(valid_records=records)
        
        assert result.total_processed == 5
        assert result.success_rate == 100.0
        assert result.is_successful
    
    def test_with_errors(self):
        """Test result with errors."""
        result = ValidationResult(
            valid_records=[],
            errors=[
                {"row": 1, "error": "Missing revenue"},
                {"row": 2, "error": "Invalid year"},
            ]
        )
        
        assert result.total_processed == 2
        assert result.success_rate == 0.0
        assert not result.is_successful
    
    def test_summary_generation(self):
        """Test summary string generation."""
        result = ValidationResult(
            valid_records=[],
            errors=[{"row": 1, "error": "Test error"}],
            warnings=["Warning 1"],
        )
        
        summary = result.summary()
        
        assert "Validation Summary" in summary
        assert "Error" in summary
        assert "Warning" in summary


class TestQueryResult:
    """Tests for the QueryResult model."""
    
    def test_successful_result(self):
        """Test successful query result."""
        result = QueryResult(
            success=True,
            data=[{"company": "Test", "revenue": 100000}],
            row_count=1,
        )
        
        assert result.success
        assert result.row_count == 1
    
    def test_failed_result(self):
        """Test failed query result."""
        result = QueryResult(
            success=False,
            error="Invalid SQL syntax",
        )
        
        assert not result.success
        assert "Invalid SQL" in result.error
    
    def test_to_natural_language_success(self):
        """Test natural language conversion for success."""
        result = QueryResult(
            success=True,
            data=[{"company": "Alpha Corp", "revenue": 185000000}],
            row_count=1,
        )
        
        nl = result.to_natural_language()
        
        assert "1 result" in nl
        assert "Alpha Corp" in nl
    
    def test_to_natural_language_failure(self):
        """Test natural language conversion for failure."""
        result = QueryResult(
            success=False,
            error="Table not found",
        )
        
        nl = result.to_natural_language()
        
        assert "failed" in nl.lower()
        assert "Table not found" in nl
