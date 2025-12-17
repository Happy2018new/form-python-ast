# -*- coding: utf-8 -*-

from ..reader.any_reader import AnyReader
from ..reader.string_reader import StringReader
from .token import (
    Token,
    CHAR_TO_TOKEN_ID,
    KEY_WORD_TO_TOKEN_ID,
    TOKEN_ID_WORD,
    TOKEN_ID_SINGLE_QUOTE,
)


class Sentence:
    reader = StringReader("")  # type: StringReader
    tokens = []  # type: list[Token]

    def __init__(self, reader):  # type: (StringReader) -> None
        self.reader = reader
        self.tokens = []

    def parse_all(self):  # type: () -> tuple[int, int, str | None]
        ptr = self.reader.pointer()

        while True:
            ptr = self.reader.pointer()
            try:
                if not self.parse_next():
                    break
            except Exception as e:
                return ptr, self.reader.pointer(), str(e)

        return ptr, self.reader.pointer(), None

    def parse_next(self):  # type: () -> bool
        self.reader.jump_space()
        ptr = self.reader.pointer()
        word = self.reader.read(1)

        if word == "":
            return False
        if word == "'":
            self.tokens.append(
                Token(
                    TOKEN_ID_SINGLE_QUOTE,
                    self.reader.parse_string(),
                    ptr,
                    self.reader.pointer(),
                )
            )
            return True
        if word in CHAR_TO_TOKEN_ID:
            self.tokens.append(
                Token(
                    CHAR_TO_TOKEN_ID[word],
                    "",
                    ptr,
                    self.reader.pointer(),
                )
            )
            return True

        while True:
            char = self.reader.read(1)
            if char == "":
                break
            if char == " " or char == "\t" or char in CHAR_TO_TOKEN_ID:
                _ = self.reader.unread(1)
                break
            word += char

        if word in KEY_WORD_TO_TOKEN_ID:
            self.tokens.append(
                Token(
                    KEY_WORD_TO_TOKEN_ID[word],
                    "",
                    ptr,
                    self.reader.pointer(),
                )
            )
        else:
            self.tokens.append(
                Token(
                    TOKEN_ID_WORD,
                    word,
                    ptr,
                    self.reader.pointer(),
                )
            )
        return True


class SentenceReader(AnyReader):
    _contents = []  # type: list[Token]
    _pointer = 0  # type: int

    def __init__(self, tokens=[], pointer=0):  # type: (list[Token], int) -> None
        self._contents = tokens if len(tokens) > 0 else []
        self._pointer = pointer

    def contents(self):  # type: () -> list[Token]
        return self._contents

    def read(self):  # type: () -> Token | None
        return AnyReader.read(self)

    def unread(self):  # type: () -> SentenceReader
        AnyReader.unread(self)
        return self

    def must_read(self):  # type: () -> Token
        return AnyReader.must_read(self)
