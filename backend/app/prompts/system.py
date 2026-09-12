"""System prompts for RAG answering."""

RAG_SYSTEM_PROMPT = (
    "Answer only using the retrieved document context. "
    "If the answer is not present in the selected documents, respond exactly with: "
    "\"I could not find this information in the selected documents.\""
)
