"""Run from the repository root; only a salted hash is printed, never a password."""
import getpass
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.auth import hash_password

if __name__ == '__main__':
    password = getpass.getpass('New invited-user password (16+ characters): ')
    if password != getpass.getpass('Confirm password: '):
        raise SystemExit('Passwords do not match.')
    print(hash_password(password))
