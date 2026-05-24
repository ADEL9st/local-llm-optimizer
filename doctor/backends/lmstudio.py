from __future__ import annotations

from doctor.backends.openai_compatible import OpenAICompatibleBackend


class LMStudioBackend(OpenAICompatibleBackend):
    name = "lmstudio"
    default_base_url = "http://localhost:1234/v1"
