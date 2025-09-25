from pygls.exceptions import PyglsError, JsonRpcException
from pygls.lsp.server import LanguageServer
from lsprotocol.types import (SemanticTokens,
                              SemanticTokensParams,
                              SemanticTokensLegend,
                              TEXT_DOCUMENT_COMPLETION,
                              CompletionOptions,
                              CompletionParams,
                              CompletionItem)

server = LanguageServer("pineapple", "v0.1")


print("Running Pineapple LSP 0.1")

legend = SemanticTokensLegend(
    token_types=["function", "variable", "keyword", "string", "number"],
    token_modifiers=[]
)

@server.feature("textDocument/semanticTokens/full")
def semantic_tokens(ls: LanguageServer, params: SemanticTokensParams) -> SemanticTokens:
    doc = ls.workspace.get_document(params.text_document.uri)
    lines = doc.source.splitlines()
    data = []

    user_functions = set()
    import re

    for line_idx, line in enumerate(lines):
        # Detect function definitions
        for match in re.finditer(r"\bfnc\s+([a-zA-Z_]+)(?=\s*\()", line):
            func_name = match.group(1)
            start_col = match.start(1)
            length = len(func_name)
            data.extend([line_idx, start_col, length, 0, 0])  # function
            user_functions.add(func_name)

    # Detect calls after collecting all function names
    for line_idx, line in enumerate(lines):
        for func_name in user_functions:
            for match in re.finditer(rf"\b{func_name}\b(?=\s*\()", line):
                start_col = match.start()
                length = len(func_name)
                token_type = 0  # "function"
                token_modifier = 0
                data.extend([line_idx, start_col, length, token_type, token_modifier])

    return SemanticTokens(data=data)



@server.feature(
    TEXT_DOCUMENT_COMPLETION,
    CompletionOptions(trigger_characters=["."]),
)
def completions(params: CompletionParams):
    document = server.workspace.get_text_document(params.text_document.uri)
    current_line = document.lines[params.position.line].strip()

    if not current_line.endswith("hello."):
        return [
        CompletionItem(label="fuck"),
        CompletionItem(label="you"),
        ]

    return [
        CompletionItem(label="world"),
        CompletionItem(label="friend"),
    ]


if __name__ == "__main__":
    server.start_io()