from .models import RetrievedChunk
from .citations import format_citation


def assemble_context(question: str, retrieved: list[RetrievedChunk]) -> str:
    evidence = []
    for index, item in enumerate(retrieved, 1):
        evidence.append(f"[{index}] {format_citation(item.chunk.metadata)}\n{item.chunk.text}")
    return ("Answer only from the supplied context. Do not invent information. If the answer is not present, say: "
            "I couldn't find that information in the provided documents. Include citations based on metadata.\n\n"
            f"Question:\n{question}\n\nContext:\n" + ("\n\n".join(evidence) or "(no relevant context)"))
