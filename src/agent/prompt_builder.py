

from typing import Any


class PromptBuilder:
    def __init__(self):
        pass

    def build_system_prompt(self, skill_manager, tool_registry=None) -> str:
        BASE_PROMPT = """Kamu adalah asisten AI pribadi yang
cerdas dan bisa diajak ngobrol. Kamu memiliki beberapa
skill khusus dan tools yang bisa digunakan sesuai kebutuhan.

ATURAN DASAR:
- Jika user menyapa atau mengobrol biasa -> jawab natural
- Skill hanya bisa diaktifkan/dinonaktifkan oleh user secara manual via UI Settings, jangan mencoba mengaktifkannya via chat.
- Jika ada skill aktif, patuhi instruksi skill tersebut secara ketat.

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
            active_info = f"\n\n[STATUS SKILL: Skill '{skill_manager.active_skill}' saat ini SEDANG AKTIF]\n\n"
            return full_prompt + active_info + skill_prompt
        else:
            active_info = "\n\n[STATUS SKILL: Saat ini TIDAK ADA skill yang aktif. Mode Asisten Normal]\n\n"
            return full_prompt + active_info + skills_list

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
        session_history: list[dict[str, Any]],
        user_input: str,
        current_metadata: dict | None = None
    ) -> list[dict[str, str]]:
        messages = []

        for msg in session_history:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            metadata = msg.get("metadata")

            # Jika ada metadata file, format kontennya
            if metadata and isinstance(metadata, dict) and metadata.get("filename"):
                filename = metadata.get("filename", "file-unknown")
                script = metadata.get("script", "unknown")
                file_text = metadata.get("text", "")
                
                if file_text.strip():
                    content = f"""[CONTEXT - File: {filename}]
Script: {script}
--- FILE CONTENT START ---
{file_text}
--- FILE CONTENT END ---

[USER MESSAGE]: {content}"""
                else:
                    content = f"""[CONTEXT - File: {filename}]
[SISTEM INFO: File PDF ini adalah hasil scan/gambar gambar biner. Teks tidak bisa diekstrak. 
INSTRUKSI WAJIB: Beritahu user secara langsung bahwa Anda tidak dapat membaca PDF hasil scan/gambar. Dilarang menggunakan tool apapun untuk mencoba mencari atau membaca file ini.]

[USER MESSAGE]: {content}"""

            messages.append({"role": role, "content": content})

        # Tambahkan input terbaru
        final_input = user_input
        if current_metadata and isinstance(current_metadata, dict) and current_metadata.get("filename"):
            filename = current_metadata.get("filename", "file-unknown")
            script = current_metadata.get("script", "unknown")
            file_text = current_metadata.get("text", "")
            
            if file_text.strip():
                final_input = f"""[CONTEXT - File: {filename}]
Script: {script}
--- FILE CONTENT START ---
{file_text}
--- FILE CONTENT END ---

[USER MESSAGE]: {user_input}"""
            else:
                final_input = f"""[CONTEXT - File: {filename}]
[SISTEM INFO: File PDF ini adalah hasil scan/gambar biner. Teks tidak bisa diekstrak. 
INSTRUKSI WAJIB: Beritahu user secara langsung bahwa Anda tidak dapat membaca PDF hasil scan/gambar. Dilarang menggunakan tool apapun untuk mencoba mencari atau membaca file ini.]

[USER MESSAGE]: {user_input}"""

        messages.append({"role": "user", "content": final_input})

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
