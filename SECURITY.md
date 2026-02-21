<!-- filepath: SECURITY.md -->

# Security Policy

AdManager takes security seriously. We appreciate your efforts to responsibly disclose your findings.

## 📋 Table of Contents

- [Supported Versions](#supported-versions)
- [Reporting a Vulnerability](#reporting-a-vulnerability)
- [Security Best Practices](#security-best-practices)
- [Known Security Considerations](#known-security-considerations)

---

## Supported Versions

We provide security updates for the following versions:

| Version | Supported          | Notes                          |
| ------- | ------------------ | ------------------------------ |
| 0.2.x   | ✅ **Supported**   | Current stable version         |
| 0.1.x   | ⚠️ **Legacy**      | Security updates until Q2 2026 |
| < 0.1   | ❌ **Unsupported** | End of life                    |

**Recommendation:** Always use the latest version from the `main` branch for production deployments.

---

## Reporting a Vulnerability

We encourage responsible disclosure of security vulnerabilities. Please follow one of these methods:

### Option 1: GitHub Private Vulnerability Reporting (Recommended)

1. Go to the [Security tab](https://github.com/GloryWater/backend-for-using-ai/security)
2. Click **"Report a vulnerability"**
3. Fill out the form with details about the vulnerability
4. We will respond within **72 hours**

### Option 2: Email

Send an email to **security@example.com** with:

- **Subject:** `[Security] Vulnerability Report - [Brief Description]`
- **Description:** Detailed description of the vulnerability
- **Impact:** Potential impact on users/system
- **Reproduction:** Steps to reproduce the issue
- **Suggested Fix:** (Optional) Your recommendations

### What to Expect

- **Initial Response:** Within 72 hours
- **Status Update:** Within 7 days (acknowledgment or request for more info)
- **Resolution Timeline:** Depends on severity (typically 14-30 days)
- **Disclosure:** Coordinated disclosure after fix is released

### What We Ask

- **Do not** disclose the vulnerability publicly before we've had a chance to fix it
- **Do not** exploit the vulnerability beyond what's necessary to demonstrate it
- **Do** provide clear reproduction steps
- **Do** be available for follow-up questions

---

## Security Best Practices

### For Developers

#### Environment Variables

- ✅ **Use strong passwords** for database credentials (minimum 16 characters)
- ✅ **Never commit `.env` files** to version control
- ✅ **Rotate API keys** regularly (every 90 days recommended)
- ✅ **Use separate credentials** for development and production

```bash
# ❌ Bad: Weak password
DB_PASS=password123

# ✅ Good: Strong password
DB_PASS=Xk9#mP2$vL5@nQ8wR3
```

#### Database Security

- ✅ **Restrict PostgreSQL access** to internal network only
- ✅ **Use SSH tunnels** for remote database access
- ✅ **Enable SSL** for database connections in production
- ✅ **Regular backups** with encryption

```yaml
# docker-compose.yaml
services:
  db:
    ports:
      - "127.0.0.1:5432:5432"  # ✅ Localhost only
    # ports:
    #   - "5432:5432"  # ❌ Exposed to all interfaces
```

#### API Security

- ✅ **Rate limiting** enabled on sensitive endpoints (`/auth`, `/edit`)
- ✅ **HMAC signature verification** for payment webhooks
- ✅ **Input validation** via Pydantic schemas
- ✅ **HTTPS only** in production (use reverse proxy like nginx)

```python
# Rate limiting example
from src.middleware import RateLimitMiddleware

app.add_middleware(
    RateLimitMiddleware,
    limiter=create_rate_limiter(
        default_requests=100,
        default_window_seconds=60,
    ),
)
```

### For System Administrators

#### Docker Security

- ✅ **Run containers as non-root** user
- ✅ **Use read-only root filesystem** where possible
- ✅ **Regular image updates** via Watchtower
- ✅ **Network isolation** (internal Docker networks)

```yaml
# docker-compose.yaml
services:
  backend:
    read_only: true
    tmpfs:
      - /tmp
    security_opt:
      - no-new-privileges:true
```

#### Monitoring

- ✅ **Enable health checks** for all services
- ✅ **Monitor logs** for suspicious activity
- ✅ **Set up alerts** for failed authentication attempts
- ✅ **Regular security audits** (quarterly recommended)

```bash
# Monitor failed auth attempts
docker-compose logs backend | grep "401 Unauthorized"

# Check for rate limit violations
docker-compose logs backend | grep "429 Too Many Requests"
```

---

## Known Security Considerations

### Current Limitations

#### ⚠️ XOR Encryption (Low Security)

The Lua script encryption uses XOR cipher, which is **not cryptographically secure**.

**Impact:**
- Scripts can be decrypted with sufficient effort
- Not suitable for protecting sensitive intellectual property

**Mitigation:**
- Scripts are obfuscated, not encrypted
- HWID binding prevents unauthorized distribution
- Legal protection via proprietary license

**Planned Improvement:**
- Migration to AES-GCM encryption (Q2 2026)
- Integration with libsodium for key derivation

#### ⚠️ In-Memory Rate Limiting

Rate limiting uses in-memory storage, which doesn't persist across restarts.

**Impact:**
- Rate limits reset on application restart
- Not effective in clustered deployments

**Mitigation:**
- Use single-instance deployment
- Implement Redis-based rate limiting (planned)

**Planned Improvement:**
- Redis-backed rate limiting (Q3 2026)
- Distributed rate limiting for multi-instance deployments

#### ⚠️ No Brute Force Protection on /auth

The `/auth` endpoint has rate limiting but no account lockout.

**Impact:**
- Attackers can attempt multiple license keys
- Limited by rate limiting (10 requests/minute)

**Mitigation:**
- Rate limiting: 10 requests/minute, 15-minute block
- Monitoring for suspicious patterns

**Planned Improvement:**
- Exponential backoff for repeated failures
- IP-based blocking for suspicious patterns

### Security Roadmap

| Quarter | Improvement | Priority |
|---------|-------------|----------|
| Q2 2026 | AES-GCM encryption for Lua scripts | 🔴 High |
| Q2 2026 | HTTPS redirect in production | 🔴 High |
| Q3 2026 | Redis-based rate limiting | 🟡 Medium |
| Q3 2026 | Audit logging for user actions | 🟡 Medium |
| Q4 2026 | Account lockout after failed attempts | 🟡 Medium |
| Q4 2026 | Security headers (CSP, HSTS, etc.) | 🟢 Low |

---

## Security Checklist for Production

Before deploying to production, ensure:

- [ ] **Strong passwords** for all credentials
- [ ] **HTTPS enabled** (reverse proxy with SSL certificate)
- [ ] **Database not exposed** to public internet
- [ ] **Rate limiting** enabled and configured
- [ ] **Webhook signatures** verified (Tribute, CryptoCloud)
- [ ] **Regular backups** configured (daily recommended)
- [ ] **Monitoring and alerting** set up
- [ ] **Latest version** deployed
- [ ] **Firewall rules** configured (allow only necessary ports)
- [ ] **`.env` file** secured (permissions: `600` or `640`)

```bash
# Secure .env file permissions
chmod 600 .env
chown root:root .env

# Verify permissions
ls -la .env
# Expected: -rw------- 1 root root ...
```

---

## Contact

For security-related questions:

- **GitHub:** [Report a vulnerability](https://github.com/GloryWater/backend-for-using-ai/security)
- **Email:** security@example.com
- **Telegram:** @your_support_bot

---

**Thank you for helping keep AdManager secure!** 🔒
