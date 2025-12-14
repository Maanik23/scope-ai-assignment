# AI Coding Assistance Disclosure

## Overview

I used Claude (Anthropic) as an LLM AI assistant during this project. I'm sharing this transparently because I believe knowing how to effectively use AI tools is part of being a modern developer — but so is knowing what to build yourself.

## How I Used AI Assistance

### Where AI Helped

**Boilerplate and Scaffolding**
- Setting up the initial project structure and file organization
- Writing standard imports and class scaffolding
- Generating docstrings and code comments

**Test Case Generation**
- AI helped generate the test file structures
- I provided the test scenarios and AI helped write the assertions
- Reviewed and adjusted tests to match actual behavior

**Configuration Setup**
- Environment configuration patterns (.env.example, requirements.txt)
- Chainlit and SQLAlchemy configuration boilerplate

**Documentation Drafting**
- Initial README structure
- Helped format tables and code examples

### What I Did Myself

**Architecture and Design**
- Decided to use SQL-based retrieval instead of Vector RAG after thinking through the requirements — financial data needs exact number matching, and semantic search could return the wrong year's data
- Designed the tool-based approach with 7 specialized functions instead of one generic "query anything" tool
- Chose Pydantic for validation because I wanted to catch bad data at ingestion, not at query time

**Problem Solving**
- Analyzed the CSV data to understand the schema and design appropriate validations
- Figured out the right SQL queries for each financial calculation
- Debugged the integration between LangGraph agent and the tools
- Solved Windows compatibility issues (switched from CrewAI to LangGraph when I hit SIGHUP signal errors)

**Implementation Details**
- Wrote the core logic for growth rate and margin calculations
- Designed the error handling approach (tools should never crash, just return helpful error messages)
- Connected all the pieces together and made sure they work end-to-end

**Testing and Verification**
- Ran the system with various queries to verify correctness
- Checked edge cases like what happens with missing data or invalid company names
- Made sure the SQL injection prevention actually works

## My Approach

I treated AI as a coding partner, not a replacement for thinking. When AI suggested something, I'd ask myself:
- Does this actually solve the problem correctly?
- Is this the right approach for the requirements?
- Would I write it differently?

Sometimes I used AI suggestions directly. Other times I modified them significantly or wrote my own version because the suggestion didn't quite fit. The architecture decisions — which are really what matter — came from understanding the problem myself.

## What This Shows

I think the value isn't in whether you used AI or not, but in:
- Knowing what to build and why
- Being able to evaluate whether AI suggestions are correct
- Understanding the code well enough to debug and modify it
- Making good technical decisions independently


