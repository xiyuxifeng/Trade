from __future__ import annotations

import hashlib
import secrets


def hash_password(password: str) -> str:
    """对密码进行加盐哈希，返回格式为 salt$hash 的字符串。"""
    salt = secrets.token_hex(16)
    pwd_hash = hashlib.sha256((salt + password).encode("utf-8")).hexdigest()
    return f"{salt}${pwd_hash}"


def verify_password(password: str, hashed: str) -> bool:
    """验证密码是否与哈希值匹配。"""
    try:
        salt, pwd_hash = hashed.split("$", 1)
        computed = hashlib.sha256((salt + password).encode("utf-8")).hexdigest()
        return computed == pwd_hash
    except (ValueError, AttributeError):
        return False
