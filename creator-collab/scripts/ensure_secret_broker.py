from __future__ import annotations

import json
import py_compile
from pathlib import Path

ROOT = Path(r"C:\Zippoworkz")
PATH = ROOT / "_system" / "SECRET_BROKER.py"

OLD_PROTECT = '    script = "$b=[Text.Encoding]::UTF8.GetBytes($env:ZW_SECRET_VALUE);$e=[Security.Cryptography.ProtectedData]::Protect($b,$null,[Security.Cryptography.DataProtectionScope]::CurrentUser);[Convert]::ToBase64String($e)"'
NEW_PROTECT = '    script = "$ErrorActionPreference=\'Stop\';Add-Type -AssemblyName System.Security;$b=[Text.Encoding]::UTF8.GetBytes($env:ZW_SECRET_VALUE);$e=[Security.Cryptography.ProtectedData]::Protect($b,$null,[Security.Cryptography.DataProtectionScope]::CurrentUser);[Convert]::ToBase64String($e)"'
OLD_UNPROTECT = '    script = "$e=[Convert]::FromBase64String($env:ZW_SECRET_BLOB);$b=[Security.Cryptography.ProtectedData]::Unprotect($e,$null,[Security.Cryptography.DataProtectionScope]::CurrentUser);[Text.Encoding]::UTF8.GetString($b)"'
NEW_UNPROTECT = '    script = "$ErrorActionPreference=\'Stop\';Add-Type -AssemblyName System.Security;$e=[Convert]::FromBase64String($env:ZW_SECRET_BLOB);$b=[Security.Cryptography.ProtectedData]::Unprotect($e,$null,[Security.Cryptography.DataProtectionScope]::CurrentUser);[Text.Encoding]::UTF8.GetString($b)"'

def main() -> int:
    if not PATH.is_file():
        raise SystemExit("secret_broker_missing")
    text = PATH.read_text(encoding="utf-8-sig")
    changed = False
    for old, new in ((OLD_PROTECT, NEW_PROTECT), (OLD_UNPROTECT, NEW_UNPROTECT)):
        if new in text:
            continue
        if old not in text:
            raise SystemExit("secret_broker_unknown_dpapi_implementation")
        text = text.replace(old, new, 1)
        changed = True
    if changed:
        temporary = PATH.with_suffix(".tmp")
        temporary.write_text(text, encoding="utf-8")
        py_compile.compile(str(temporary), doraise=True)
        temporary.replace(PATH)
    py_compile.compile(str(PATH), doraise=True)
    print(json.dumps({"ok": True, "changed": changed, "path": str(PATH)}))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
