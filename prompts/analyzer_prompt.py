"""Analyzer Agent Prompts — Cross-Source Verification"""

EXTRACT_CLAIMS_PROMPT = """You are a Claims Extractor. Given a search result summary, extract atomic factual claims.

## Search Result
Source: {source_title} ({source_url})
Summary: {summary}

## Instructions
Extract specific, verifiable factual claims. Each claim should be:
- Atomic (one fact per claim)
- Specific (contains concrete numbers, names, or descriptions)
- Verifiable (could be checked against another source)

Do NOT extract opinions, vague statements, or subjective assessments.

## Output Format (JSON)
{{
  "claims": [
    "Claim 1 text...",
    "Claim 2 text...",
    ...
  ]
}}
"""

ANALYZE_AND_SYNTHESIZE_PROMPT = """You are a Research Analyzer. Synthesize verified search results into a structured analysis.

## User Query
{user_query}

## Previous Round Analysis
{previous_analysis_text}

## Verified Claims
{verified_claims_text}

## Search Summaries
{search_summaries_text}

## Instructions
Create a comprehensive analysis that:
1. Groups related findings by theme/dimension
2. Highlights areas of consensus (multiple sources agree)
3. Flags disputed areas (sources contradict each other)
4. Notes gaps where information is insufficient
5. Preserves source attribution for each key point
6. If a previous round analysis is given, keep its findings that are still valid and merge them with the new results (this round's searches targeted gaps in the previous report), so the final analysis covers both

Keep the analysis concise (under 800 words) — the Writer will expand it into a full report.

## Output Format
Write a structured analysis in markdown. Use these confidence markers:
- ✅ for claims supported by multiple sources
- ⚠️ for disputed claims (note both sides)
- ❓ for claims from a single source only
"""
