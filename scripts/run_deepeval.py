"""Optional DeepEval entrypoint. It intentionally does not manufacture scores without configured LLM credentials."""
import os
if not os.getenv('OPENROUTER_API_KEY') and not os.getenv('OPENAI_API_KEY'):
    raise SystemExit('Set OPENROUTER_API_KEY or OPENAI_API_KEY before running LLM-backed DeepEval.')
raise SystemExit('Configure your DeepEval model adapter and representative evaluation dataset before measuring metrics.')
