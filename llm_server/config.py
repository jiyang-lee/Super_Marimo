import logging
import os

logger = logging.getLogger("llm_server")

MOCK_MODE = os.getenv("MOCK_MODE", "false").lower() == "true"
LLM_MODEL_ID = os.getenv("LLM_MODEL_ID", "LGAI-EXAONE/EXAONE-3.5-2.4B-Instruct")
LLM_MODEL_REVISION = os.getenv("LLM_MODEL_REVISION", "c38726a")
