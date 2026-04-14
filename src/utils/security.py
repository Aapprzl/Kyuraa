import os
import base64
from pathlib import Path
from cryptography.fernet import Fernet
from typing import Any
import json
import uuid

from src.utils.logger import log

SECRET_DIR = Path("workspace")
MASTER_KEY_FILE = SECRET_DIR / ".kyuraa-secret"

class SecurityManager:
    _fernet: Fernet = None
    _gateway_token: str = None

    @classmethod
    def initialize(cls):
        """Siapkan kunci master dan gateway token."""
        SECRET_DIR.mkdir(parents=True, exist_ok=True)
        
        # 1. Handle Master Key (Fernet)
        if not MASTER_KEY_FILE.exists():
            key = Fernet.generate_key()
            MASTER_KEY_FILE.write_bytes(key)
            log("security", "New Master Key generated and saved.")
        else:
            key = MASTER_KEY_FILE.read_bytes()
        
        cls._fernet = Fernet(key)

        # 2. Handle Gateway Token (Auth)
        cls._gateway_token = os.environ.get("GATEWAY_TOKEN")
        
        if not cls._gateway_token:
            cls._gateway_token = str(uuid.uuid4().hex[:16])
            # Mask token in logs for security
            masked = cls._gateway_token[:4] + "********" 
            log("security", f"New Gateway Token generated: {masked}")
            
        os.environ["GATEWAY_TOKEN"] = cls._gateway_token

    @classmethod
    def encrypt(cls, text: str) -> str:
        if not cls._fernet:
            cls.initialize()
        return cls._fernet.encrypt(text.encode()).decode()

    @classmethod
    def decrypt(cls, token: str) -> str:
        if not cls._fernet:
            cls.initialize()
        try:
            return cls._fernet.decrypt(token.encode()).decode()
        except Exception as e:
            log("error", f"Decryption failed: {e}")
            return ""

    @classmethod
    def encrypt_dict(cls, data: dict) -> dict:
        """Enkripsi nilai-nilai sensitif dalam dict (API Keys)."""
        encrypted = data.copy()
        for key in ["OPENROUTER_API_KEY", "GOOGLE_API_KEY"]:
            if key in encrypted and encrypted[key] and not encrypted[key].startswith("enc:"):
                raw_val = encrypted[key]
                encrypted[key] = f"enc:{cls.encrypt(raw_val)}"
        return encrypted

    @classmethod
    def decrypt_dict(cls, data: dict) -> dict:
        """Dekripsi nilai-nilai sensitif dalam dict (API Keys)."""
        decrypted = data.copy()
        for key in ["OPENROUTER_API_KEY", "GOOGLE_API_KEY"]:
            if key in decrypted and isinstance(decrypted[key], str) and decrypted[key].startswith("enc:"):
                token = decrypted[key].replace("enc:", "")
                decrypted[key] = cls.decrypt(token)
        return decrypted

    @classmethod
    def get_gateway_token(cls) -> str:
        if not cls._gateway_token:
            cls.initialize()
        return cls._gateway_token
