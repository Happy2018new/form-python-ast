TYPE_CHECKING = False
if TYPE_CHECKING:
    from typing import Any
    from .combine import ExpressionCombine

from .define import (
    ExpressionElement,
    CONTEXT_PARSE_ARGUMENT,
    CONTEXT_PARSE_SUB_EXPR,
    CONTEXT_PARSE_BARRIER,
    TYPE_ENUM_INT,
    TYPE_ENUM_BOOL,
    TYPE_ENUM_FLOAT,
    TYPE_ENUM_STR,
    ELEMENT_ID_REF,
    ELEMENT_ID_SELECTOR,
    ELEMENT_ID_SCORE,
    ELEMENT_ID_COMMAND,
    ELEMENT_ID_FUNC,
)
from ..token.sentence import SentenceReader
from ..token.token import (
    TOKEN_ID_WORD,
    TOKEN_ID_LEFT_BRACKET,
    TOKEN_ID_RIGHT_BRACKET,
    TOKEN_ID_COMMA,
    TOKEN_ID_KEY_WORD_INT,
    TOKEN_ID_KEY_WORD_BOOL,
    TOKEN_ID_KEY_WORD_STR,
    TOKEN_ID_KEY_WORD_FLOAT,
)


class ExpressionNormal(ExpressionElement):
    element_id = 0
    element_payload = None

    def __init__(self, element_id):  # type: (int) -> None
        self.element_id = element_id
        self.element_payload = None


class ExpressionLiteral(ExpressionElement):
    element_id = 0  # type: int
    element_payload = 0  # type: int | bool | float | str | ExpressionCombine

    def __init__(
        self, element_id, element_payload
    ):  # type: (int, int | bool | float | str | ExpressionCombine) -> None
        self.element_id = element_id
        self.element_payload = element_payload

    def parse(
        self, reader, layer=0
    ):  # type: (SentenceReader, int) -> ExpressionLiteral
        from .combine import ExpressionCombine

        token = reader.must_read()
        if token.token_id != TOKEN_ID_LEFT_BRACKET:
            raise Exception('parse: Syntax error; expected="(", token={}'.format(token))

        val = ExpressionCombine().parse(reader, layer + 1, CONTEXT_PARSE_SUB_EXPR)
        sub = reader.unread().must_read()
        if sub.token_id != TOKEN_ID_RIGHT_BRACKET:
            raise Exception('parse: Syntax error; expected=")", token={}'.format(token))

        self.element_payload = val
        return self


class ExpressionReference(ExpressionElement):
    element_id = 0  # type: int
    element_payload = []  # type: list[Any]

    def __init__(self, payload=[]):  # type: (list[Any]) -> None
        self.element_id = ELEMENT_ID_REF
        self.element_payload = payload if len(payload) > 0 else []

    def parse(self, reader):  # type: (SentenceReader) -> ExpressionReference
        from .combine import ExpressionCombine

        token = reader.must_read()
        if token.token_id != TOKEN_ID_COMMA:
            raise Exception('parse: Syntax error; expected=",", token={}'.format(token))

        token = reader.must_read()
        if token.token_id == TOKEN_ID_KEY_WORD_INT:
            self.element_payload = [TYPE_ENUM_INT]
        elif token.token_id == TOKEN_ID_KEY_WORD_BOOL:
            self.element_payload = [TYPE_ENUM_BOOL]
        elif token.token_id == TOKEN_ID_KEY_WORD_FLOAT:
            self.element_payload = [TYPE_ENUM_FLOAT]
        elif token.token_id == TOKEN_ID_KEY_WORD_STR:
            self.element_payload = [TYPE_ENUM_STR]
        else:
            raise Exception(
                "parse: Syntax error: Type of reference must be int/bool/float/str; token={}".format(
                    token
                )
            )

        token = reader.must_read()
        if token.token_id != TOKEN_ID_COMMA:
            raise Exception('parse: Syntax error; expected=",", token={}'.format(token))
        self.element_payload.append(
            ExpressionCombine().parse(reader, 1, CONTEXT_PARSE_BARRIER)
        )
        _ = reader.unread()

        return self


class ExpressionSelector(ExpressionElement):
    element_id = ELEMENT_ID_SELECTOR  # type: int
    element_payload = None  # type: ExpressionCombine | None

    def __init__(self, payload=None):  # type: (ExpressionCombine | None) -> None
        self.element_id = ELEMENT_ID_SELECTOR
        self.element_payload = payload

    def parse(self, reader):  # type: (SentenceReader) -> ExpressionSelector
        from .combine import ExpressionCombine

        token = reader.must_read()
        if token.token_id != TOKEN_ID_COMMA:
            raise Exception('parse: Syntax error; expected=",", token={}'.format(token))

        self.element_payload = ExpressionCombine().parse(
            reader, 1, CONTEXT_PARSE_BARRIER
        )
        _ = reader.unread()

        return self


class ExpressionScore(ExpressionElement):
    element_id = ELEMENT_ID_SCORE  # type: int
    element_payload = []  # type: list[ExpressionCombine]

    def __init__(self, payload=[]):  # type: (list[ExpressionCombine]) -> None
        self.element_id = ELEMENT_ID_SCORE
        self.element_payload = payload if len(payload) > 0 else []

    def parse(self, reader):  # type: (SentenceReader) -> ExpressionScore
        from .combine import ExpressionCombine

        self.element_payload = []
        for index in range(2):
            token = reader.must_read()
            if token.token_id != TOKEN_ID_COMMA:
                raise Exception(
                    'parse: Syntax error; expected=",", index={}, token={}'.format(
                        index, token
                    )
                )
            self.element_payload.append(
                ExpressionCombine().parse(reader, 1, CONTEXT_PARSE_BARRIER)
            )
            _ = reader.unread()
        return self


class ExpressionCommand(ExpressionElement):
    element_id = ELEMENT_ID_COMMAND  # type: int
    element_payload = None  # type: ExpressionCombine | None

    def __init__(self, payload=None):  # type: (ExpressionCombine | None) -> None
        self.element_id = ELEMENT_ID_COMMAND
        self.element_payload = payload

    def parse(self, reader):  # type: (SentenceReader) -> ExpressionCommand
        from .combine import ExpressionCombine

        token = reader.must_read()
        if token.token_id != TOKEN_ID_COMMA:
            raise Exception('parse: Syntax error; expected=",", token={}'.format(token))

        self.element_payload = ExpressionCombine().parse(
            reader, 1, CONTEXT_PARSE_BARRIER
        )
        _ = reader.unread()

        return self


class ExpressionFunction(ExpressionElement):
    element_id = 0  # type: int
    element_payload = []  # type: list[Any]

    def __init__(self, element_payload=[]):  # type: (list[Any]) -> None
        self.element_id = ELEMENT_ID_FUNC
        self.element_payload = element_payload if len(element_payload) > 0 else []

    def parse(self, reader):  # type: (SentenceReader) -> ExpressionFunction
        from .combine import ExpressionCombine

        self.element_payload = []  # type: list[Any]
        arguments = []  # type: list[ExpressionCombine]

        token = reader.must_read()
        if token.token_id != TOKEN_ID_COMMA:
            raise Exception('parse: Syntax error; expected=",", token={}'.format(token))

        token = reader.must_read()
        if token.token_id == TOKEN_ID_KEY_WORD_INT:
            self.element_payload.append("int")
        elif token.token_id == TOKEN_ID_KEY_WORD_BOOL:
            self.element_payload.append("bool")
        elif token.token_id == TOKEN_ID_KEY_WORD_FLOAT:
            self.element_payload.append("float")
        elif token.token_id == TOKEN_ID_KEY_WORD_STR:
            self.element_payload.append("str")
        elif token.token_id == TOKEN_ID_WORD:
            self.element_payload.append(token.token_payload)
        else:
            raise Exception(
                "parse: Syntax error: Invalid function name; token={}".format(token)
            )

        token = reader.must_read()
        if token.token_id != TOKEN_ID_LEFT_BRACKET:
            raise Exception('parse: Syntax error; expected="(", token={}'.format(token))

        token = reader.must_read()
        if token.token_id != TOKEN_ID_RIGHT_BRACKET:
            _ = reader.unread()
            while True:
                arguments.append(
                    ExpressionCombine().parse(reader, 1, CONTEXT_PARSE_ARGUMENT)
                )
                if reader.unread().must_read().token_id == TOKEN_ID_RIGHT_BRACKET:
                    break

        self.element_payload.append(arguments)
        return self
