# Security

- Passwords hashed with bcrypt
- JWT sessions
- Helmet + CORS
- Multer file type/size limits
- contextIsolation Electron preload bridge
- No secrets in frontend bundles
- `.env.example` only — never commit `.env`
- XSS-conscious React rendering; code blocks not executed
- Uploaded documents never executed
- Privacy center for delete session/document/account/clear local data
