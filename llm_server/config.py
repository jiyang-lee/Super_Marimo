import logging
import os

logger = logging.getLogger("llm_server")

RUN_MODE = os.getenv("RUN_MODE", os.getenv("MOCK_MODE", "false").lower() == "true" and "mock" or "gpu").lower()
MOCK_MODE = RUN_MODE == "mock"
LLM_MODEL_ID = os.getenv("LLM_MODEL_ID", "LGAI-EXAONE/EXAONE-3.5-2.4B-Instruct")
LLM_MODEL_REVISION = os.getenv("LLM_MODEL_REVISION", "c38726a")
HF_TOKEN = os.getenv("HF_TOKEN", "")
HF_LLM_BACKEND = os.getenv("HF_LLM_BACKEND", "endpoint").lower()
HF_LLM_ENDPOINT_URL = os.getenv("HF_LLM_ENDPOINT_URL", "")
HF_LLM_ROUTER_BASE_URL = os.getenv("HF_LLM_ROUTER_BASE_URL", "https://router.huggingface.co/v1")
HF_LLM_ROUTER_MODEL = os.getenv("HF_LLM_ROUTER_MODEL", "Qwen/Qwen3-14B:nscale")
HF_TIMEOUT_SEC = float(os.getenv("HF_TIMEOUT_SEC", "8"))
