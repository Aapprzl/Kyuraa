import os
import json
from pathlib import Path
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from src.utils.logger import log
from src.utils.security import SecurityManager

router = APIRouter()

class SettingsSchema(BaseModel):
    provider: str
    model: str
    api_key: str

@router.get("/info")
async def info():
    settings_path = Path("workspace/settings.json")
    model = ""
    active = ""

    if settings_path.exists():
        try:
            with open(settings_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                active = data.get("ACTIVE_PROVIDER", "google")
                if active == "google":
                    model = data.get("GOOGLE_MODEL", "")
                else:
                    model = data.get("OPENROUTER_MODEL") or data.get("AGENT_MODEL", "")
        except Exception:
            pass

    if not active:
        active = os.environ.get("ACTIVE_PROVIDER", "google")
    if not model:
        if active == "google":
            model = os.environ.get("GOOGLE_MODEL", "")
        else:
            model = os.environ.get("OPENROUTER_MODEL") or os.environ.get("AGENT_MODEL", "")

    return {
        "model": model or "Unknown",
        "provider": active,
        "version": "1.0.0"
    }

@router.get("/settings")
async def get_settings(request: Request):
    # Verify token
    cli_token = request.headers.get("X-API-Key") or request.query_params.get("token")
    srv_token = SecurityManager.get_gateway_token()
    if not cli_token or cli_token != srv_token:
        raise HTTPException(status_code=401, detail="❌ Akses dilarang: Token tidak valid.")

    or_model = os.environ.get("OPENROUTER_MODEL") or os.environ.get("AGENT_MODEL", "")
    or_key = os.environ.get("OPENROUTER_API_KEY", "")
    google_model = os.environ.get("GOOGLE_MODEL", "")
    google_key = os.environ.get("GOOGLE_API_KEY", "")
    active = os.environ.get("ACTIVE_PROVIDER", "google")

    def mask(key):
        return key[:6] + "********" if len(key) > 6 else "********" if key else ""

    return {
        "openrouter": {"model": or_model, "api_key": mask(or_key)},
        "google": {"model": google_model, "api_key": mask(google_key)},
        "active_provider": active
    }

@router.post("/settings/validate-and-save")
async def save_settings(settings: SettingsSchema, request: Request):
    # Verify token
    cli_token = request.headers.get("X-API-Key") or request.query_params.get("token")
    srv_token = SecurityManager.get_gateway_token()
    if not cli_token or cli_token != srv_token:
        raise HTTPException(status_code=401, detail="❌ Akses dilarang: Token tidak valid.")

    provider = settings.provider.lower()
    api_key = settings.api_key
    key_env = "OPENROUTER_API_KEY" if provider == "openrouter" else "GOOGLE_API_KEY"
    model_env = "OPENROUTER_MODEL" if provider == "openrouter" else "GOOGLE_MODEL"

    if "********" in api_key:
        api_key = os.environ.get(key_env, "")

    from src.agent.llm_client import LLMClient
    try:
        is_google = (provider == "google")
        base_url = "https://generativelanguage.googleapis.com/v1beta/openai/" if is_google else "https://openrouter.ai/api/v1"
        valid_model = settings.model
        if is_google:
            valid_model = valid_model.replace("google/", "").split(":")[0]

        test_client = LLMClient(api_key=api_key, model=valid_model)
        test_client._client.base_url = base_url
        test_client.chat(system="You are a validator.", messages=[{"role": "user", "content": "hi"}])
    except Exception as e:
        err_msg = str(e).lower()
        log("error", f"Validation failed for {provider}: {e}")
        if "api_key" in err_msg or "401" in err_msg or "unauthorized" in err_msg:
            raise HTTPException(status_code=400, detail=f"❌ API Key {provider} tidak valid.")
        elif "model" in err_msg or "404" in err_msg:
            raise HTTPException(status_code=400, detail=f"❌ Model {settings.model} tidak ditemukan di {provider}.")
        else:
            raise HTTPException(status_code=400, detail=f"❌ Kesalahan {provider}: {str(e)}")

    settings_path = Path("workspace/settings.json")
    current_settings = {}
    if settings_path.exists():
        try:
            with open(settings_path, "r", encoding="utf-8") as f:
                current_settings = json.load(f)
        except Exception:
            log("warn", "settings.json corrupt atau tidak bisa dibaca")

    if provider == "openrouter":
        current_settings["OPENROUTER_API_KEY"] = api_key
        current_settings["OPENROUTER_MODEL"] = settings.model
        current_settings["ACTIVE_PROVIDER"] = "openrouter"
    else:
        current_settings["GOOGLE_API_KEY"] = api_key
        current_settings["GOOGLE_MODEL"] = settings.model
        current_settings["ACTIVE_PROVIDER"] = "google"

    current_settings["AGENT_MODEL"] = settings.model
    encrypted_settings = SecurityManager.encrypt_dict(current_settings)
    with open(settings_path, "w", encoding="utf-8") as f:
        json.dump(encrypted_settings, f, indent=4)

    os.environ[key_env] = api_key
    os.environ[model_env] = settings.model
    os.environ["ACTIVE_PROVIDER"] = provider
    os.environ["AGENT_MODEL"] = settings.model

    log("gateway", f"Settings updated for {provider}")
    return {"status": "ok", "message": f"✅ Koneksi {provider} berhasil! Setting disimpan."}
