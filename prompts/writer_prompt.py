"""Writer Agent Prompts — Citation-Tracked Report Generation"""

WRITE_REPORT_PROMPT = """You are a Research Report Writer. Generate a well-structured research report with proper citations.

## User Query
{user_query}

## Analysis Summary
{analysis_summary}

## Critic Feedback from Previous Iteration (if any)
{critic_feedback}

## Instructions
Write a comprehensive research report that:
1. Directly answers the user's query
2. Is structured with clear sections and headings
3. Cites sources for every key claim using [Source: URL] format
4. Marks confidence levels: ✅ (multi-source confirmed), ⚠️ (disputed), ❓ (single source)
5. Includes a "Limitations & Gaps" section noting what couldn't be fully verified
6. Ends with a concise "Key Takeaways" section

## Formatting Rules
- Use markdown formatting
- Keep total length under 2000 words
- Every factual claim MUST have a citation
- If previous critic feedback exists, specifically address the missing aspects

## Output
Write the report directly in markdown.
"""

REFINE_REPORT_PROMPT = """You are refining an existing research report based on critic feedback.

## Original Report
{previous_report}

## Critic Feedback
Score: {score}/10
Missing aspects: {missing_aspects}
Suggestions: {suggestions}

## New Information from Additional Search
{new_analysis}

## Instructions
Revise the report to address the critic's feedback. Specifically:
1. Add content for each missing aspect listed
2. Incorporate new search findings with proper citations
3. Do NOT remove existing well-cited content
4. Maintain the same formatting and structure

Output the complete revised report in markdown.
"""
