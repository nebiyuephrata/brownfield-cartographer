from __future__ import annotations

from pathlib import Path
from typing import List

try:
    from tree_sitter import Language, Parser
except Exception:  # pragma: no cover
    Language = None
    Parser = None

from ..models.nodes import Evidence, ModuleNode


_PY_LANGUAGE = None


def _get_python_language():
    """
    Best-effort loader for the tree-sitter Python language.

    This expects an environment variable or prebuilt library to be available.
    For now, if loading fails, we return None and fall back to a heuristic parser.
    """
    global _PY_LANGUAGE
    if _PY_LANGUAGE is not None:
        return _PY_LANGUAGE

    try:  # pragma: no cover - environment dependent
        # Users can override this with a prebuilt tree-sitter library if desired.
        from tree_sitter_languages import get_language

        _PY_LANGUAGE = get_language("python")
    except Exception:
        _PY_LANGUAGE = None
    return _PY_LANGUAGE


def analyze_python_module(path: Path) -> ModuleNode:
    """
    Analyze a Python module using tree-sitter when available, otherwise heuristics.
    """
    source = path.read_text(encoding="utf-8", errors="ignore")
    evidence = [
        Evidence(
            file_path=str(path),
            line_start=1,
            line_end=max(1, source.count("\n") + 1),
            method="tree_sitter:python" if _get_python_language() else "heuristic:python",
        )
    ]

    language = _get_python_language()
    imports: List[str] = []
    functions: List[str] = []
    classes: List[str] = []

    if language is None:
        # Heuristic: very rough line-based parsing.
        for line in source.splitlines():
            stripped = line.strip()
            if stripped.startswith("import "):
                target = stripped[len("import ") :].split(" ")[0]
                imports.append(target)
            elif stripped.startswith("from "):
                target = stripped[len("from ") :].split(" ")[0]
                imports.append(target)
            elif stripped.startswith("def "):
                name = stripped[len("def ") :].split("(")[0]
                functions.append(name)
            elif stripped.startswith("class "):
                name = stripped[len("class ") :].split("(")[0].split(":")[0]
                classes.append(name)
    else:  # pragma: no cover - depends on external language library
        if Parser is None:
            language = None
        parser = Parser()
        parser.set_language(language)
        tree = parser.parse(source.encode("utf8"))
        root = tree.root_node

        for node in root.children:
            if node.type in {"import_statement", "import_from_statement"}:
                text = source[node.start_byte : node.end_byte]
                if node.type == "import_statement":
                    for part in text.split("import", 1)[1].split(","):
                        imports.append(part.strip().split(" ")[0])
                else:
                    after_from = text.split("from", 1)[1]
                    target = after_from.split("import", 1)[0].strip()
                    imports.append(target)
            elif node.type == "function_definition":
                text = source[node.start_byte : node.end_byte]
                header = text.split("(", 1)[0]
                name = header.replace("def", "").strip()
                functions.append(name)
            elif node.type == "class_definition":
                text = source[node.start_byte : node.end_byte]
                header = text.split("(", 1)[0]
                name = header.replace("class", "").replace(":", "").strip()
                classes.append(name)

    module_id = str(path.relative_to(path.anchor)).replace("/", ".").removesuffix(".py")

    return ModuleNode(
        id=module_id,
        path=str(path),
        language="python",
        imports=sorted(set(imports)),
        functions=sorted(set(functions)),
        classes=sorted(set(classes)),
        evidence=evidence,
    )


def analyze_sql_structure(path: Path) -> Evidence:
    """
    Lightweight placeholder for SQL static structure analysis.

    For now this simply returns an Evidence object covering the whole file so
    that future analyzers can attach more detailed metadata without changing
    call sites.
    """
    sql_text = path.read_text(encoding="utf-8", errors="ignore")
    return Evidence(
        file_path=str(path),
        line_start=1,
        line_end=max(1, sql_text.count("\n") + 1),
        method="heuristic:sql",
    )


def analyze_yaml_structure(path: Path) -> Evidence:
    """
    Lightweight placeholder for YAML static structure analysis.

    Similar to analyze_sql_structure, this currently produces a single Evidence
    object to anchor future metadata derived from YAML configs.
    """
    text = path.read_text(encoding="utf-8", errors="ignore")
    return Evidence(
        file_path=str(path),
        line_start=1,
        line_end=max(1, text.count("\n") + 1),
        method="heuristic:yaml",
    )


def analyze_module(path: Path) -> ModuleNode:
    """
    Multi-language entry point that routes to the correct parser based on extension.

    Today this focuses on Python modules via analyze_python_module, but the structure
    allows additional grammars (e.g. JavaScript/TypeScript) to be wired in later
    without changing call sites.
    """
    suffix = path.suffix.lower()
    if suffix == ".py":
        return analyze_python_module(path)
    # Future: wire in additional language analyzers here.
    return analyze_python_module(path)

