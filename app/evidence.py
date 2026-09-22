"""Conservative English value-presence checks, not semantic entailment."""

from dataclasses import dataclass
import re

from .retrieval import Hit, tokens

ABSTENTION = "I don't have enough grounded context to answer that question."
MIN_SUBJECT_COVERAGE = 0.75

_NUMBER_WORDS = (
    "zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|"
    "thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|"
    "thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred|thousand|million"
)
_NUMBER = rf"(?:\d+(?:[.,]\d+)*|(?:{_NUMBER_WORDS})(?:[ -](?:{_NUMBER_WORDS}))*)"
_SCALAR = re.compile(rf"\b{_NUMBER}\b", re.I)
_PERCENT = re.compile(rf"\b{_NUMBER}\s*(?:%|percent\b|per cent\b)", re.I)
_MONEY = re.compile(rf"(?:[$\u00a3\u20ac]\s*{_NUMBER}\b|\b(?:USD|EUR|GBP|PKR)\s*{_NUMBER}\b|"
                    rf"\b{_NUMBER}\s*(?:dollars?|cents?|euros?|pounds?|rupees?)\b)", re.I)
_VERSION = re.compile(r"\bv?\d+(?:\.\d+){1,3}(?:[-+][\w.]+)?\b|\bversion\s+\d+\b", re.I)
_DURATION_UNITS = {"second", "minute", "hour", "day", "week", "month", "year"}
_UNAVAILABLE = re.compile(r"\b(?:unknown|unspecified|undocumented|unavailable)\b|"
                          r"\bnot\s+(?:specified|documented|available|stated|published)\b", re.I)
_STOP = set((
    "a an the what which how is are was were be been being do does did of for to in on at by "
    "with from as and or after before per s me us tell give please can could would will "
    "many much long exact exactly current currently installed deployed running runs "
    "service contract guarantee guarantees guaranteed promise promises promised allowed allow "
    "price pricing cost costs charge charges dollar dollars percent percentage version "
    "number value amount limit maximum minimum total it its this that these those "
    "million thousand"
).split())


def _terms(text: str) -> set[str]:
    # Only normalize simple English plurals; this is not a semantic query rewriter.
    return {word[:-3] + "y" if word.endswith("ies") else
            word[:-1] if word.endswith("s") and not word.endswith("ss") and len(word) > 3 else word
            for word in tokens(text) if word not in _STOP and not word.isdigit()}


def required_values(question: str) -> tuple[str, ...]:
    q = " ".join(tokens(question))
    if not re.match(r"^(?:what|which|tell me|give me)\b", q) and not re.search(r"\bhow (?:many|much|long)\b", q):
        return ()
    if re.search(r"\b(?:should|procedure|strategy|steps|choose|upgrade|controls|practices|methods)\b", q):
        return ()
    required = []
    if re.search(r"\b(?:percentage|percent)\b", q):
        required.append("percentage")
    if re.search(r"\b(?:price|pricing|cost|costs|charge|charges)\b", q):
        required.append("money")
    if re.search(r"\bversion\b", q):
        required.append("version")
    if re.search(r"\bhow (?:many|long)\b", q):
        required.append("quantity")
    return tuple(required)


def _has_value(kind: str, sentence: str, question: str) -> bool:
    if kind != "quantity":
        return bool({"percentage": _PERCENT, "money": _MONEY, "version": _VERSION}[kind].search(sentence))
    question_terms = _terms(question)
    units = question_terms & _DURATION_UNITS
    if "how long" in question.lower():
        units = units or _DURATION_UNITS
    for value in _SCALAR.finditer(sentence):
        following = " ".join(tokens(sentence[value.end():])[:3])
        if _terms(following) & (units or question_terms):
            return True
    return False


@dataclass(frozen=True)
class EvidencePassage:
    hit: Hit
    text: str


@dataclass(frozen=True)
class EvidenceSelection:
    passages: tuple[EvidencePassage, ...]
    reason: str
    required: tuple[str, ...] = ()


def select_evidence(question: str, hits: list[Hit], max_words: int) -> EvidenceSelection:
    passages = []
    remaining = max_words
    for hit in hits:
        if hit.score <= 0 or remaining <= 0:
            continue
        words = hit.chunk.text.split()[:remaining]
        if words:
            passages.append(EvidencePassage(hit, " ".join(words)))
            remaining -= len(words)
    if not passages:
        return EvidenceSelection((), "no_positive_context")

    required = required_values(question)
    if not required:
        return EvidenceSelection(tuple(passages), "lexical_context_only")
    anchors = _terms(question) - _DURATION_UNITS
    if not anchors:
        return EvidenceSelection((), "ambiguous_value_request", required)

    supported = set()
    selected = []
    for passage in passages:
        found = set()
        # Check only the text that will actually reach generation, after truncation.
        for sentence in re.split(r"(?<=[.!?])\s+", passage.text):
            if _UNAVAILABLE.search(sentence):
                continue
            if len(anchors & _terms(sentence)) / len(anchors) < MIN_SUBJECT_COVERAGE:
                continue
            found.update(kind for kind in required if _has_value(kind, sentence, question))
        if found:
            supported.update(found)
            selected.append(passage)
    if not set(required) <= supported:
        missing = ",".join(kind for kind in required if kind not in supported)
        return EvidenceSelection((), "missing_value_evidence:" + missing, required)
    return EvidenceSelection(tuple(selected), "value_evidence_present", required)
