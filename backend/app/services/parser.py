"""
Code parser — turns raw source files into structured "chunks".

RAG works best when each chunk is a meaningful unit (function, class),
not a random slice of text. Step 1 uses language-aware parsing:

  - Python: built-in `ast` module (accurate, no extra dependencies)
  - JavaScript/TypeScript: regex patterns (good enough for common cases)

Each chunk carries metadata (file path, name, line numbers) that we'll
attach to embeddings in step 3 and show to the user in step 5.
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass
class CodeChunk:
    """One searchable unit of source code."""

    file_path: str
    chunk_type: str  # "function", "class", "method", "module"
    name: str | None
    start_line: int
    end_line: int
    content: str
    language: str


def _read_file_lines(path: Path) -> list[str]:
    try:
        return path.read_text(encoding="utf-8").splitlines(keepends=True)
    except UnicodeDecodeError:
        # Skip binary or oddly encoded files
        return []


def _slice_lines(lines: list[str], start_line: int, end_line: int) -> str:
    """Extract 1-indexed line range from a file."""
    return "".join(lines[start_line - 1 : end_line])


def parse_python_file(path: Path, repo_root: Path) -> list[CodeChunk]:
    """
    Parse a .py file using Python's AST.

    AST = Abstract Syntax Tree: Python reads the file and builds a tree
    of nodes (functions, classes, imports). We walk that tree to find
    top-level functions and classes.
    """
    source = path.read_text(encoding="utf-8")
    lines = source.splitlines(keepends=True)
    rel_path = str(path.relative_to(repo_root)).replace("\\", "/")

    try:
        tree = ast.parse(source, filename=rel_path)
    except SyntaxError:
        # Broken syntax — fall back to treating the whole file as one chunk
        return [
            CodeChunk(
                file_path=rel_path,
                chunk_type="module",
                name=path.stem,
                start_line=1,
                end_line=max(len(lines), 1),
                content=source,
                language="python",
            )
        ]

    chunks: list[CodeChunk] = []

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            chunks.append(
                CodeChunk(
                    file_path=rel_path,
                    chunk_type="function",
                    name=node.name,
                    start_line=node.lineno,
                    end_line=getattr(node, "end_lineno", node.lineno),
                    content=_slice_lines(
                        lines, node.lineno, getattr(node, "end_lineno", node.lineno)
                    ),
                    language="python",
                )
            )
        elif isinstance(node, ast.ClassDef):
            chunks.append(
                CodeChunk(
                    file_path=rel_path,
                    chunk_type="class",
                    name=node.name,
                    start_line=node.lineno,
                    end_line=getattr(node, "end_lineno", node.lineno),
                    content=_slice_lines(
                        lines, node.lineno, getattr(node, "end_lineno", node.lineno)
                    ),
                    language="python",
                )
            )

            # Also extract methods inside the class for finer-grained search
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    chunks.append(
                        CodeChunk(
                            file_path=rel_path,
                            chunk_type="method",
                            name=f"{node.name}.{item.name}",
                            start_line=item.lineno,
                            end_line=getattr(item, "end_lineno", item.lineno),
                            content=_slice_lines(
                                lines,
                                item.lineno,
                                getattr(item, "end_lineno", item.lineno),
                            ),
                            language="python",
                        )
                    )

    if not chunks:
        # File has only imports/constants — keep whole file as one chunk
        chunks.append(
            CodeChunk(
                file_path=rel_path,
                chunk_type="module",
                name=path.stem,
                start_line=1,
                end_line=max(len(lines), 1),
                content=source,
                language="python",
            )
        )

    return chunks


# --- JavaScript / TypeScript (regex-based) ---

# Matches: function foo(...) { ... }
JS_FUNCTION_PATTERN = re.compile(
    r"^(?:export\s+)?(?:async\s+)?function\s+(?P<name>[A-Za-z_$][\w$]*)\s*\(",
    re.MULTILINE,
)

# Matches: const foo = (...) => { ... }  or  const foo = async function(...) {
JS_ARROW_OR_CONST_FN = re.compile(
    r"^(?:export\s+)?(?:const|let|var)\s+(?P<name>[A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?"
    r"(?:function\s*\(|\([^)]*\)\s*=>)",
    re.MULTILINE,
)

# Matches: class Foo { ... }
JS_CLASS_PATTERN = re.compile(
    r"^(?:export\s+)?(?:default\s+)?class\s+(?P<name>[A-Za-z_$][\w$]*)",
    re.MULTILINE,
)


def _find_js_block_end(lines: list[str], start_idx: int) -> int:
    """
    Find where a JS function/class body ends by counting { and }.

    Simple brace matching — works for most normal code, but can fail on
    braces inside strings. Good enough for step 1; tree-sitter would be
    more accurate in production.
    """
    depth = 0
    started = False

    for i in range(start_idx, len(lines)):
        line = lines[i]
        for char in line:
            if char == "{":
                depth += 1
                started = True
            elif char == "}":
                depth -= 1
                if started and depth == 0:
                    return i + 1  # 1-indexed line number

    return len(lines)


def parse_javascript_file(path: Path, repo_root: Path) -> list[CodeChunk]:
    """Parse .js/.jsx/.ts/.tsx files using regex + brace matching."""
    lines = _read_file_lines(path)
    if not lines:
        return []

    source = "".join(lines)
    rel_path = str(path.relative_to(repo_root)).replace("\\", "/")
    language = "typescript" if path.suffix.lower() in {".ts", ".tsx"} else "javascript"

    chunks: list[CodeChunk] = []
    seen_starts: set[int] = set()

    patterns: list[tuple[re.Pattern[str], str]] = [
        (JS_CLASS_PATTERN, "class"),
        (JS_FUNCTION_PATTERN, "function"),
        (JS_ARROW_OR_CONST_FN, "function"),
    ]

    for pattern, chunk_type in patterns:
        for match in pattern.finditer(source):
            # Convert byte offset to line number
            start_line = source[: match.start()].count("\n") + 1
            if start_line in seen_starts:
                continue
            seen_starts.add(start_line)

            end_line = _find_js_block_end(lines, start_line - 1)
            content = _slice_lines(lines, start_line, end_line)

            chunks.append(
                CodeChunk(
                    file_path=rel_path,
                    chunk_type=chunk_type,
                    name=match.group("name"),
                    start_line=start_line,
                    end_line=end_line,
                    content=content,
                    language=language,
                )
            )

    if not chunks:
        chunks.append(
            CodeChunk(
                file_path=rel_path,
                chunk_type="module",
                name=path.stem,
                start_line=1,
                end_line=len(lines),
                content=source,
                language=language,
            )
        )

    return chunks


def parse_code_file(path: Path, repo_root: Path) -> list[CodeChunk]:
    """Route a file to the correct language parser."""
    suffix = path.suffix.lower()

    if suffix == ".py":
        return parse_python_file(path, repo_root)
    if suffix in {".js", ".jsx", ".ts", ".tsx"}:
        return parse_javascript_file(path, repo_root)

    return []


def parse_repository(repo_root: Path) -> tuple[list[CodeChunk], int]:
    """
    Parse every supported file in a cloned repo.

    Returns:
        (all_chunks, number_of_files_scanned)
    """
    from app.services.github import list_code_files

    all_chunks: list[CodeChunk] = []
    files = list_code_files(repo_root)

    for file_path in files:
        all_chunks.extend(parse_code_file(file_path, repo_root))

    return all_chunks, len(files)
