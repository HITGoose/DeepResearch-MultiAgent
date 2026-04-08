"""
DeepResearch-Agent Configuration
"""
import os
from dotenv import load_dotenv

load_dotenv()

# ===== LLM Configuration =====
# Main model for complex reasoning (Planner, Writer, Critic)
MAIN_MODEL = os.getenv("MAIN_MODEL", "deepseek-chat")
MAIN_MODEL_BASE_URL = os.getenv("MAIN_MODEL_BASE_URL", "https://api.deepseek.com")
MAIN_MODEL_API_KEY = os.getenv("MAIN_MODEL_API_KEY", "")

# Light model for simulation evaluation and summarization
LIGHT_MODEL = os.getenv("LIGHT_MODEL", "deepseek-chat")
LIGHT_MODEL_BASE_URL = os.getenv("LIGHT_MODEL_BASE_URL", "https://api.deepseek.com")
LIGHT_MODEL_API_KEY = os.getenv("LIGHT_MODEL_API_KEY", "")

# ===== Search Configuration =====
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
MAX_SEARCH_RESULTS_PER_QUERY = 5

# ===== Agent Parameters =====
# Planner: Simulate-Before-Act
NUM_CANDIDATE_PLANS = 3          # Number of candidate plans to generate
COVERAGE_SCORE_THRESHOLD = 0.6   # Minimum coverage score to accept a plan

# Critic: LLM-as-a-Judge
CRITIC_SCORE_THRESHOLD = 6.0     # Score out of 10; below this triggers re-planning
MAX_ITERATIONS = 3               # Maximum refinement iterations

# Analyzer: Cross-Source Verification
NLI_MODEL_NAME = "cross-encoder/nli-deberta-v3-base"
CONTRADICTION_THRESHOLD = 0.8    # NLI confidence threshold for contradiction

# ===== Context Management =====
MAX_SUMMARY_TOKENS = 500         # Max tokens per search result summary
MAX_REPORT_TOKENS = 3000         # Max tokens for final report
MEMORY_DIR = "outputs/memory"    # Directory for File-as-Memory storage

# ===== Output =====
OUTPUT_DIR = "outputs/reports"
