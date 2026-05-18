import sys
from pathlib import Path


VOICE_AGENT_DIR = Path(__file__).resolve().parents[1]
if str(VOICE_AGENT_DIR) not in sys.path:
    sys.path.insert(0, str(VOICE_AGENT_DIR))
