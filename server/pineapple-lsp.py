from pygls.exceptions import PyglsError, JsonRpcException
from pygls.lsp.server import LanguageServer
from lsprotocol.types import (SemanticTokens,
                              SemanticTokensParams,
                              SemanticTokensLegend,
                              TEXT_DOCUMENT_COMPLETION,
                              CompletionOptions,
                              CompletionParams,
                              CompletionItem)

import enum
import logging
import operator
import re
from functools import reduce
from typing import Dict
from typing import List
from typing import Optional

import attrs
from lsprotocol import types

from pygls.cli import start_server
from pygls.lsp.server import LanguageServer
from pygls.workspace import TextDocument


server = LanguageServer("pineapple", "v0.1")

print("Running Pineapple LSP 0.1")

class TokenModifier(enum.IntFlag):
    deprecated = enum.auto()
    readonly = enum.auto()
    defaultLibrary = enum.auto()
    definition = enum.auto()


@attrs.define
class Token:
    line: int
    offset: int
    text: str

    tok_type: str = ""
    tok_modifiers: List[TokenModifier] = attrs.field(factory=list)


TokenTypes = ["keyword", "variable", "function", "operator", "parameter", "type", "string", "number"]

SYMBOL = re.compile(r"\w+")
OP = re.compile(r"->|[\{\}\(\)\.,+:*-=]")
SPACE = re.compile(r"\s+")
NUMBER = re.compile(r'\d+(\.\d+)?')
STRING = re.compile(r'"([^"\\]|\\.|\\\n)*"')


KEYWORDS = {"type", "fnc"}


def is_type(token: Optional[Token]) -> bool:
    if token is None:
        return False

    return token.text == "type" and token.tok_type == "keyword"


def is_fn(token: Optional[Token]) -> bool:
    if token is None:
        return False

    return token.text == "fnc" and token.tok_type == "keyword"


def is_lparen(token: Optional[Token]) -> bool:
    if token is None:
        return False

    return token.text == "(" and token.tok_type == "operator"


def is_rparen(token: Optional[Token]) -> bool:
    if token is None:
        return False

    return token.text == ")" and token.tok_type == "operator"


def is_lbrace(token: Optional[Token]) -> bool:
    if token is None:
        return False

    return token.text == "{" and token.tok_type == "operator"


def is_rbrace(token: Optional[Token]) -> bool:
    if token is None:
        return False

    return token.text == "}" and token.tok_type == "operator"


def is_colon(token: Optional[Token]) -> bool:
    if token is None:
        return False

    return token.text == ":" and token.tok_type == "operator"


class SemanticTokensServer(LanguageServer):
    """Language server demonstrating the semantic token methods from the LSP
    specification."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tokens: Dict[str, List[Token]] = {}

    def parse(self, doc: TextDocument):
        """Convert the given document into a list of tokens"""
        tokens = self.lex(doc)
        self.classify_tokens(tokens)

        # logging.info("%s", tokens)
        self.tokens[doc.uri] = tokens

    def classify_tokens(self, tokens: List[Token]):
        """Given a list of tokens, determine their type and modifiers."""

        def prev(idx):
            """Get the previous token, if possible"""
            if idx < 0:
                return None

            return tokens[idx - 1]

        def next(idx):
            """Get the next token, if possible"""
            if idx >= len(tokens) - 1:
                return None

            return tokens[idx + 1]

        in_brace = False
        in_paren = False

        for idx, token in enumerate(tokens):
            if token.tok_type == "operator":
                if is_lparen(token):
                    in_paren = True

                elif is_rparen(token):
                    in_paren = False

                elif is_lbrace(token):
                    in_brace = True

                elif is_rbrace(token):
                    in_brace = False

                continue

            if token.text in KEYWORDS:
                token.tok_type = "keyword"

            elif token.text[0].isupper():
                token.tok_type = "type"

                if is_type(prev(idx)):
                    token.tok_modifiers.append(TokenModifier.definition)

            elif is_fn(prev(idx)) or is_lparen(next(idx)):
                token.tok_type = "function"
                token.tok_modifiers.append(TokenModifier.definition)

            elif is_colon(next(idx)) and in_brace:
                token.tok_type = "parameter"

            elif is_colon(prev(idx)) and in_paren:
                token.tok_type = "type"
                token.tok_modifiers.append(TokenModifier.defaultLibrary)
            elif NUMBER.match(token.text):
                token.tok_type = "number"

            elif STRING.match(token.text):
                token.tok_type = "string"
            else:
                token.tok_type = "variable"

    def lex(self, doc: TextDocument) -> List[Token]:
        """Convert the given document into a list of tokens"""
        tokens = []

        prev_line = 0
        prev_offset = 0

        for current_line, line in enumerate(doc.lines):
            line = line.rstrip("\n")
            prev_offset = current_offset = 0
            chars_left = len(line)

            while line:
                if (match := SPACE.match(line)) is not None:
                    # Skip whitespace
                    current_offset += len(match.group(0))
                    line = line[match.end():]

                elif (match := STRING.match(line)) is not None:
                    tokens.append(
                        Token(
                            line=current_line - prev_line,
                            offset=current_offset - prev_offset,
                            text=match.group(0),
                            tok_type="string"
                        )
                    )
                    line = line[match.end():]
                    prev_offset = current_offset
                    prev_line = current_line
                    current_offset += len(match.group(0))

                elif (match := SYMBOL.match(line)) is not None:
                    tokens.append(
                        Token(
                            line=current_line - prev_line,
                            offset=current_offset - prev_offset,
                            text=match.group(0),
                        )
                    )
                    line = line[match.end():]
                    prev_offset = current_offset
                    prev_line = current_line
                    current_offset += len(match.group(0))

                elif (match := OP.match(line)) is not None:
                    tokens.append(
                        Token(
                            line=current_line - prev_line,
                            offset=current_offset - prev_offset,
                            text=match.group(0),
                            tok_type="operator",
                        )
                    )
                    line = line[match.end():]
                    prev_offset = current_offset
                    prev_line = current_line
                    current_offset += len(match.group(0))

                else:
                    raise RuntimeError(f"No match: {line!r}")

                # Make sure we don't hit an infinite loop
                if (n := len(line)) == chars_left:
                    raise RuntimeError("Inifite loop detected")
                else:
                    chars_left = n

        return tokens


semantic_server = SemanticTokensServer("semantic-tokens-server", "v1")


@semantic_server.feature(types.TEXT_DOCUMENT_DID_OPEN)
def did_open(ls: SemanticTokensServer, params: types.DidOpenTextDocumentParams):
    """Parse each document when it is opened"""
    doc = ls.workspace.get_text_document(params.text_document.uri)
    ls.parse(doc)


@semantic_server.feature(types.TEXT_DOCUMENT_DID_CHANGE)
def did_change(ls: SemanticTokensServer, params: types.DidOpenTextDocumentParams):
    """Parse each document when it is changed"""
    doc = ls.workspace.get_text_document(params.text_document.uri)
    ls.parse(doc)


@semantic_server.feature(
    types.TEXT_DOCUMENT_SEMANTIC_TOKENS_FULL,
    types.SemanticTokensLegend(
        token_types=TokenTypes,
        token_modifiers=[m.name for m in TokenModifier],
    ),
)
def semantic_tokens_full(ls: SemanticTokensServer, params: types.SemanticTokensParams):
    """Return the semantic tokens for the entire document"""
    data = []
    tokens = ls.tokens.get(params.text_document.uri, [])

    for token in tokens:
        data.extend(
            [
                token.line,
                token.offset,
                len(token.text),
                TokenTypes.index(token.tok_type),
                reduce(operator.or_, token.tok_modifiers, 0),
            ]
        )

    return types.SemanticTokens(data=data)


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
    start_server(semantic_server)
    server.start_io()