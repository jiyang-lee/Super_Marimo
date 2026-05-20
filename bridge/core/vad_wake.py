import random
import re

WAKE_PREFIXES = (
    "안녕마리모",
    "안녕하세요마리모",
    "마리모",
    "마리모야",
    "마리모씨",
    "마리모님",
    "마리모아",
    "마리모아야",
)

WAKE_SUFFIXES = (
    "",
    "야",
    "아",
    "씨",
    "님",
    "좀",
    "불러",
    "불러줘",
    "말해줘",
    "대답해줘",
)

EXIT_PHRASES = (
    "잘가",
    "바이",
    "그만",
    "대화종료",
    "대화종료마리모",
    "종료마리모",
    "종료해마리모",
)

WAKE_GREETINGS = (
    "안녕, 편하게 이야기해도 돼.",
    "응, 뭐 도와줄까?",
    "안녕. 지금 뭐가 필요해?",
    "그래, 말해줘.",
)


def normalize_text(text: str) -> str:
    normalized = (text or "").lower().strip()
    normalized = re.sub(r"[\s\.,!?~:;(){}\[\]<>/\\|\-\"'`]+", "", normalized)
    return normalized


def has_wake_phrase(text: str) -> bool:
    normalized = normalize_text(text)
    if not normalized:
        return False
    for phrase in WAKE_PREFIXES:
        if not normalized.startswith(phrase):
            continue
        suffix = normalized[len(phrase):]
        if not suffix:
            return True
        if any(suffix.startswith(allowed) for allowed in WAKE_SUFFIXES if allowed):
            return True
    return False


def has_exit_phrase(text: str) -> bool:
    normalized = normalize_text(text)
    return any(phrase in normalized for phrase in EXIT_PHRASES)


def strip_wake_phrase(text: str) -> str:
    raw = (text or "").strip()
    compact = normalize_text(raw)
    for phrase in WAKE_PREFIXES:
        if not compact.startswith(phrase):
            continue
        return raw[len(raw) - len(compact) + len(phrase):].lstrip(" \t\r\n:,-")
    return raw


def is_noise_transcript(text: str) -> bool:
    normalized = normalize_text(text)
    if not normalized:
        return True
    if re.fullmatch(r"[\?？]{2,}", normalized):
        return True
    if len(set(normalized)) == 1:
        return True
    if _is_repeated_chunk(normalized) and len(normalized) <= 8:
        return True
    return False


def _is_repeated_chunk(text: str) -> bool:
    if len(text) < 2:
        return False
    max_chunk = min(4, len(text) // 2)
    for size in range(1, max_chunk + 1):
        if len(text) % size != 0:
            continue
        chunk = text[:size]
        if chunk * (len(text) // size) == text:
            return True
    return False


def should_retry_followup(text: str) -> bool:
    if is_noise_transcript(text):
        return True

    normalized = normalize_text(text)
    if not normalized:
        return True

    if "?" in text or "？" in text:
        return False

    question_cues = (
        "뭐",
        "왜",
        "어디",
        "언제",
        "어떻게",
        "누구",
        "무엇",
        "몇",
    )
    if any(cue in normalized for cue in question_cues):
        return False

    if len(normalized) <= 1:
        return True

    if _is_repeated_chunk(normalized):
        return True

    return False


def retry_prompt() -> str:
    return "다시 한 번 말해줄래?"


def pick_wake_greeting() -> str:
    return random.choice(WAKE_GREETINGS)
