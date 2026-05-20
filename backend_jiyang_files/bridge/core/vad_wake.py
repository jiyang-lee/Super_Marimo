import random
import re

WAKE_PREFIXES = (
    "안녕마리모",
    "안녕하세요마리모",
    "마리모",
    "마니모",
    "마린모",
    "마리모야",
    "마리모씨",
    "마니모야",
    "마린모야",
)

WAKE_SUFFIXES = (
    "",
    "야",
    "씨",
    "님",
    "요",
    "좀",
    "부탁",
    "불러",
    "불러줘",
    "도와줘",
    "도와줄래",
    "말해줘",
)

EXIT_PHRASES = (
    "잘가",
    "잘 가",
    "바이",
    "그만해",
    "대화 종료",
    "대화종료",
    "종료해 마리모",
    "종료핵마리모",
)

WAKE_GREETINGS = (
    "안녕, 불렀구나. 천천히 말해줘.",
    "응, 마리모야. 편하게 이야기핧도 돼.",
    "안녕. 무엇을 도와줄까?",
    "그래, 듣고 있어. 말해줘.",
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
    if re.fullmatch(r"[ㅋㅎㅜㅠ]{2,}", normalized):
        return True
    if normalized in {"음", "어", "아", "네", "응", "예", "흠", "휴", "헉"}:
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

    if re.search(r"[?？]", text):
        return False

    question_cues = (
        "왜", "뭐", "누구", "언제", "어디", "어떻게", "얼마", "몇", "어떤",
        "궁금", "알려줘", "말해줘", "도와줘", "설명", "해줘", "할까",
        "될까", "되나", "되니", "가능해",
    )
    if any(cue in normalized for cue in question_cues):
        return False

    if len(normalized) <= 1:
        return True

    if _is_repeated_chunk(normalized):
        return True

    return False


def retry_prompt() -> str:
    return "조금만 다시 말해줄래?"


def pick_wake_greeting() -> str:
    return random.choice(WAKE_GREETINGS)
