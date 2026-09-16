"""Load prompts and invoice text, call the model adapter, and validate JSON."""

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from .config import PROMPTS_DIR, DEFAULT_PROMPT_VERSION, DEFAULT_MODEL, DEFAULT_MAX_OUTPUT_TOKENS, DEFAULT_TEMPERATURE
from .llm_client import get_llm_client
from .schema import validate_extraction

logger = logging.getLogger(__name__)


class ExtractionError(Exception):
    # Identifies failures while parsing or validating model extraction output.
    pass


# Load one versioned prompt template from the prompts directory.
def load_prompt(version: str = DEFAULT_PROMPT_VERSION) -> str:
    path = PROMPTS_DIR / f"{version}.txt"
    if not path.exists():
        raise FileNotFoundError(f"Prompt version {version} not found at {path}")
    return path.read_text(encoding="utf-8")


# Read the source invoice text and raise a clear error when it is missing.
def read_invoice(text_path: str | Path) -> str:
    path = Path(text_path)
    if not path.exists():
        raise FileNotFoundError(f"Invoice file not found: {path}")
    return path.read_text(encoding="utf-8")


# Run prompt insertion, provider generation, JSON parsing, and schema validation.
def extract_from_text(invoice_text: str, prompt_version: str = DEFAULT_PROMPT_VERSION,
                       model: str = DEFAULT_MODEL,
                       temperature: float = DEFAULT_TEMPERATURE,
                       max_output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS) -> Dict[str, Any]:
    prompt_template = load_prompt(prompt_version)
    enriched_prompt = prompt_template.replace("{{DOCUMENT}}", invoice_text)
    client = get_llm_client()
    raw_output = client.generate(enriched_prompt, model=model,
                                  temperature=temperature,
                                  max_output_tokens=max_output_tokens)

    # Safely parse JSON out of the raw response.
    try:
        payload = json.loads(raw_output)
    except Exception as exc:
        logger.warning("Malformed model JSON detected. Attempting recovery.")
        # Attempt to find a JSON object inside text if provider returns extra commentary.
        start = raw_output.find("{")
        end = raw_output.rfind("}")
        if start >= 0 and end > start:
            payload = json.loads(raw_output[start:end+1])
        else:
            raise ExtractionError(f"Malformed model output: {exc}") from exc

    # Validate with Pydantic.
    try:
        result = validate_extraction(payload)
    except Exception as exc:
        raise ExtractionError(f"Schema validation failed: {exc}") from exc

    return result.model_dump()


# Combine file reading and text extraction for the CLI and demo callers.
def extract_file(input_path: str | Path, prompt_version: str = DEFAULT_PROMPT_VERSION) -> Dict[str, Any]:
    invoice_text = read_invoice(input_path)
    return extract_from_text(invoice_text, prompt_version=prompt_version)
