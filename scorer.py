"""
Scorer module for AI201 Project 1
"""

def judge(question: str, expects: str, answer: str, results: list) -> bool:
    """
    Return True if the answer matches expectations, False otherwise.
    If expects contains commas, requires all parts to be present.
    """
    answer_lower = answer.strip().lower()
    terms = [t.strip().lower() for t in expects.split(",") if t.strip()]
    return all(term in answer_lower for term in terms)