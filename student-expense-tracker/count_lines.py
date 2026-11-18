"""count_lines.py - count source lines in the project.

Run:  python count_lines.py

We print THREE numbers per file so you can follow whichever rule your instructor confirms:
  total    = every line in the file (including blanks)
  non-blank = lines that are not empty
  code     = non-blank lines that are not pure comments or docstring-only lines
The "code" count is a simple estimate (it understands #, //, /* */, <!-- --> and triple quotes).
"""
import os

SOURCE_FILES = [
    "app.py", "database.py", "models.py", "services.py",
    "templates/index.html", "static/css/style.css", "static/js/app.js",
    "tests/test_api.py",
]


def count_file(path):
    total = non_blank = code = 0
    in_block = False                      # inside a """docstring""", /* css */ or <!-- html --> comment
    with open(path, encoding="utf-8") as file:
        for raw in file:
            total += 1
            line = raw.strip()
            if not line:
                continue
            non_blank += 1
            if in_block:
                if any(end in line for end in ('"""', "*/", "-->")):
                    in_block = False
                continue
            if line.startswith(('"""', "/*", "<!--")):
                closes_here = any(end in line[3:] for end in ('"""', "*/", "-->")) or line.endswith(("*/", "-->"))
                in_block = not closes_here
                continue
            if line.startswith(("#", "//")):
                continue
            code += 1
    return total, non_blank, code


def main():
    print(f"{'file':<24}{'total':>8}{'non-blank':>11}{'code':>8}")
    sums = [0, 0, 0]
    for path in SOURCE_FILES:
        if not os.path.exists(path):
            print(f"{path:<24}  (missing)")
            continue
        counts = count_file(path)
        sums = [a + b for a, b in zip(sums, counts)]
        print(f"{path:<24}{counts[0]:>8}{counts[1]:>11}{counts[2]:>8}")
    print("-" * 51)
    print(f"{'TOTAL':<24}{sums[0]:>8}{sums[1]:>11}{sums[2]:>8}")


if __name__ == "__main__":
    main()
