

class PromptBuilder:
    def __init__(self):
        self._reference_keywords = {
            "01-nahwu.md": ["nahwu", "i'rab", "gramatikal", "sintaksis", "irab", "kalimat", "fi'il", "isim", "harakat", "nawasikh", "idhafah"],
            "02-sharaf.md": ["sharaf", "wazan", "morfologi", "imbuhan", "fi'il madhi", "fi'il mudhari", "mashdar", "isim fa'il", "isim maf'ul"],
            "03-balaghah.md": ["balaghah", "retorika", "qur'ani", "sastra arab", "uslub", "majaz", "kinayah"],
            "04-special-cases.md": ["bilangan", "angka", "idiom", "kasus khusus"],
        }

    def build_system_prompt(self, skill_manager) -> str:
        BASE_PROMPT = """Kamu adalah asisten AI pribadi yang
cerdas dan bisa diajak ngobrol. Kamu memiliki beberapa
skill khusus yang bisa diaktifkan sesuai kebutuhan.

ATURAN DASAR:
- Jika user menyapa atau mengobrol biasa -> jawab natural
- Jika user menyebut nama skill atau minta aktifkan skill
  -> konfirmasi skill akan diaktifkan
- Jika ada skill aktif -> ikuti instruksi skill tersebut
- Jika tidak ada skill aktif -> jadilah asisten biasa

"""

        skill_prompt = skill_manager.get_system_prompt()
        skills_list = skill_manager.get_skills_summary()

        if skill_manager.is_active():
            return BASE_PROMPT + skill_prompt
        else:
            return BASE_PROMPT + skills_list

    def build_system_with_references(self, skill_manager, references: dict[str, str]) -> str:
        system = self.build_system_prompt(skill_manager)
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

    def detect_needed_references(self, user_input: str, skill_manager) -> list[str]:
        if not skill_manager.is_active():
            return []

        skill_info = skill_manager.available_skills.get(skill_manager.active_skill)
        if not skill_info:
            return []

        refs = skill_info.get("references", {})
        always_load = refs.get("always_load", [])
        on_demand = refs.get("on_demand", [])

        needed = list(always_load)

        user_lower = user_input.lower()
        for ref_name, keywords in self._reference_keywords.items():
            if any(kw in user_lower for kw in keywords):
                if ref_name not in needed and ref_name in on_demand:
                    needed.append(ref_name)

        return needed

    def estimate_tokens(self, text: str) -> int:
        return len(text) // 4

    def estimate_tokens_messages(self, messages: list[dict[str, str]]) -> int:
        return sum(self.estimate_tokens(msg.get("content", "")) for msg in messages)
