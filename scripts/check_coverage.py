"""Valida separadamente cobertura de linhas e branches no XML do coverage.py."""
import sys
from xml.etree import ElementTree


def main(path):
    root = ElementTree.parse(path).getroot()
    lines = float(root.attrib["line-rate"]) * 100
    branches = float(root.attrib["branch-rate"]) * 100
    print(f"Linhas: {lines:.2f}% (mínimo 85%) | Branches: {branches:.2f}% (mínimo 80%)")
    return 0 if lines >= 85 and branches >= 80 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
