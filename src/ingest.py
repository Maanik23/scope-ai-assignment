"""
Data Ingestion Pipeline - CSV loading, validation, and database persistence.

This module orchestrates the entire data ingestion process:
1. Load raw CSV data
2. Validate each row with Pydantic
3. Handle data quality issues
4. Persist to SQLite database
5. Generate ingestion report

Design Principles:
- Fail-fast validation (reject bad data early)
- Clear error messages for debugging
- Idempotent operations (safe to run multiple times)
- Detailed progress and quality reporting
"""

from __future__ import annotations

import csv
import logging
from pathlib import Path
from typing import Optional
from datetime import datetime

import pandas as pd
from pydantic import ValidationError

from src.models import FinancialRecord, ValidationResult, DataQualityFlag
from src.database import FinancialDatabase

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DataIngestionPipeline:
    """
    Orchestrates the complete data ingestion process.
    
    Responsibilities:
    - Load CSV data (handles encoding, delimiters)
    - Validate each row against Pydantic schema
    - Track and report data quality issues
    - Insert valid records into database
    - Generate summary report
    
    Usage:
        pipeline = DataIngestionPipeline(
            csv_path="data/financials.csv",
            db_path="data/financials.db"
        )
        result = pipeline.run()
        print(result.summary())
    """
    
    def __init__(
        self,
        csv_path: str = "data/financials.csv",
        db_path: str = "data/financials.db",
        reset_db: bool = True,
    ):
        """
        Initialize the ingestion pipeline.
        
        Args:
            csv_path: Path to the source CSV file
            db_path: Path to the SQLite database
            reset_db: If True, clear existing data before ingestion
        """
        self.csv_path = Path(csv_path)
        self.db_path = Path(db_path)
        self.reset_db = reset_db
        
        # Validate CSV exists
        if not self.csv_path.exists():
            raise FileNotFoundError(f"CSV file not found: {self.csv_path}")
        
        # Initialize database
        self.db = FinancialDatabase(str(self.db_path))
    
    def load_csv(self) -> pd.DataFrame:
        """
        Load CSV file into a pandas DataFrame.
        
        Handles common CSV issues:
        - Different encodings (UTF-8, Latin-1)
        - Trailing whitespace
        - Empty rows
        
        Returns:
            DataFrame with raw CSV data
        """
        logger.info(f"Loading CSV from: {self.csv_path}")
        
        # Try UTF-8 first, fall back to Latin-1
        try:
            df = pd.read_csv(self.csv_path, encoding='utf-8')
        except UnicodeDecodeError:
            logger.warning("UTF-8 failed, trying Latin-1 encoding")
            df = pd.read_csv(self.csv_path, encoding='latin-1')
        
        # Clean column names (strip whitespace, lowercase)
        df.columns = df.columns.str.strip().str.lower()
        
        # Remove completely empty rows
        df = df.dropna(how='all')
        
        logger.info(f"Loaded {len(df)} rows from CSV")
        return df
    
    def validate_row(self, row: dict, row_number: int) -> tuple[Optional[FinancialRecord], Optional[dict]]:
        """
        Validate a single row of data against the Pydantic schema.
        
        Args:
            row: Dictionary of column values
            row_number: Row number for error reporting
            
        Returns:
            Tuple of (validated_record, error_dict)
            One will always be None
        """
        try:
            record = FinancialRecord(**row)
            return record, None
            
        except ValidationError as e:
            # Extract meaningful error messages
            error_messages = []
            for error in e.errors():
                field = error.get('loc', ('unknown',))[0]
                msg = error.get('msg', 'Validation failed')
                error_messages.append(f"{field}: {msg}")
            
            return None, {
                'row': row_number,
                'error': "; ".join(error_messages),
                'data': row,
            }
    
    def validate_all(self, df: pd.DataFrame) -> ValidationResult:
        """
        Validate all rows in the DataFrame.
        
        Args:
            df: DataFrame with raw data
            
        Returns:
            ValidationResult with valid records and errors
        """
        result = ValidationResult()
        
        for idx, row in df.iterrows():
            # Convert row to dict, handling NaN values
            row_dict = {k: (v if pd.notna(v) else None) for k, v in row.to_dict().items()}
            row_number = idx + 2  # +2 because CSV has header and pandas is 0-indexed
            
            record, error = self.validate_row(row_dict, row_number)
            
            if record:
                result.valid_records.append(record)
                
                # Track quality warnings
                if record.quality_flag != DataQualityFlag.CLEAN:
                    result.warnings.append(
                        f"Row {row_number} ({record.company}, {record.fiscal_year}): "
                        f"{record.quality_flag.value}"
                    )
            else:
                result.errors.append(error)
        
        return result
    
    def run(self) -> ValidationResult:
        """
        Execute the complete ingestion pipeline.
        
        Steps:
        1. Load CSV
        2. Validate all rows
        3. Initialize database
        4. Insert valid records
        5. Return results
        
        Returns:
            ValidationResult with summary of ingestion
        """
        logger.info("=" * 50)
        logger.info("Starting Data Ingestion Pipeline")
        logger.info("=" * 50)
        
        # Step 1: Load CSV
        df = self.load_csv()
        
        # Step 2: Validate
        logger.info("Validating data...")
        result = self.validate_all(df)
        
        logger.info(f"Validation complete: {len(result.valid_records)} valid, "
                   f"{len(result.errors)} errors")
        
        # Step 3: Initialize database
        if self.reset_db:
            logger.info("Resetting database...")
            self.db.reset()
        else:
            self.db.initialize()
        
        # Step 4: Insert valid records
        if result.valid_records:
            logger.info(f"Inserting {len(result.valid_records)} records into database...")
            records_dict = [r.to_dict() for r in result.valid_records]
            inserted = self.db.insert_records(records_dict)
            logger.info(f"Successfully inserted {inserted} records")
        else:
            logger.warning("No valid records to insert!")
        
        # Step 5: Final report
        logger.info("=" * 50)
        logger.info("Ingestion Complete!")
        logger.info(f"Database: {self.db_path}")
        logger.info(f"Total records in DB: {self.db.get_record_count()}")
        logger.info("=" * 50)
        
        return result
    
    def generate_report(self, result: ValidationResult) -> str:
        """
        Generate a detailed ingestion report.
        
        Args:
            result: ValidationResult from the run
            
        Returns:
            Formatted report string
        """
        report_lines = [
            "=" * 60,
            "DATA INGESTION REPORT",
            f"Generated: {datetime.now().isoformat()}",
            "=" * 60,
            "",
            "SOURCE",
            "-" * 30,
            f"CSV File: {self.csv_path}",
            f"Database: {self.db_path}",
            "",
            "VALIDATION RESULTS",
            "-" * 30,
            result.summary(),
            "",
            "DATABASE STATE",
            "-" * 30,
            f"Total Records: {self.db.get_record_count()}",
            f"Companies: {', '.join(self.db.get_all_companies())}",
            f"Years: {', '.join(map(str, self.db.get_all_years()))}",
            "",
            "SCHEMA",
            "-" * 30,
            self.db.get_schema_description(),
        ]
        
        return "\n".join(report_lines)


def main():
    """
    Entry point for running ingestion from command line.
    
    Usage:
        python -m src.ingest
        # or
        python src/ingest.py
    """
    import argparse
    
    parser = argparse.ArgumentParser(description="Ingest financial data from CSV to SQLite")
    parser.add_argument(
        "--csv", 
        default="data/financials.csv",
        help="Path to CSV file"
    )
    parser.add_argument(
        "--db", 
        default="data/financials.db",
        help="Path to SQLite database"
    )
    parser.add_argument(
        "--no-reset",
        action="store_true",
        help="Don't reset database before ingestion"
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Generate detailed report after ingestion"
    )
    
    args = parser.parse_args()
    
    try:
        pipeline = DataIngestionPipeline(
            csv_path=args.csv,
            db_path=args.db,
            reset_db=not args.no_reset,
        )
        
        result = pipeline.run()
        
        print("\n" + result.summary())
        
        if args.report:
            report = pipeline.generate_report(result)
            print("\n" + report)
        
        # Exit with error if validation failed
        if not result.is_successful:
            exit(1)
            
    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        exit(1)
    except Exception as e:
        logger.exception(f"Ingestion failed: {e}")
        exit(1)


if __name__ == "__main__":
    main()
