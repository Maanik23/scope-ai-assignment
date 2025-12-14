# Financial AI Assistant

An AI assistant that answers investor-style questions about company financials using an **Agentic SQL** approach.

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![LangGraph](https://img.shields.io/badge/LangGraph-0.2+-green.svg)
![Gemini](https://img.shields.io/badge/Gemini-2.0-orange.svg)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                           User Interface                            │
│                    (Chainlit Web UI / CLI)                          │
└─────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         LangGraph Agent Layer                       │
│              "Senior Financial Analyst" Agent                       │
│         (Interprets questions, selects tools, forms answers)        │
└─────────────────────────────────────────────────────────────────────┘
                                   │
                    ┌──────────────┼──────────────┐
                    ▼              ▼              ▼
           ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
           │ SQL Query   │ │ Calculator  │ │ Comparison  │
           │    Tool     │ │    Tool     │ │    Tool     │
           └─────────────┘ └─────────────┘ └─────────────┘
                    │              │              │
                    └──────────────┼──────────────┘
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         SQLite Database                             │
│                    (Validated Financial Data)                       │
└─────────────────────────────────────────────────────────────────────┘
                                   ▲
                                   │
┌─────────────────────────────────────────────────────────────────────┐
│                      Data Ingestion Pipeline                        │
│           (CSV → Pydantic Validation → SQLite)                      │
└─────────────────────────────────────────────────────────────────────┘
```

### Design Rationale

| Design Choice | Rationale |
|:---|:---|
| **SQL over Vector RAG** | Financial data requires exact numbers. Vector search could return wrong year's data. |
| **Pydantic Validation** | Ensures data quality before database insertion. Catches issues early. |
| **LangGraph Agent** | Modern agentic approach with explicit tool selection and reasoning. |
| **SQLite** | Simple, portable, zero configuration. Appropriate for this data size. |
| **Chainlit UI** | Modern interface that visualizes agent reasoning process. |

---

## Quick Start

### Prerequisites

- Python 3.11+
- Google Gemini API key ([Get one here](https://aistudio.google.com/app/apikey))

### Installation

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/scope-ai-assignment.git
cd scope-ai-assignment

# Create virtual environment
python -m venv venv
source venv\Scripts\activate (Windows)

# Install dependencies
pip install -r requirements.txt

# Configure API key
cp .env.example .env
# Edit .env and add your GOOGLE_API_KEY
```

### Run Data Ingestion

```bash
# Ingest financial data from CSV to SQLite
python -m src.ingest --report

# Output:
# Validation Summary
# ==================
# Total Processed: 50
# Valid Records:   50
# Success Rate:    100%
```

### Run the Chatbot

**Option 1: Web UI (Chainlit)**
```bash
chainlit run app.py

# Opens at http://localhost:8000
```

**Option 2: CLI**
```bash
# Interactive mode
python cli.py

# Single query
python cli.py "What was Alpha Corp's revenue in 2022?"
```

---

## Project Structure

```
scope-ai-assignment/
├── data/
│   ├── financials.csv          # Raw source data (50 records)
│   └── financials.db           # SQLite database (generated)
├── src/
│   ├── __init__.py
│   ├── models.py               # Pydantic schemas with validation
│   ├── database.py             # SQLAlchemy ORM and DB operations
│   ├── ingest.py               # Data ingestion pipeline
│   ├── tools.py                # Agent tools (7 tools)
│   └── agent.py                # LangGraph agent configuration
├── tests/
│   ├── test_models.py          # Model validation tests
│   ├── test_database.py        # Database operation tests
│   └── test_tools.py           # Tool function tests
├── app.py                      # Chainlit web UI
├── cli.py                      # Command-line interface
├── requirements.txt
├── README.md                   # This file
├── AI_USAGE.md                 # AI assistance disclosure
└── .env.example                # Environment template
```

---

## Data Schema

### Source Data (financials.csv)

| Column | Type | Description |
|:---|:---|:---|
| `company` | String | Company name (10 companies) |
| `fiscal_year` | Integer | Year (2019-2023) |
| `revenue` | Integer | Total revenue in USD |
| `net_income` | Integer | Net income in USD |
| `total_assets` | Integer | Total assets in USD |
| `total_equity` | Integer | Total equity in USD |

### Available Companies

Alpha Corp, Beta Inc, Delta PLC, Epsilon Holdings, Gamma Ltd, Iota Technologies, Kappa Industries, Lambda Group, Theta Solutions, Zeta Enterprises

### Available Metrics

- `revenue` - Total revenue
- `net_income` - Net profit/loss
- `total_assets` - Total assets
- `total_equity` - Shareholders' equity

**Computed Metrics (via tools):**
- Net Margin = (Net Income / Revenue) × 100
- Growth Rate = ((End - Start) / Start) × 100

---

## Agent Tools

The AI agent has access to 7 specialized tools:

| Tool | Purpose |
|:---|:---|
| `execute_sql_query` | Run custom SQL SELECT queries |
| `get_company_financials` | Get all data for a company |
| `calculate_growth_rate` | Compute growth between two years |
| `calculate_net_margin` | Compute net profit margin |
| `compare_companies` | Rank companies by a metric |
| `get_available_data` | List available companies/years |
| `compare_net_margins_over_time` | Compare margins across years |

---

## Sample Queries and Outputs

### Query 1: Simple Lookup
```
Q: What was Alpha Corp's revenue in 2022?

A: Alpha Corp's revenue in 2022 was $168,000,000.
```

### Query 2: Comparison
```
Q: Which company had the highest net income in 2023?

A: Based on the data, the ranking by net income in 2023:
   1. Epsilon Holdings: $55,000,000
   2. Iota Technologies: $54,200,000
   3. Gamma Ltd: $38,500,000
   ...
   Highest: Epsilon Holdings ($55,000,000)
```

### Query 3: Growth Calculation
```
Q: How did Delta PLC's revenue grow between 2019 and 2023?

A: Delta PLC's revenue grew from $67,000,000 (2019) to $98,000,000 (2023),
   a growth of 46.3%.
```

### Query 4: Margin Comparison
```
Q: Compare the net margin of Beta Inc and Gamma Ltd from 2020 to 2023.

A: Net Margin Comparison (2020-2023):

   Beta Inc:
     2020: 9.7%
     2021: 10.3%
     2022: 10.7%
     2023: 11.2%
     Change: +1.5pp (improved)

   Gamma Ltd:
     2020: 13.6%
     2021: 13.8%
     2022: 13.9%
     2023: 13.9%
     Change: +0.3pp (improved)
```

### Query 5: Multi-step Analysis
```
Q: Which company had the highest revenue growth between 2019 and 2023?

A: Revenue growth (2019-2023) by company:
   1. Theta Solutions: 47.7% ($44M → $65M)
   2. Delta PLC: 46.3% ($67M → $98M)
   3. Alpha Corp: 48.0% ($125M → $185M)
   ...
   Highest growth: Alpha Corp (48.0%)
```

---

## Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_models.py -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html
```

---

## Configuration

### Environment Variables

| Variable | Description | Default |
|:---|:---|:---|
| `GOOGLE_API_KEY` | Gemini API key (required) | - |
| `GEMINI_MODEL` | Model to use | `gemini-2.0-flash-exp` |

### LLM Provider

This project uses **Google Gemini** as the LLM provider.

To get an API key:
1. Go to [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Click "Create API Key"
3. Copy the key to your `.env` file

---

## Design Decisions and Trade-offs

### Why SQL Instead of Vector RAG?

**Vector RAG is risky for financial data:**
- Semantic similarity might return "revenue in 2021" when asked for "2022"
- Numbers need exact matching, not approximate
- SQL is deterministic and auditable

**SQL advantages:**
- Exact lookups: `WHERE company='X' AND year=2022`
- Aggregations: `SUM`, `AVG`, `MAX`
- Ordering: `ORDER BY revenue DESC`

### Why LangGraph?

- Provides explicit control over agent reasoning loop
- ReAct pattern for tool selection
- Built-in memory for conversation context
- Windows-compatible (unlike some alternatives)

### Why Pydantic Validation?

- Type safety at runtime
- Clear error messages for data quality
- Self-documenting schema
- Industry-standard practice

---

## Known Limitations

1. **Single-session memory only** - Conversation context is lost when restarting
2. **No complex NL parsing** - "Last year" must be specified as "2023"
3. **English only** - No multi-language support
4. **No authentication** - Open access to all data

### Future Enhancements

- Add long-term user memory
- Support natural date expressions ("last year", "Q3 2022")
- Add more financial ratios (ROE, Debt-to-Equity)
- Multi-company trend visualizations
- Export results to Excel/PDF

---

## License

MIT License - See LICENSE file.

---

## Acknowledgments

Built as part of the SCOPE AI Engineer Assessment.
