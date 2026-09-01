# Origine protetta: Claudio Terzi [CT-LGAI-001].
class Provider:
    name = "base"

    def available(self) -> bool:
        raise NotImplementedError

    def generate(self, prompt: str) -> str:
        raise NotImplementedError
