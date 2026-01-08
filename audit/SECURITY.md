# Security Policy

## Supported Versions

Use this section to tell people about which versions of your project are
currently being supported with security updates.

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

We take the security of OSS Audit seriously. If you believe you have found a security vulnerability, please report it to us as described below.

### Reporting Process

1. **Do not create a public GitHub issue** for the vulnerability
2. **Email us** at [security@oss-audit.org](mailto:security@oss-audit.org) with:
   - A description of the vulnerability
   - Steps to reproduce the issue
   - Potential impact assessment
   - Any suggested fixes (if available)

### What to Expect

- We will acknowledge receipt of your report within 48 hours
- We will investigate and provide updates on our progress
- We will work with you to understand and address the issue
- We will coordinate the disclosure and release of any fixes

### Responsible Disclosure

We follow responsible disclosure practices:
- We will not publicly disclose the vulnerability until a fix is available
- We will credit you in our security advisories (unless you prefer to remain anonymous)
- We will work with you to ensure the fix addresses the root cause

### Security Best Practices

When using OSS Audit:

1. **Keep dependencies updated**: Regularly update your Python packages
2. **Use secure connections**: Always use HTTPS when downloading packages
3. **Review audit results**: Carefully review the security assessment results
4. **Validate inputs**: Ensure project paths are from trusted sources
5. **Monitor for updates**: Watch for security updates to the tool

### Security Features

OSS Audit includes several security features:

- **Input validation**: All project paths are validated before processing
- **Safe file operations**: Uses read-only access to project files
- **No data collection**: Does not collect or transmit project data
- **Local processing**: All analysis is performed locally

### Known Limitations

- The tool analyzes project structure and files but does not execute project code
- Security assessments are based on static analysis and may not catch all issues
- Results should be used as guidance, not as the sole security measure

## Security Updates

Security updates will be released as patch versions (e.g., 1.0.1, 1.0.2) and will be clearly marked in the changelog.

For questions about this security policy, please contact us at [security@oss-audit.org](mailto:security@oss-audit.org).
