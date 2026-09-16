import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BASE_DIR / ".env")

DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash-lite")
DEFAULT_TEMPERATURE = float(os.getenv("temperature", "0.1"))
DEFAULT_MAX_OUTPUT_TOKENS = int(os.getenv("max_output_tokens", "800"))
DEFAULT_PROMPT_VERSION = os.getenv("prompt_version", "v5")

DATA_DIR = BASE_DIR / "data"
INVOICES_DIR = DATA_DIR / "invoices"
GROUND_TRUTH_DIR = DATA_DIR / "ground_truth"
OUTPUTS_DIR = DATA_DIR / "outputs"
PROMPTS_DIR = BASE_DIR / "prompts"
RESULTS_DIR = BASE_DIR / "results"

FIELDS = [
    "invoice_number",
    "invoice_date",
    "vendor",
    "bill_to",
    "subtotal",
    "tax",
    "total",
    "payment_terms",
    "currency",
]
