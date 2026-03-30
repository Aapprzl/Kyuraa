from typing import Any


class PromptBuilder:
    def __init__(self):
        self._reference_keywords = {
            "01-nahwu": ["nahwu", "i'rab", "gramatikal", "sintaksis", "irab", "kalimat", "fi'il", "isim", "harakat", "nawasikh", "idhafah"],
            "02-sharaf": ["sharaf", "wazan", "morfologi", "imbuhan", "fi'il madhi", "fi'il mudhari", "mashdar", "isim fa'il", "isim maf'ul"],
            "03-balaghah": ["balaghah", "retorika", "qur'ani", "sastra arab", "uslub", "majaz", "kinayah"],
            "04-special-cases": ["bilangan", "angka", "idiom", "kasus khusus"],
            "05-akademik": ["akademik", "skripsi", "tesis", "jurnal", "abstrak"],
            "06-kolokasi": ["kolokasi", "verba", "kata kerja"],
        }

    def build_system_prompt(self, skill_loader) -> str:
        if skill_loader is None:
            return ""

        prompt = skill_loader.get_system_prompt()
        if not prompt:
            return ""

        parts = [prompt]

        name = skill_loader.get_name()
        if name:
            parts.insert(0, f"# Skill: {name}\n")

        return "\n\n".join(parts)

    def build_system_with_references(self, skill_loader, references: dict[str, str]) -> str:
        system = self.build_system_prompt(skill_loader)
        if not references:
            return system

        ref_parts = ["\n\n## Referensi Aktif:\n"]
        for ref_name, ref_content in references.items():
            ref_parts.append(f"\n### {ref_name}\n{ref_content}")

        return system + "".join(ref_parts)

    def build_messages(
        self,
        session_history: list[dict[str, str]],
        user_input: str
    ) -> list[dict[str, str]]:
        messages = []

        for msg in session_history:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            messages.append({"role": role, "content": content})

        messages.append({"role": "user", "content": user_input})

        return messages

    def inject_reference(
        self,
        prompt: str,
        ref_name: str,
        ref_content: str
    ) -> str:
        ref_section = f"\n\n## Reference: {ref_name}\n\n{ref_content}\n"
        return prompt + ref_section

    def detect_needed_references(self, user_input: str) -> list[str]:
        user_lower = user_input.lower()
        needed = ["05-akademik", "06-kolokasi"]

        for ref_name, keywords in self._reference_keywords.items():
            if ref_name in needed:
                continue
            if any(kw in user_lower for kw in keywords):
                needed.append(ref_name)

        return needed

    def estimate_tokens(self, text: str) -> int:
        return len(text) // 4

    def estimate_tokens_messages(self, messages: list[dict[str, str]]) -> int:
        return sum(self.estimate_tokens(msg.get("content", "")) for msg in messages)
