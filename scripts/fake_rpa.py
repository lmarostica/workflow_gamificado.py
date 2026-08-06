"""RPA falso para testes do orquestrador — não toca em sistema nenhum.

Uso: python fake_rpa.py [--sleep N] [--exit-code N] [--spam-kb N] [--empresa X]
"""

import argparse
import sys
import time


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sleep", type=float, default=0)
    parser.add_argument("--exit-code", type=int, default=0)
    parser.add_argument("--spam-kb", type=int, default=0)
    parser.add_argument("--empresa", default=None)
    args, _unknown = parser.parse_known_args()

    print(f"fake_rpa iniciado: empresa={args.empresa}")
    if args.spam_kb:
        for _ in range(args.spam_kb):
            sys.stdout.write("x" * 1023 + "\n")
    if args.sleep:
        time.sleep(args.sleep)
    print("fake_rpa terminando")
    return args.exit_code


if __name__ == "__main__":
    sys.exit(main())
