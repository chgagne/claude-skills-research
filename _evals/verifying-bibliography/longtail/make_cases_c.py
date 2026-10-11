#!/usr/bin/env python3
"""Protocol C cases: the long-tail bibliographies as case.yaml with a scaffold that installs the
frozen _shared module and the S2 key file, so the skills' scripts can actually run (the reason
protocol C exists). The prompt body is the frozen long-tail prompt, unchanged.

  make_cases_c.py --out <plugin>/evals --shared <dir> --key-file <file> --runs 2
"""
import argparse, os, pathlib, re, shutil, sys

HERE = pathlib.Path(__file__).resolve().parent
SCAFFOLD = """#!/bin/bash
mkdir -p "$HOME/.claude/skills" && cp -R "{shared}" "$HOME/.claude/skills/_shared"
mkdir -p "$HOME/.config/scholarly" && cp "{key}" "$HOME/.config/scholarly/s2_key" && chmod 600 "$HOME/.config/scholarly/s2_key"
"""


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", required=True); ap.add_argument("--shared", required=True)
    ap.add_argument("--key-file", required=True); ap.add_argument("--runs", type=int, default=2)
    a = ap.parse_args(argv)
    for src in sorted((HERE / "evals").iterdir()):
        text = (src / "prompt.md").read_text()
        body = re.split(r"^---\s*$", text, maxsplit=2, flags=re.M)[2].strip("\n")
        d = pathlib.Path(a.out) / src.name
        if d.exists():
            shutil.rmtree(d)
        shutil.copytree(src / "graders", d / "graders")
        yaml = ["schema_version: \"1.1\"", f"name: \"{src.name}\"", f"runs: {a.runs}", "execution:",
                "  max_turns: 60", "  timeout_seconds: 1500",
                "  allowed_tools: [Read, Write, Edit, Bash, Glob, Grep, WebFetch, WebSearch, Skill]",
                "  prompt: |"] + ["    " + l for l in body.splitlines()] + ["context:", "  scaffold_script: scaffold.sh"]
        (d / "case.yaml").write_text("\n".join(yaml) + "\n")
        (d / "scaffold.sh").write_text(SCAFFOLD.format(shared=os.path.abspath(a.shared), key=os.path.abspath(a.key_file)))
        os.chmod(d / "scaffold.sh", 0o755)
        print("wrote", d)
    return 0


if __name__ == "__main__":
    sys.exit(main())
