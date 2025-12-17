# -*- coding: utf-8 -*-

TYPE_CHECKING = False
if TYPE_CHECKING:
    from typing import Any


class AnyReader:
    _contents = []  # type: list[Any]
    _pointer = 0  # type: int

    def __init__(self, _contents, pointer=0):  # type: (list[Any], int) -> None
        self._contents = _contents
        self._pointer = pointer

    def contents(self):  # type: () -> list[Any]
        return self._contents

    def pointer(self):  # type: () -> int
        return self._pointer

    def set_pointer(self, ptr):  # type: (int) -> None
        self._pointer = ptr
        if self._pointer < 0:
            self._pointer = 0
        if self._pointer > len(self._contents):
            self._pointer = len(self._contents)

    def read(self):  # type: () -> Any | None
        if self._pointer >= len(self._contents):
            return None
        self._pointer += 1
        return self._contents[self._pointer - 1]

    def unread(self):  # type: () -> AnyReader
        self._pointer -= 1
        if self._pointer < 0:
            self._pointer = 0
            raise Exception("unread: Try unread in the beginning")
        return self

    def must_read(self):  # type: () -> Any
        element = self.read()
        if element is None:
            raise Exception("must_read: Unexpected EOF")
        return element
