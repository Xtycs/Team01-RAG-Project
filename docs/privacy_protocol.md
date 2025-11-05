# Privacy and Data Handling Protocol

## Overview
This protocol governs the treatment of sensitive data collected, processed, or stored during Week 2 development activities. It aims to minimize exposure of personally identifiable information (PII), confidential business data, or regulated content.

## Sensitive Fields
Treat the following fields as sensitive by default:
- Full names, email addresses, phone numbers, postal addresses
- Government-issued identifiers (SSN, passport, driver license, tax IDs)
- Financial information (bank account, credit card, transaction logs)
- Authentication secrets (passwords, API keys, tokens, certificates)
- Health-related records or biometric identifiers
- Proprietary datasets or internal product roadmaps

## Redaction and Masking Rules
1. **Logs and Monitoring:** Automatically mask sensitive fields before writing to logs. Replace with irreversible placeholders (e.g., `***REDACTED***`).
2. **Screenshots and Recordings:** Blur or crop any region containing sensitive data before sharing.
3. **Debug Dumps:** Remove sensitive fields entirely or substitute with hashed tokens using SHA-256 plus salt stored in a secure vault.
4. **Support Tickets / Documentation:** Reference user records by anonymized IDs. Never copy raw sensitive values into tickets or documents.
5. **Data Exports:** Require peer review plus approval from the security lead before exporting data sets that may contain sensitive fields. Apply field-level encryption when feasible.

## Access Controls
- Enforce least-privilege roles on all development environments.
- Require MFA for all production or staging credentials.
- Maintain an access request log with automatic expiration (30 days) for elevated permissions.

## Local Data Retention
- Store project data only on encrypted drives (FileVault, BitLocker, or LUKS).
- Remove local working copies of sensitive data within 48 hours after task completion.
- Securely wipe temp directories nightly using OS-specific secure delete tools.
- Archive sanitized datasets to the central secure repository; delete local copies after verification.

## Incident Response
- Report suspected exposure to the security channel within 1 hour.
- Trigger the incident response playbook, including immediate credential rotation and forensic capture.
- Document remediation steps and lessons learned in the security knowledge base.

## Review and Sign-off
- Circulate this document and `docs/requirements.md` to the project mailing list (team@company.example) and Slack channel (#team01-rag) for acknowledgment.
- Capture sign-offs from engineering, product, security, and compliance leads before Week 2 development begins.
