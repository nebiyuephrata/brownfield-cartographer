from pathlib import Path

from brownfield_cartographer.analyzers.tree_sitter_analyzer import analyze_python_module


def test_analyze_python_module_heuristic_or_tree_sitter(tmp_path):
    src = "\n".join(
        [
            "import os",
            "from collections import defaultdict",
            "",
            "def foo(x):",
            "    return x * 2",
            "",
            "class Bar:",
            "    def method(self):",
            "        return foo(1)",
        ]
    )

    file_path = tmp_path / "sample_module.py"
    file_path.write_text(src, encoding="utf-8")

    module = analyze_python_module(file_path)

    # Basic structural checks
    assert module.id.endswith("sample_module")
    assert module.path == str(file_path)
    assert "foo" in module.functions
    assert "Bar" in module.classes

    # Import extraction should pick up both styles.
    assert "os" in module.imports
    assert "collections" in {imp.split(".")[0] for imp in module.imports}

    # Evidence should be populated with a reasonable method tag.
    assert module.evidence, "Expected at least one evidence entry"
    method_values = {e.method for e in module.evidence}
    # Depending on environment we may have tree-sitter or heuristic mode.
    assert method_values & {"tree_sitter:python", "heuristic:python"}

