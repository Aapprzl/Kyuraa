import pytest
from fastapi.testclient import TestClient
from pathlib import Path
import os

from src.gateway.server import GatewayServer
from src.utils.security import SecurityManager

class TestSecurityBoundaries:
    @classmethod
    def setup_class(cls):
        # Set test mode to avoid single instance checks and use test locks
        os.environ["KYURAA_TEST_MODE"] = "1"
        SecurityManager.initialize()
        cls.server = GatewayServer()
        cls.client = TestClient(cls.server._app)
        cls.token = SecurityManager.get_gateway_token()

    def test_unauthorized_access_to_info_endpoint(self):
        # Note: /info is public in current implementation, let's test a protected one
        response = self.client.get("/stats")
        assert response.status_code == 401
        assert "Akses dilarang" in response.json()["detail"]

    def test_authorized_access_with_header(self):
        response = self.client.get("/stats", headers={"X-API-Key": self.token})
        assert response.status_code == 200

    def test_authorized_access_with_query_param(self):
        response = self.client.get(f"/stats?token={self.token}")
        assert response.status_code == 200

    def test_path_traversal_prevention_in_registry(self):
        from src.tools.registry import registry
        
        # Attempt to read a file outside workspace
        # Assuming .env exists in project root
        secret_file = "../../.env" 
        result = registry.execute("read_file", path=secret_file)
        
        assert result["success"] is False
        assert "tidak diizinkan" in result["error"]

    def test_pdf_upload_security_size_limit(self):
        # Create a large dummy content (over 5MB) starting with %PDF magic bytes
        large_content = b"%PDF" + b"a" * (6 * 1024 * 1024)
        files = {"file": ("test.pdf", large_content, "application/pdf")}
        
        response = self.client.post(
            "/upload", 
            headers={"X-API-Key": self.token},
            files=files
        )
        
        assert response.status_code == 400
        assert "File terlalu besar" in response.json()["detail"]

    def test_pdf_upload_security_type_check(self):
        files = {"file": ("test.txt", b"not a pdf", "text/plain")}
        
        response = self.client.post(
            "/upload", 
            headers={"X-API-Key": self.token},
            files=files
        )
        
        assert response.status_code == 400
        assert "Hanya file PDF" in response.json()["detail"]
