class StringReader:
    _buffer = ""
    _pointer = 0

    def __init__(self, data, pointer=0):  # type: (str, int) -> None
        self._buffer = data
        self._pointer = min(pointer, len(data))

    def buffer(self):  # type: () -> str
        return self._buffer

    def pointer(self):  # type: () -> int
        return self._pointer

    def set_pointer(self, ptr):  # type: (int) -> None
        self._pointer = ptr
        if self._pointer < 0:
            self._pointer = 0
        if self._pointer > len(self._buffer):
            self._pointer = len(self._buffer)

    def read(self, n):  # type: (int) -> str
        result = self._buffer[self._pointer : self._pointer + n]
        self._pointer = min(self._pointer + n, len(self._buffer))
        return result

    def unread(self, n):  # type: (int) -> StringReader
        self._pointer -= n
        if self._pointer < 0:
            self._pointer = 0
            raise Exception(
                "unread: Try unread to the position that beyond the beginning"
            )
        return self

    def jump_space(self):  # type: () -> None
        while True:
            char = self.read(1)
            if char == " " or char == "\t":
                continue
            if char != "":
                _ = self.unread(1)
            break

    def parse_string(self):  # type: () -> str
        result = ""
        while True:
            char = self.read(1)
            if char == "":
                raise Exception("parse_string: Unexpected EOF")
            if char == "\\":
                sub = char + self.read(1)
                sub = sub.encode(encoding="utf-8").decode(encoding="unicode_escape")
                result += sub
                continue
            if char == "'":
                break
            result += char
        return result
