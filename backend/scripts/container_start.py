"""Set ownership of the mounted data directory, then drop container root privileges."""

import os
import sys
from pathlib import Path

if __name__ == "__main__":
    folder = Path("/var/data")
    if not folder.is_dir():
        raise SystemExit("Mount /var/data before starting the container.")
    if os.geteuid() == 0:
        os.chown(folder, 10001, 10001)
        os.chmod(folder, 0o700)
        os.setgroups([])
        os.setgid(10001)
        os.setuid(10001)
    os.execv(sys.executable, [sys.executable, "-m", "scripts.start"])
