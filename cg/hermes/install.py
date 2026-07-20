"""Deploy the cohermes Hermes hook into ~/.hermes/hooks/cohermes/.

Run:  python -m cg.hermes.install

Hermes discovers hooks from ``$HERMES_HOME/hooks/*/``. The hook imports cohermes,
so the Hermes process needs it on PYTHONPATH (or cohermes pip-installed).
"""
import os
import pathlib
import shutil

_SRC = pathlib.Path(__file__).parent


def install(hermes_home: str | None = None) -> pathlib.Path:
    home = pathlib.Path(hermes_home or os.environ.get("HERMES_HOME",
                                                      os.path.expanduser("~/.hermes")))
    dst = home / "hooks" / "cohermes"
    dst.mkdir(parents=True, exist_ok=True)
    for f in ("HOOK.yaml", "handler.py"):
        shutil.copy(_SRC / f, dst / f)
    return dst


def main():
    dst = install()
    print(f"installed cohermes Hermes hook → {dst}")
    print("(a proper `pip install -e .` of cohermes makes PYTHONPATH unnecessary.)")


if __name__ == "__main__":
    main()
