# Security Policy

## Supported Versions

We release patches for security vulnerabilities in the following versions:

| Version | Supported          |
| ------- | ------------------ |
| 1.1.x   | :white_check_mark: |
| 1.0.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

We take the security of OCRBridge seriously. If you believe you have found a security vulnerability, please report it to us as described below.

### Where to Report

**Please do NOT report security vulnerabilities through public GitHub issues.**

Instead, please report them via:

- **Email**: 24376955+datenzar@users.noreply.github.com
- **GitHub Security Advisories**: Use the "Security" tab in this repository to privately report vulnerabilities

### What to Include

Please include the following information in your report:

- Type of vulnerability (e.g., remote code execution, SQL injection, cross-site scripting)
- Full paths of source file(s) related to the vulnerability
- Location of the affected source code (tag/branch/commit or direct URL)
- Step-by-step instructions to reproduce the issue
- Proof-of-concept or exploit code (if possible)
- Impact of the vulnerability, including how an attacker might exploit it

### Response Timeline

- **Initial Response**: Within 48 hours of receiving your report
- **Status Update**: Within 7 days with our evaluation and expected resolution timeline
- **Resolution**: We aim to resolve critical vulnerabilities within 30 days

### Disclosure Policy

- We request that you give us reasonable time to address the vulnerability before public disclosure
- We will credit you in the security advisory unless you prefer to remain anonymous
- Once a fix is released, we will publish a security advisory detailing the vulnerability and the fix

## Security Considerations

### File Upload Security

This API processes user-uploaded files. Please be aware of the following security measures and best practices:

#### Built-in Protections

- **File Size Limits**: Maximum 25MB upload size (configurable via `MAX_UPLOAD_SIZE_MB`)
- **File Type Validation**: Only JPEG, PNG, PDF, and TIFF files are accepted
- **MIME Type Checking**: Server validates file content, not just extension
- **Filename Sanitization**: Uploaded filenames are sanitized to prevent path traversal attacks
- **Rate Limiting**: 100 requests per minute per IP address (configurable)
- **Auto Cleanup**: Temporary files and results are automatically deleted after 48 hours
- **No Code Execution**: OCR processing uses sandboxed libraries (Tesseract, EasyOCR)

#### Additional Recommendations for Production

1. **Network Security**
   - Deploy behind a reverse proxy (nginx, Traefik) with TLS/HTTPS
   - Use a Web Application Firewall (WAF) to filter malicious requests
   - Implement IP allowlisting if serving internal users only

2. **File Processing**
   - Consider running OCR processing in isolated containers or sandboxes
   - Scan uploaded files with antivirus/malware detection (ClamAV, VirusTotal API)
   - Monitor for suspicious file patterns (polyglot files, unusual metadata)

3. **Resource Protection**
   - Set CPU and memory limits for OCR processing containers
   - Implement request timeouts to prevent resource exhaustion
   - Use Redis authentication (`requirepass`) in production
   - Enable Redis persistence and backup for job state recovery

4. **Monitoring & Logging**
   - Monitor for unusual upload patterns (high frequency, large files)
   - Log all file uploads with user IP, timestamp, and file hash
   - Set up alerts for rate limit violations
   - Review Prometheus metrics regularly for anomalies

5. **Data Privacy**
   - Uploaded files may contain sensitive information (PII, confidential documents)
   - Ensure compliance with GDPR, HIPAA, or other relevant regulations
   - Consider end-to-end encryption for file transfers
   - Document data retention policies (default: 48 hours auto-deletion)

### Known Limitations

- **PDF Processing**: Uses `poppler` via `pdf2image` - keep poppler updated for security patches
- **Image Processing**: Uses `Pillow` - known vulnerabilities in older versions, keep dependencies updated
- **PyTorch**: EasyOCR depends on PyTorch - monitor for security advisories
- **Docker Container**: Running as root by default - consider implementing non-root user

### Dependency Security

We use the following tools to maintain dependency security:

- **Dependabot**: Automated dependency updates (configure in `.github/dependabot.yml`)
- **UV Lock File**: `uv.lock` ensures reproducible builds with known-good dependency versions
- **Pre-commit Hooks**: Automated checks before commits (security linters can be added)

### Reporting False Positives

If you believe a security advisory or automated scan has incorrectly flagged an issue, please report it through the same channels as vulnerability reports.

## Security Updates

Subscribe to security updates:

- Watch this repository for security advisories
- Check the [CHANGELOG](CHANGELOG.md) for security-related updates
- Follow our releases for security patches

## Acknowledgments

We thank the following individuals for responsibly disclosing security vulnerabilities:

<!-- Add security researchers who have reported vulnerabilities -->
- None yet - you could be first!

---

**Last Updated**: 2024-11-22
