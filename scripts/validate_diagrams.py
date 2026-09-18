from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT / "docs" / "diagrams"
EXPORTS = SOURCES / "exports"
NAMES = ("architecture", "classes", "mer", "relational-model")


def main() -> None:
    missing: list[str] = []
    for name in NAMES:
        source = SOURCES / f"{name}.mmd"
        export = EXPORTS / f"{name}.png"
        if not source.exists() or source.stat().st_size < 200:
            missing.append(str(source))
            continue
        if not export.exists() or export.stat().st_size < 10_000:
            missing.append(str(export))
            continue
        with Image.open(export) as image:
            if image.width < 2000 or image.height < 1200:
                missing.append(f"{export} ({image.width}x{image.height})")
    if missing:
        raise SystemExit("Diagramas ausentes ou ilegíveis:\n" + "\n".join(missing))
    print("4 diagramas validados com fontes editáveis e exportações legíveis.")


if __name__ == "__main__":
    main()
