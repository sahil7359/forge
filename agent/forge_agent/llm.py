"""Ollama client + output contract (TechSpec §5).

TODO P4:
- chat(prompt_system, context_json) -> str via POST {OLLAMA_URL}/api/chat,
  options: temperature (0.6 nudge / 0.4 report), num_predict caps, timeout 90 s.
- NudgePayload(BaseModel): title: str (<=40), body: str (<=220) — validate LLM JSON;
  on failure retry once with a 'return ONLY valid JSON' reminder; then raise LLMFallback
  so the caller uses the deterministic template (never ship malformed output).
- Report path: plain markdown out, hard length cap, strip any HTML (defense before
  DOMPurify at render — Security.md §6).
"""
