"""Valida separadamente cobertura de linhas e branches no XML do coverage.py."""
import sys
from xml.etree import ElementTree


def main(path):
    root = ElementTree.parse(path).getroot()
    lines_covered = int(root.attrib["lines-covered"])
    lines_valid = int(root.attrib["lines-valid"])
    branches_covered = int(root.attrib["branches-covered"])
    branches_valid = int(root.attrib["branches-valid"])
    lines = 100 * lines_covered / lines_valid
    branches = 100 * branches_covered / branches_valid
    print(f"Linhas: {lines:.2f}% (mínimo 85%) | Branches: {branches:.2f}% (mínimo 80%)")
    # Contagens do XML evitam que o arredondamento altere o resultado do gate.
    passed = 100 * lines_covered >= 85 * lines_valid and 100 * branches_covered >= 80 * branches_valid
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
