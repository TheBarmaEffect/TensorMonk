# Security Policy

## Reporting Vulnerabilities

If you discover a security vulnerability, please report it responsibly:

1. **Do not** open a public GitHub issue
2. Email the maintainers directly
3. Include a description of the vulnerability and steps to reproduce

## Security Measures

- XSS pattern detection in security middleware
- Content Security Policy (CSP) headers with strict directives
- HSTS headers for transport security
- Rate limiting per IP to prevent abuse
- Input validation on all API request models
- No secrets committed to repository (env vars only)
