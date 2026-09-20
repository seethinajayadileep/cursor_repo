from __future__ import annotations

import os
import tempfile
from pathlib import Path

TMP = Path(tempfile.mkdtemp()) / "accounts.sqlite"
os.environ.setdefault("SESSION_SECRET", "test-secret-value-not-for-production")
os.environ.setdefault("AZURE_CLIENT_ID", "test-client-id")
os.environ.setdefault("AZURE_CLIENT_SECRET", "test-client-secret")
os.environ.setdefault("AZURE_TENANT_ID", "common")
os.environ.setdefault("REDIRECT_URI", "http://testserver/auth/callback")
os.environ["MAIL_DB_PATH"] = str(TMP)
