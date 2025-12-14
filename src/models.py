"""
Data Models - Pydantic schemas for financial data validation.

This module defines strict data contracts that ensure data quality
before it enters the database. Every row from the CSV is validated
against these schemas.

Features:
- Runtime type validation with Pydantic v2
- Automatic type coercion for CSV data (strings to integers)
- Computed financial properties (net_margin, ROE, equity_ratio)
- Data quality flags for tracking issues
"""

from __future__ import annotations

from typing import Optional
from decimal import Decimal
from pydantic import BaseModel, Field, field_validator, model_validator
from enum import Enum


class DataQualityFlag(str, Enum):
    """Flags for tracking data quality issues during ingestion."""
    CLEAN = "clean"
    MISSING_VALUE_IMPUTED = "missing_value_imputed"
    NEGATIVE_VALUE_WARNING = "negative_value_warning"
    OUTLIER_DETECTED = "outlier_detected"


class FinancialRecord(BaseModel):
    """
    Core data model for a single financial record.
    
    Represents one row of company financial data for a specific fiscal year.
    All monetary values are stored as integers (cents would be better for
    real finance, but this data uses whole dollars).
    
    Validation Rules:
    - company: Non-empty string, stripped of whitespace
    - fiscal_year: Integer between 1900-2100
    - revenue: Non-negative integer (can be 0 for pre-revenue companies)
    - net_income: Can be negative (companies can have losses)
    - total_assets: Positive integer (must have some assets)
    - total_equity: Can be negative (if liabilities > assets)
    """
    
    company: str = Field(
        ..., 
        min_length=1, 
        description="Company name, e.g., 'Alpha Corp'"
    )
    fiscal_year: int = Field(
        ..., 
        ge=1900, 
        le=2100, 
        description="Fiscal year, e.g., 2023"
    )
    revenue: int = Field(
        ..., 
        ge=0, 
        description="Total revenue in dollars"
    )
    net_income: int = Field(
        ..., 
        description="Net income in dollars (can be negative)"
    )
    total_assets: int = Field(
        ..., 
        gt=0, 
        description="Total assets in dollars"
    )
    total_equity: int = Field(
        ..., 
        description="Total equity in dollars (can be negative)"
    )
    
    # Optional: Track data quality
    quality_flag: DataQualityFlag = Field(
        default=DataQualityFlag.CLEAN,
        description="Data quality indicator"
    )
    
    @field_validator('company', mode='before')
    @classmethod
    def clean_company_name(cls, v: str) -> str:
        """Strip whitespace and normalize company name."""
        if isinstance(v, str):
            return v.strip()
        return v
    
    @field_validator('revenue', 'net_income', 'total_assets', 'total_equity', mode='before')
    @classmethod
    def coerce_to_int(cls, v) -> int:
        """
        Handle various numeric formats from CSV.
        
        Handles: "125000000", "125,000,000", 125000000.0, etc.
        """
        if v is None or v == '':
            raise ValueError("Missing value - cannot be empty")
        
        if isinstance(v, str):
            # Remove commas and whitespace
            v = v.replace(',', '').strip()
        
        try:
            # Convert to float first (handles "125000000.0"), then to int
            return int(float(v))
        except (ValueError, TypeError) as e:
            raise ValueError(f"Cannot convert '{v}' to integer: {e}")
    
    @model_validator(mode='after')
    def validate_financial_consistency(self) -> 'FinancialRecord':
        """
        Cross-field validation for financial sanity checks.
        
        These are warnings, not errors - we flag but don't reject.
        """
        # Flag if net income is suspiciously high relative to revenue
        if self.revenue > 0 and self.net_income > self.revenue:
            # Net income > revenue is unusual (possible but rare)
            self.quality_flag = DataQualityFlag.OUTLIER_DETECTED
        
        # Flag negative equity (technically valid but noteworthy)
        if self.total_equity < 0:
            self.quality_flag = DataQualityFlag.NEGATIVE_VALUE_WARNING
            
        return self
    
    def to_dict(self) -> dict:
        """Convert to dictionary for database insertion."""
        return {
            'company': self.company,
            'fiscal_year': self.fiscal_year,
            'revenue': self.revenue,
            'net_income': self.net_income,
            'total_assets': self.total_assets,
            'total_equity': self.total_equity,
        }
    
    @property
    def net_margin(self) -> float:
        """Calculate net profit margin (net_income / revenue)."""
        if self.revenue == 0:
            return 0.0
        return round(self.net_income / self.revenue * 100, 2)
    
    @property
    def return_on_equity(self) -> float:
        """Calculate ROE (net_income / total_equity)."""
        if self.total_equity == 0:
            return 0.0
        return round(self.net_income / self.total_equity * 100, 2)
    
    @property
    def equity_ratio(self) -> float:
        """Calculate equity ratio (total_equity / total_assets)."""
        if self.total_assets == 0:
            return 0.0
        return round(self.total_equity / self.total_assets * 100, 2)


class ValidationResult(BaseModel):
    """
    Result of validating a batch of records.
    
    Tracks both successful records and any validation errors,
    allowing the ingestion pipeline to report on data quality.
    """
    
    valid_records: list[FinancialRecord] = Field(default_factory=list)
    errors: list[dict] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    
    @property
    def total_processed(self) -> int:
        """Total records attempted."""
        return len(self.valid_records) + len(self.errors)
    
    @property
    def success_rate(self) -> float:
        """Percentage of records that passed validation."""
        if self.total_processed == 0:
            return 0.0
        return round(len(self.valid_records) / self.total_processed * 100, 2)
    
    @property
    def is_successful(self) -> bool:
        """True if all records passed validation."""
        return len(self.errors) == 0
    
    def summary(self) -> str:
        """Human-readable validation summary."""
        lines = [
            f"Validation Summary",
            f"=" * 40,
            f"Total Processed: {self.total_processed}",
            f"Valid Records:   {len(self.valid_records)}",
            f"Errors:          {len(self.errors)}",
            f"Success Rate:    {self.success_rate}%",
        ]
        
        if self.warnings:
            lines.append(f"\nWarnings ({len(self.warnings)}):")
            for w in self.warnings[:5]:  # Show first 5
                lines.append(f"  - {w}")
            if len(self.warnings) > 5:
                lines.append(f"  ... and {len(self.warnings) - 5} more")
        
        if self.errors:
            lines.append(f"\nErrors ({len(self.errors)}):")
            for e in self.errors[:5]:  # Show first 5
                lines.append(f"  - Row {e.get('row', '?')}: {e.get('error', 'Unknown')}")
            if len(self.errors) > 5:
                lines.append(f"  ... and {len(self.errors) - 5} more")
        
        return "\n".join(lines)


class QueryResult(BaseModel):
    """
    Structured result from a financial query.
    
    Used to pass data between tools and the agent in a type-safe way.
    """
    
    success: bool = Field(..., description="Whether the query succeeded")
    data: Optional[list[dict]] = Field(default=None, description="Query results")
    error: Optional[str] = Field(default=None, description="Error message if failed")
    sql_query: Optional[str] = Field(default=None, description="SQL that was executed")
    row_count: int = Field(default=0, description="Number of rows returned")
    
    def to_natural_language(self) -> str:
        """Convert result to a string the LLM can use in its response."""
        if not self.success:
            return f"Query failed: {self.error}"
        
        if not self.data or self.row_count == 0:
            return "No data found matching the query."
        
        # Format the data nicely
        lines = [f"Found {self.row_count} result(s):"]
        for row in self.data:
            parts = [f"{k}: {v:,}" if isinstance(v, int) else f"{k}: {v}" 
                     for k, v in row.items()]
            lines.append("  " + ", ".join(parts))
        
        return "\n".join(lines)
