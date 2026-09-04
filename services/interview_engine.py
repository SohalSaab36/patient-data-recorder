import json
import os

_FLOW_CACHE = None
_FLAGS_CACHE = None


def _read(name):
    base = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", name)
    with open(base, encoding="utf-8") as handle:
        return json.load(handle)


def get_flow():
    global _FLOW_CACHE
    if _FLOW_CACHE is None:
        _FLOW_CACHE = _read("interview_flows.json")
    return _FLOW_CACHE


def get_red_flags():
    global _FLAGS_CACHE
    if _FLAGS_CACHE is None:
        _FLAGS_CACHE = _read("red_flags.json")
    return _FLAGS_CACHE


def pick_text(block, lang, simple=False, simple_block=None):
    lang = lang if lang in ("en", "hi") else "en"
    if simple and simple_block:
        return simple_block.get(lang) or simple_block.get("en") or ""
    if not block:
        return ""
    return block.get(lang) or block.get("en") or ""


def get_question(question_id):
    return get_flow()["questions"].get(question_id)


def localize_question(question, lang, simple=False):
    if not question:
        return None
    return {
        "type": question.get("type", "text"),
        "section": question.get("section", "general"),
        "text": pick_text(question.get("text"), lang, simple, question.get("simple")),
        "help": pick_text(question.get("simple") or {}, lang) if simple else "",
        "choices": [
            {
                "value": c["value"],
                "label": pick_text(c.get("label"), lang),
            }
            for c in question.get("choices", [])
        ],
    }


def resolve_next(question, answer_value):
    if not question:
        return "END"
    if question.get("next_map"):
        return question["next_map"].get(answer_value) or question["next_map"].get("_default") or "END"
    for rule in question.get("next_rules") or []:
        if "if_equals" in rule and answer_value == rule["if_equals"]:
            return rule["goto"]
        if "if_contains" in rule:
            text = (answer_value or "").lower()
            if any(token.lower() in text for token in rule["if_contains"]):
                return rule["goto"]
        if "else" in rule:
            return rule["else"]
    return question.get("next") or "END"


def progress_for(question_id):
    flow = get_flow()
    keys = list(flow["questions"].keys())
    if question_id not in keys:
        return 100
    idx = keys.index(question_id)
    return min(99, int((idx / max(len(keys), 1)) * 100))


def scan_red_flags(*texts):
    blob = " ".join(t or "" for t in texts).lower()
    hits = []
    for item in get_red_flags().get("flags", []):
        for phrase in item.get("phrases", []):
            if phrase.lower() in blob:
                hits.append(
                    {
                        "id": item["id"],
                        "phrase": phrase,
                        "message": item["message"],
                    }
                )
                break
    return hits
