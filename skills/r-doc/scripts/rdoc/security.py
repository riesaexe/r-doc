from __future__ import annotations

import re


SAFE_EXAMPLE_VALUES = {
    "aws-access-key": frozenset({"AKIAIOSFODNN7EXAMPLE"}),
}

SECRET_PATTERNS = (
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"), "private-key-marker"),
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "aws-access-key"),
    (re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b"), "github-token"),
    (re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"), "github-token"),
    (re.compile(r"\bAIza[0-9A-Za-z_-]{20,}\b"), "google-api-key"),
    (re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b"), "slack-token"),
    (re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"), "jwt"),
    (re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b"), "openai-api-key"),
    (
        re.compile(
            r"\b(?:postgres(?:ql)?|mysql|mariadb|mongodb(?:\+srv)?|redis|amqp)://[^/\s:@]+:[^@\s]+@[^)\s]+"
        ),
        "database-connection-string",
    ),
    (
        re.compile(
            r"(?i)\b(?:password|passwd|pwd)\s*[:=]\s*['\"]?"
            r"(?!<|your\b|example\b|sample\b|dummy\b|redacted\b|changeme\b|"
            r"(?:你的|请输入|请填写|请替换|示例|样例|占位符)[^\s'\"]{0,16}(?:密码|口令)|"
            r"(?:待填写|待补充|待设置|未设置)|\*{3,})[^\s'\"]{8,}"
        ),
        "generic-password",
    ),
)
SECRET_CODES = frozenset(code for _, code in SECRET_PATTERNS)


def is_safe_example(code: str, value: str, allowlist: dict[str, tuple[str, ...]] | None = None) -> bool:
    built_in = SAFE_EXAMPLE_VALUES.get(code, ())
    configured = (allowlist or {}).get(code, ())
    return value in built_in or value in configured
