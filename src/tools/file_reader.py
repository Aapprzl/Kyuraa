from pathlib import Path
from typing import Any


class FileReader:
    """
    Reads large files chunk by chunk from top to bottom.
    Implements human-like reading behavior with paragraph awareness.
    """
    
    DELIMITERS = [
        '\n\n',
        '\n',
    ]
    
    def __init__(self, max_chars: int = 6000):
        self._max_chars = max_chars
        self._file_cache: dict[str, list[dict]] = {}
    
    def read_file(self, filepath: str) -> dict[str, Any]:
        """Read entire file and return chunks info"""
        path = Path(filepath)
        
        if not path.exists():
            raise FileNotFoundError(f"File tidak ditemukan: {filepath}")
        
        content = path.read_text(encoding="utf-8")
        chunks = self._split_into_chunks(content)
        
        self._file_cache[filepath] = chunks
        
        return {
            "total_chars": len(content),
            "total_chunks": len(chunks),
            "chunks": [
                {
                    "index": i,
                    "title": c["title"],
                    "chars": len(c["content"])
                }
                for i, c in enumerate(chunks)
            ]
        }
    
    def get_chunk(self, filepath: str, chunk_index: int) -> dict[str, Any]:
        """Get specific chunk by index"""
        if filepath not in self._file_cache:
            self.read_file(filepath)
        
        chunks = self._file_cache[filepath]
        
        if chunk_index < 0 or chunk_index >= len(chunks):
            return {
                "chunk_index": chunk_index,
                "chunk_content": "",
                "has_next": False,
                "is_complete": True,
                "message": f"Chunk {chunk_index + 1} tidak ditemukan. File hanya memiliki {len(chunks)} chunk."
            }
        
        chunk = chunks[chunk_index]
        is_last = chunk_index == len(chunks) - 1
        
        return {
            "chunk_index": chunk_index,
            "chunk_total": len(chunks),
            "chunk_title": chunk["title"],
            "chunk_content": chunk["content"],
            "chunk_chars": len(chunk["content"]),
            "has_next": not is_last,
            "is_complete": is_last,
            "progress_percent": int((chunk_index + 1) / len(chunks) * 100)
        }
    
    def get_file_info(self, filepath: str) -> dict[str, Any]:
        """Get file metadata without caching content"""
        path = Path(filepath)
        
        if not path.exists():
            raise FileNotFoundError(f"File tidak ditemukan: {filepath}")
        
        content = path.read_text(encoding="utf-8")
        chunks = self._split_into_chunks(content)
        
        return {
            "filename": path.name,
            "total_chars": len(content),
            "total_chunks": len(chunks),
            "chunks": [
                {
                    "index": i,
                    "title": c["title"],
                    "chars": len(c["content"])
                }
                for i, c in enumerate(chunks)
            ]
        }
    
    def _split_into_chunks(self, content: str) -> list[dict]:
        """Split content into chunks by paragraphs/lines"""
        chunks = []
        
        for delim in self.DELIMITERS:
            if delim in content:
                parts = content.split(delim)
                if len(parts) > 2:
                    current_chunk = ""
                    current_lines = []
                    
                    for part in parts:
                        part_text = part + delim
                        
                        if len(current_chunk) + len(part_text) <= self._max_chars:
                            current_chunk += part_text
                            current_lines.append(part.strip())
                        else:
                            if current_chunk.strip():
                                chunks.append({
                                    "content": current_chunk.strip(),
                                    "title": self._extract_title(current_lines)
                                })
                            
                            if len(part) <= self._max_chars:
                                current_chunk = part_text
                                current_lines = [part.strip()]
                            else:
                                sub_chunks = self._split_long_text(part, self._max_chars)
                                for i, sc in enumerate(sub_chunks[:-1]):
                                    chunks.append({
                                        "content": sc.strip(),
                                        "title": self._extract_title([sc.strip()])
                                    })
                                current_chunk = sub_chunks[-1] + delim if sub_chunks else ""
                                current_lines = [sub_chunks[-1].strip()] if sub_chunks else []
                    
                    if current_chunk.strip():
                        chunks.append({
                            "content": current_chunk.strip(),
                            "title": self._extract_title(current_lines)
                        })
                    
                    break
            
            if chunks:
                break
        else:
            chunks = self._fixed_split(content)
        
        return self._ensure_chunks(chunks)
    
    def _fixed_split(self, content: str) -> list[dict]:
        """Fallback: fixed size chunking"""
        chunks = []
        for i in range(0, len(content), self._max_chars):
            chunk_text = content[i:i + self._max_chars]
            chunks.append({
                "content": chunk_text.strip(),
                "title": self._extract_title(chunk_text.split('\n'))
            })
        return chunks
    
    def _split_long_text(self, text: str, max_size: int) -> list[str]:
        """Split long text by sentences/words"""
        if len(text) <= max_size:
            return [text]
        
        parts = []
        current = ""
        
        sentences = text.replace('!', '.').replace('?', '.').split('.')
        
        for sentence in sentences:
            sentence = sentence.strip() + '.'
            
            if len(current) + len(sentence) <= max_size:
                current += sentence + "\n"
            else:
                if current.strip():
                    parts.append(current.strip())
                current = sentence + "\n"
        
        if current.strip():
            parts.append(current.strip())
        
        return parts if parts else [text]
    
    def _extract_title(self, lines: list[str]) -> str:
        """Extract first meaningful line as chunk title"""
        for line in lines[:5]:
            line = line.strip()
            if line and len(line) > 3:
                clean = line.replace('#', '').replace('*', '').strip()
                if len(clean) > 60:
                    return clean[:57] + "..."
                return clean
        return "Bagian"
    
    def _ensure_chunks(self, chunks: list[dict]) -> list[dict]:
        """Merge tiny chunks and ensure reasonable size"""
        if not chunks:
            return [{"content": "", "title": "File kosong"}]
        
        merged = []
        buffer = {"content": "", "lines": []}
        
        for chunk in chunks:
            content = chunk["content"]
            
            if len(buffer["content"]) + len(content) <= self._max_chars:
                buffer["content"] += "\n\n" + content
                buffer["lines"].append(content)
            else:
                if buffer["content"].strip():
                    merged.append({
                        "content": buffer["content"].strip(),
                        "title": buffer["lines"][0][:60] if buffer["lines"] else "Bagian"
                    })
                
                if len(content) <= self._max_chars:
                    buffer = {"content": content, "lines": [content]}
                else:
                    sub_chunks = self._split_long_text(content, self._max_chars)
                    for sc in sub_chunks[:-1]:
                        merged.append({
                            "content": sc.strip(),
                            "title": self._extract_title(sc.split('\n'))
                        })
                    buffer = {"content": sub_chunks[-1], "lines": [sub_chunks[-1]]}
        
        if buffer["content"].strip():
            merged.append({
                "content": buffer["content"].strip(),
                "title": buffer["lines"][0][:60] if buffer["lines"] else "Bagian"
            })
        
        for i, chunk in enumerate(merged):
            if not chunk["title"] or chunk["title"] == "Bagian":
                chunk["title"] = f"Bagian {i + 1}"
        
        return merged if merged else [{"content": "", "title": "File kosong"}]
    
    def clear_cache(self, filepath: str = None):
        """Clear file cache"""
        if filepath:
            self._file_cache.pop(filepath, None)
        else:
            self._file_cache.clear()
