"""
Database Layer - SQLAlchemy models and database operations.

This module handles all database interactions using SQLAlchemy ORM.
SQLite is used for simplicity and portability.

Features:
- ORM models for type-safe database operations
- Raw SQL execution with security controls (SELECT only)
- Schema introspection for AI agent context
- Session management with automatic commit/rollback
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, Any
from contextlib import contextmanager

from sqlalchemy import (
    create_engine, 
    Column, 
    Integer, 
    String, 
    Float,
    UniqueConstraint,
    Index,
    text,
)
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from sqlalchemy.exc import SQLAlchemyError

# Base class for all ORM models
Base = declarative_base()


class Financial(Base):
    """
    SQLAlchemy ORM model for the financials table.
    
    This mirrors our Pydantic FinancialRecord but is specific
    to database operations.
    """
    
    __tablename__ = 'financials'
    
    # Primary key - auto-incrementing ID
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Core fields
    company = Column(String(100), nullable=False, index=True)
    fiscal_year = Column(Integer, nullable=False, index=True)
    revenue = Column(Integer, nullable=False)
    net_income = Column(Integer, nullable=False)
    total_assets = Column(Integer, nullable=False)
    total_equity = Column(Integer, nullable=False)
    
    # Ensure no duplicate company+year combinations
    __table_args__ = (
        UniqueConstraint('company', 'fiscal_year', name='uq_company_year'),
        Index('idx_company_year', 'company', 'fiscal_year'),
    )
    
    def __repr__(self) -> str:
        return f"<Financial(company='{self.company}', year={self.fiscal_year}, revenue={self.revenue:,})>"
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'company': self.company,
            'fiscal_year': self.fiscal_year,
            'revenue': self.revenue,
            'net_income': self.net_income,
            'total_assets': self.total_assets,
            'total_equity': self.total_equity,
        }


class FinancialDatabase:
    """
    Database manager for financial data operations.
    
    Provides a clean API for:
    - Creating/connecting to the database
    - Inserting validated records
    - Executing queries (both ORM and raw SQL)
    - Schema introspection for the AI agent
    
    Usage:
        db = FinancialDatabase("data/financials.db")
        db.initialize()
        db.insert_records(validated_records)
        results = db.query("SELECT * FROM financials WHERE company = 'Alpha Corp'")
    """
    
    def __init__(self, db_path: str = "data/financials.db"):
        """
        Initialize database connection.
        
        Args:
            db_path: Path to SQLite database file. Created if doesn't exist.
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # SQLAlchemy engine with connection pooling disabled for SQLite
        self.engine = create_engine(
            f"sqlite:///{self.db_path}",
            echo=False,  # Set to True for SQL debugging
            pool_pre_ping=True,  # Verify connections before use
        )
        
        # Session factory
        self.SessionLocal = sessionmaker(
            bind=self.engine,
            autocommit=False,
            autoflush=False,
        )
    
    def initialize(self) -> None:
        """
        Create all tables if they don't exist.
        
        Safe to call multiple times - won't drop existing data.
        """
        Base.metadata.create_all(self.engine)
    
    def drop_all(self) -> None:
        """
        Drop all tables. USE WITH CAUTION.
        
        Useful for testing or re-ingestion.
        """
        Base.metadata.drop_all(self.engine)
    
    def reset(self) -> None:
        """Drop and recreate all tables."""
        self.drop_all()
        self.initialize()
    
    @contextmanager
    def get_session(self):
        """
        Context manager for database sessions.
        
        Handles commit/rollback automatically.
        
        Usage:
            with db.get_session() as session:
                session.add(record)
        """
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    def insert_records(self, records: list[dict]) -> int:
        """
        Insert multiple financial records into the database.
        
        Args:
            records: List of dictionaries with financial data
            
        Returns:
            Number of records inserted
            
        Raises:
            SQLAlchemyError: If database operation fails
        """
        with self.get_session() as session:
            for record in records:
                financial = Financial(
                    company=record['company'],
                    fiscal_year=record['fiscal_year'],
                    revenue=record['revenue'],
                    net_income=record['net_income'],
                    total_assets=record['total_assets'],
                    total_equity=record['total_equity'],
                )
                session.add(financial)
        
        return len(records)
    
    def execute_sql(self, sql: str) -> dict:
        """
        Execute raw SQL query and return results.
        
        This is what the AI agent uses to query the database.
        Includes error handling and result formatting.
        
        Args:
            sql: SQL query string (SELECT only for safety)
            
        Returns:
            Dictionary with 'success', 'data', 'error', 'row_count'
        """
        # Basic SQL injection prevention - only allow SELECT
        sql_upper = sql.strip().upper()
        if not sql_upper.startswith('SELECT'):
            return {
                'success': False,
                'data': None,
                'error': "Only SELECT queries are allowed for safety.",
                'row_count': 0,
                'sql_query': sql,
            }
        
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(sql))
                
                # Fetch all rows and convert to list of dicts
                columns = result.keys()
                rows = [dict(zip(columns, row)) for row in result.fetchall()]
                
                return {
                    'success': True,
                    'data': rows,
                    'error': None,
                    'row_count': len(rows),
                    'sql_query': sql,
                }
                
        except SQLAlchemyError as e:
            return {
                'success': False,
                'data': None,
                'error': str(e),
                'row_count': 0,
                'sql_query': sql,
            }
    
    def get_all_companies(self) -> list[str]:
        """Get list of all unique company names."""
        with self.get_session() as session:
            result = session.query(Financial.company).distinct().all()
            return sorted([r[0] for r in result])
    
    def get_all_years(self) -> list[int]:
        """Get list of all unique fiscal years."""
        with self.get_session() as session:
            result = session.query(Financial.fiscal_year).distinct().all()
            return sorted([r[0] for r in result])
    
    def get_metrics(self) -> list[str]:
        """Get list of available metrics (column names)."""
        return ['revenue', 'net_income', 'total_assets', 'total_equity']
    
    def get_schema_description(self) -> str:
        """
        Generate a natural language description of the database schema.
        
        This is injected into the AI agent's system prompt so it
        understands what data is available.
        """
        companies = self.get_all_companies()
        years = self.get_all_years()
        
        schema = f"""
DATABASE SCHEMA:
================

Table: financials
-----------------
Contains financial data for {len(companies)} companies across fiscal years {min(years)}-{max(years)}.

Columns:
- company (TEXT): Company name. Available: {', '.join(companies)}
- fiscal_year (INTEGER): Fiscal year (2019-2023)
- revenue (INTEGER): Total revenue in dollars
- net_income (INTEGER): Net income in dollars (can be negative for losses)
- total_assets (INTEGER): Total assets in dollars
- total_equity (INTEGER): Total equity in dollars

Example Queries:
- Get revenue for a company: SELECT revenue FROM financials WHERE company = 'Alpha Corp' AND fiscal_year = 2022
- Compare companies: SELECT company, revenue FROM financials WHERE fiscal_year = 2023 ORDER BY revenue DESC
- Get all data for a company: SELECT * FROM financials WHERE company = 'Beta Inc' ORDER BY fiscal_year

Available Companies: {', '.join(companies)}
Available Years: {', '.join(map(str, years))}
Available Metrics: revenue, net_income, total_assets, total_equity

IMPORTANT: Always use exact company names as listed above. Names are case-sensitive.
"""
        return schema.strip()
    
    def get_record_count(self) -> int:
        """Get total number of records in the database."""
        with self.get_session() as session:
            return session.query(Financial).count()
    
    def get_company_data(self, company: str, year: Optional[int] = None) -> list[dict]:
        """
        Get financial data for a specific company.
        
        Args:
            company: Company name
            year: Optional specific year (all years if None)
            
        Returns:
            List of financial records as dictionaries
        """
        with self.get_session() as session:
            query = session.query(Financial).filter(Financial.company == company)
            if year:
                query = query.filter(Financial.fiscal_year == year)
            query = query.order_by(Financial.fiscal_year)
            
            return [r.to_dict() for r in query.all()]
