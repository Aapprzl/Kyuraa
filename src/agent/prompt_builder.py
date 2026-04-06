

class PromptBuilder:
    def __init__(self):
        pass

    def build_system_prompt(self, skill_manager, tool_registry=None) -> str:
        BASE_PROMPT = """Kamu adalah asisten AI pribadi yang
cerdas dan bisa diajak ngobrol. Kamu memiliki beberapa
skill khusus dan tools yang bisa digunakan sesuai kebutuhan.

ATURAN DASAR:
- Jika user menyapa atau mengobrol biasa -> jawab natural
- Jika user menyebut nama skill atau minta aktifkan skill
  -> konfirmasi skill akan diaktifkan
- Jika ada skill aktif -> ikuti instruksi skill tersebut
- Jika tidak ada skill aktif -> jadilah asisten biasa

## CARA MENGGUNAKAN TOOL:
Jika kamu butuh data tambahan atau ingin melakukan aksi teknis, sisipkan tag berikut di dalam jawabanmu:
[TOOL: nama_tool] param1="nilai" param2="nilai"

Sistem akan otomatis mengeksekusi tool tersebut dan memberikan hasilnya kepadamu di giliran berikutnya.
"""
        
        tools_section = self._build_tools_section(tool_registry)
        skill_prompt = skill_manager.get_system_prompt()
        skills_list = skill_manager.get_skills_summary()

        full_prompt = BASE_PROMPT + tools_section
        
        if skill_manager.is_active():
            return full_prompt + "\n\n" + skill_prompt
        else:
            return full_prompt + "\n\n" + skills_list

    def _build_tools_section(self, tool_registry) -> str:
        if not tool_registry:
            return ""
            
        active_tools = [t for t in tool_registry.list_tools_detail() if t.get("enabled", True)]
        if not active_tools:
            return ""
            
        parts = ["\n## TOOLS YANG TERSEDIA:\n"]
        for t in active_tools:
            parts.append(f"- {t['name']}: {t['description']}")
            
        return "\n".join(parts) + "\n"

    def build_system_with_references(self, skill_manager, references: dict[str, str], tool_registry=None) -> str:
        system = self.build_system_prompt(skill_manager, tool_registry)
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

        GREETINGS = ["halo", "hai", "hi", "oke", "ok", "thanks",
                     "terima kasih", "lanjut", "skip", "ya", "tidak"]
        user_lower = user_input.lower().strip()
        is_greeting = user_lower in GREETINGS or len(user_input) < 20

        if not is_greeting:
            for ref in on_demand:
                if ref not in needed:
                    needed.append(ref)

        return needed

    def estimate_tokens(self, text: str) -> int:
        return len(text) // 4

    def estimate_tokens_messages(self, messages: list[dict[str, str]]) -> int:
        return sum(self.estimate_tokens(msg.get("content", "")) for msg in messages)
