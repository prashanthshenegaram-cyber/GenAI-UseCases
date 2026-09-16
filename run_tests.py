import subprocess
import sys


def main():
    result = subprocess.run([sys.executable, "-m", "pytest", "-q"], check=False)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
