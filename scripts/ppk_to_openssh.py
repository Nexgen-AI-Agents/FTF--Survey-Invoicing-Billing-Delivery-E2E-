"""Convert an unencrypted PuTTY .ppk (v2/v3, ssh-rsa) to an OpenSSH private key.

Used by the invoice_pipeline workflow to build an SSH key from the committed
Prod-Server-Key.ppk at runtime, so the pipeline can open an SSH tunnel to the FTF
RDS MySQL through the prod server (whose static IP is allowed through the RDS
security group). No external tools (puttygen/plink) required — only `cryptography`,
which is already a pipeline dependency.

Usage:
    python scripts/ppk_to_openssh.py <input.ppk> <output_key>
"""
import base64
import os
import sys

from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization


def _ssh_strings(buf: bytes) -> list[bytes]:
    out, i = [], 0
    while i < len(buf):
        ln = int.from_bytes(buf[i:i + 4], "big")
        i += 4
        out.append(buf[i:i + ln])
        i += ln
    return out


def convert(ppk_path: str, out_path: str) -> None:
    lines = open(ppk_path).read().splitlines()
    if "Encryption: none" not in lines[:3] and not any(
        l.strip() == "Encryption: none" for l in lines[:4]
    ):
        raise SystemExit("ppk_to_openssh: only unencrypted (Encryption: none) keys are supported")

    def block(tag: str) -> bytes:
        idx = next(k for k, l in enumerate(lines) if l.startswith(tag))
        n = int(lines[idx].split(":")[1])
        return base64.b64decode("".join(lines[idx + 1:idx + 1 + n]))

    pub = _ssh_strings(block("Public-Lines"))   # [b"ssh-rsa", e, n]
    prv = _ssh_strings(block("Private-Lines"))  # [d, p, q, iqmp]
    e = int.from_bytes(pub[1], "big")
    n = int.from_bytes(pub[2], "big")
    d = int.from_bytes(prv[0], "big")
    p = int.from_bytes(prv[1], "big")
    q = int.from_bytes(prv[2], "big")
    if p * q != n:
        raise SystemExit("ppk_to_openssh: key integrity check failed (p*q != n)")

    pubn = rsa.RSAPublicNumbers(e, n)
    priv = rsa.RSAPrivateNumbers(
        p, q, d,
        rsa.rsa_crt_dmp1(d, p), rsa.rsa_crt_dmq1(d, q), rsa.rsa_crt_iqmp(p, q),
        pubn,
    )
    pem = priv.private_key().private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.OpenSSH,
        serialization.NoEncryption(),
    )
    with open(out_path, "wb") as f:
        f.write(pem)
    os.chmod(out_path, 0o600)
    print(f"ppk_to_openssh: wrote OpenSSH key -> {out_path} ({len(pem)} bytes)")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: python scripts/ppk_to_openssh.py <input.ppk> <output_key>")
    convert(sys.argv[1], sys.argv[2])
