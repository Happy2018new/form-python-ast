TYPE_CHECKING = False
if TYPE_CHECKING:
    from typing import Any

import json
from .baisc import (
    ExpressionElement,
    ExpressionNormal,
    ExpressionLiteral,
    ExpressionReference,
    ExpressionSelector,
    ExpressionScore,
    ExpressionFunction,
)
from .compute import (
    ExpressionTimes,
    ExpressionDivide,
    ExpressionAdd,
    ExpressionRemove,
)
from .compare import (
    ExpressionGreaterThan,
    ExpressionLessThan,
    ExpressionGreaterEqual,
    ExpressionLessEqual,
    ExpressionEqual,
    ExpressionNotEqual,
    ExpressionAnd,
    ExpressionOr,
    ExpressionIn,
    ExpressionInverse,
)
from .define import (
    ExpressionOperator,
    CONTEXT_PARSE_ASSIGN,
    CONTEXT_PARSE_IF,
    CONTEXT_PARSE_ARGUMENT,
    CONTEXT_PARSE_SUB_EXPR,
    CONTEXT_PARSE_REF_EXPR,
    ELEMENT_ID_FUNC,
    ELEMENT_ID_REF,
    ELEMENT_ID_SCORE,
    ELEMENT_ID_SELECTOR,
    ELEMENT_ID_VAR,
    ELEMENT_ID_EXPR,
    ELEMENT_ID_EQUAL,
    ELEMENT_ID_LESS_THAN,
    ELEMENT_ID_GREATER_THAN,
    ELEMENT_ID_LESS_EQUAL,
    ELEMENT_ID_GREATER_EQUAL,
    ELEMENT_ID_ADD,
    ELEMENT_ID_REMOVE,
    ELEMENT_ID_TIMES,
    ELEMENT_ID_DIVIDE,
    ELEMENT_ID_NOT_EQUAL,
    ELEMENT_ID_INT,
    ELEMENT_ID_BOOL,
    ELEMENT_ID_STR,
    ELEMENT_ID_FLOAT,
    ELEMENT_ID_AND,
    ELEMENT_ID_OR,
    ELEMENT_ID_IN,
    ELEMENT_ID_INVERSE,
)
from ..reader.any_reader import AnyReader
from ..token.sentence import SentenceReader
from ..token.token import (
    Token,
    TOKEN_ID_WORD,
    TOKEN_ID_ASSIGN,
    TOKEN_ID_LEFT_ANGLE_BRACKET,
    TOKEN_ID_RIGHT_ANGLE_BRACKET,
    TOKEN_ID_LEFT_BARRIER,
    TOKEN_ID_RIGHT_BARRIER,
    TOKEN_ID_COLON,
    TOKEN_ID_PLUS,
    TOKEN_ID_MINUS,
    TOKEN_ID_ASTERISK,
    TOKEN_ID_SLASH,
    TOKEN_ID_SINGLE_QUOTE,
    TOKEN_ID_LEFT_BRACKET,
    TOKEN_ID_RIGHT_BRACKET,
    TOKEN_ID_COMMA,
    TOKEN_ID_EXCLAMATION,
    TOKEN_ID_SEPSEPARATE,
    TOKEN_ID_KEY_WORD_INT,
    TOKEN_ID_KEY_WORD_BOOL,
    TOKEN_ID_KEY_WORD_STR,
    TOKEN_ID_KEY_WORD_FLOAT,
    TOKEN_ID_KEY_WORD_REF,
    TOKEN_ID_KEY_WORD_SELECTOR,
    TOKEN_ID_KEY_WORD_SCORE,
    TOKEN_ID_KEY_WORD_FUNC,
    TOKEN_ID_KEY_WORD_RETURN,
    TOKEN_ID_KEY_WORD_IF,
    TOKEN_ID_KEY_WORD_ELSE,
    TOKEN_ID_KEY_WORD_ELIF,
    TOKEN_ID_KEY_WORD_FI,
    TOKEN_ID_KEY_WORD_AND,
    TOKEN_ID_KEY_WORD_OR,
    TOKEN_ID_KEY_WORD_NOT,
    TOKEN_ID_KEY_WORD_IN,
    TOKEN_ID_KEY_WORD_TRUE,
    TOKEN_ID_KEY_WORD_FALSE,
)


class ExpressionCombine(ExpressionElement):
    element_id = ELEMENT_ID_EXPR  # type: int
    element_payload = []  # type: list[ExpressionElement]

    def __init__(self, payload=[]):  # type: (list[ExpressionElement]) -> None
        self.element_id = ELEMENT_ID_EXPR
        self.element_payload = payload if len(payload) > 0 else []

    def try_parse_float(self, token):  # type: (Token) -> bool
        if token.token_id != TOKEN_ID_WORD:
            return False
        if "." not in token.token_payload:
            return False
        number = float(token.token_payload)
        self.element_payload.append(ExpressionLiteral(ELEMENT_ID_FLOAT, number))
        return True

    def try_parse_int(self, token):  # type: (Token) -> bool
        if token.token_id != TOKEN_ID_WORD:
            return False
        try:
            number = int(token.token_payload)
            self.element_payload.append(ExpressionLiteral(ELEMENT_ID_INT, number))
            return True
        except Exception:
            return False

    def try_parse_var(self, token):  # type: (Token) -> bool
        if token.token_id != TOKEN_ID_WORD:
            return False

        if "'" in token.token_payload or '"' in token.token_payload:
            raise Exception(
                "try_parse_var: Syntax error: Variable name should not contain quotes; token.token_payload={}".format(
                    json.dumps(token.token_payload, ensure_ascii=False)
                )
            )
        for i in ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]:
            if token.token_payload.startswith(i):
                raise Exception(
                    "try_parse_var: Syntax error: Variable name should not start with number ({}); token.token_payload={}".format(
                        i, json.dumps(token.token_payload, ensure_ascii=False)
                    )
                )

        self.element_payload.append(
            ExpressionLiteral(ELEMENT_ID_VAR, token.token_payload)
        )
        return True

    def try_parse_equal(self, token, sub):  # type: (Token, Token) -> None
        if token.token_id != TOKEN_ID_ASSIGN:
            raise Exception(
                'try_parse_equal: Syntax error; expected="=", token={}'.format(token)
            )
        if sub.token_id != TOKEN_ID_ASSIGN:
            raise Exception(
                'try_parse_equal: Syntax error; expected="=", sub={}'.format(sub)
            )
        self.element_payload.append(ExpressionNormal(ELEMENT_ID_EQUAL))

    def try_parse_compare(
        self, reader, token, sub
    ):  # type: (SentenceReader, Token, Token) -> None
        if token.token_id == TOKEN_ID_LEFT_ANGLE_BRACKET:
            if sub.token_id == TOKEN_ID_ASSIGN:
                self.element_payload.append(ExpressionNormal(ELEMENT_ID_LESS_EQUAL))
            else:
                self.element_payload.append(ExpressionNormal(ELEMENT_ID_LESS_THAN))
                _ = reader.unread()
            return

        if token.token_id == TOKEN_ID_RIGHT_ANGLE_BRACKET:
            if sub.token_id == TOKEN_ID_ASSIGN:
                self.element_payload.append(ExpressionNormal(ELEMENT_ID_GREATER_EQUAL))
            else:
                self.element_payload.append(ExpressionNormal(ELEMENT_ID_GREATER_THAN))
                _ = reader.unread()
            return

        raise Exception(
            "try_parse_compare: Syntax error; token={}, sub={}".format(token, sub)
        )

    def try_parse_barrier(self, reader, token):  # type: (SentenceReader, Token) -> None
        if token.token_id != TOKEN_ID_LEFT_BARRIER:
            raise Exception(
                'try_parse_barrier: Syntax error; expected="{", token={}'.format(token)
            )

        sub = reader.must_read()
        if sub.token_id == TOKEN_ID_KEY_WORD_REF:
            self.element_payload.append(ExpressionReference().parse(reader))
        elif sub.token_id == TOKEN_ID_KEY_WORD_SELECTOR:
            self.element_payload.append(ExpressionSelector().parse(reader))
        elif sub.token_id == TOKEN_ID_KEY_WORD_SCORE:
            self.element_payload.append(ExpressionScore().parse(reader))
        elif sub.token_id == TOKEN_ID_KEY_WORD_FUNC:
            self.element_payload.append(ExpressionFunction().parse(reader))
        else:
            raise Exception(
                "try_parse_barrier: Syntax error: Barrier only accept ref/selector/score/func; sub={}".format(
                    sub
                )
            )

        end = reader.must_read()
        if end.token_id != TOKEN_ID_RIGHT_BARRIER:
            raise Exception("try_parse_barrier: Barrier not closed")

    def try_parse_not_equal(self, token, sub):  # type: (Token, Token) -> None
        if token.token_id != TOKEN_ID_EXCLAMATION:
            raise Exception(
                'try_parse_equal: Syntax error; expected="!", token={}'.format(token)
            )
        if sub.token_id != TOKEN_ID_ASSIGN:
            raise Exception(
                'try_parse_equal: Syntax error; expected="=", sub={}'.format(sub)
            )
        self.element_payload.append(ExpressionNormal(ELEMENT_ID_NOT_EQUAL))

    def parse_to_elements(
        self, reader, layer=0, context=CONTEXT_PARSE_ASSIGN
    ):  # type: (SentenceReader, int, int) -> None
        while True:
            token = reader.must_read()
            if token.token_id == TOKEN_ID_WORD:
                if self.try_parse_float(token):
                    continue
                if self.try_parse_int(token):
                    continue
                if self.try_parse_var(token):
                    continue
            if token.token_id == TOKEN_ID_ASSIGN:
                self.try_parse_equal(token, reader.must_read())
                continue
            if token.token_id == TOKEN_ID_LEFT_ANGLE_BRACKET:
                self.try_parse_compare(reader, token, reader.must_read())
                continue
            if token.token_id == TOKEN_ID_RIGHT_ANGLE_BRACKET:
                self.try_parse_compare(reader, token, reader.must_read())
                continue
            if token.token_id == TOKEN_ID_LEFT_BARRIER:
                self.try_parse_barrier(reader, token)
                continue
            if token.token_id == TOKEN_ID_RIGHT_BARRIER:
                if context & CONTEXT_PARSE_REF_EXPR == 0:
                    raise Exception(
                        'parse_to_elements: Syntax error: "}" can only been used under "ref" barrier'
                    )
                break
            if token.token_id == TOKEN_ID_COLON:
                if context & CONTEXT_PARSE_IF == 0:
                    raise Exception(
                        'parse_to_elements: Syntax error: ":" can only been used under "if" condition'
                    )
                break
            if token.token_id == TOKEN_ID_PLUS:
                self.element_payload.append(ExpressionNormal(ELEMENT_ID_ADD))
                continue
            if token.token_id == TOKEN_ID_MINUS:
                self.element_payload.append(ExpressionNormal(ELEMENT_ID_REMOVE))
                continue
            if token.token_id == TOKEN_ID_ASTERISK:
                self.element_payload.append(ExpressionNormal(ELEMENT_ID_TIMES))
                continue
            if token.token_id == TOKEN_ID_SLASH:
                self.element_payload.append(ExpressionNormal(ELEMENT_ID_DIVIDE))
                continue
            if token.token_id == TOKEN_ID_SINGLE_QUOTE:
                self.element_payload.append(
                    ExpressionLiteral(ELEMENT_ID_STR, token.token_payload)
                )
                continue
            if token.token_id == TOKEN_ID_LEFT_BRACKET:
                self.element_payload.append(
                    ExpressionCombine().parse(reader, layer + 1, CONTEXT_PARSE_SUB_EXPR)
                )
                continue
            if token.token_id == TOKEN_ID_RIGHT_BRACKET:
                if (
                    context & CONTEXT_PARSE_SUB_EXPR == 0
                    and context & CONTEXT_PARSE_ARGUMENT == 0
                ):
                    raise Exception(
                        'parse_to_elements: Syntax error: ")" only accepted under sub-expression or function argument'
                    )
                if layer == 0:
                    raise Exception(
                        "parse_to_elements: Syntax error: Bracket closed incorrectly"
                    )
                break
            if token.token_id == TOKEN_ID_COMMA:
                if context & CONTEXT_PARSE_ARGUMENT == 0:
                    raise Exception(
                        'parse_to_elements: Syntax error: "," only accepted under function argument'
                    )
                break
            if token.token_id == TOKEN_ID_EXCLAMATION:
                self.try_parse_not_equal(token, reader.must_read())
                continue
            if token.token_id == TOKEN_ID_SEPSEPARATE:
                if context & CONTEXT_PARSE_ASSIGN == 0:
                    raise Exception(
                        "parse_to_elements: Syntax error: Incomplete expression in the end of a line"
                    )
                break
            if token.token_id == TOKEN_ID_KEY_WORD_INT:
                self.element_payload.append(
                    ExpressionLiteral(ELEMENT_ID_INT, 0).parse(reader, layer + 1)
                )
                continue
            if token.token_id == TOKEN_ID_KEY_WORD_BOOL:
                self.element_payload.append(
                    ExpressionLiteral(ELEMENT_ID_BOOL, False).parse(reader, layer + 1)
                )
                continue
            if token.token_id == TOKEN_ID_KEY_WORD_STR:
                self.element_payload.append(
                    ExpressionLiteral(ELEMENT_ID_STR, "").parse(reader, layer + 1)
                )
                continue
            if token.token_id == TOKEN_ID_KEY_WORD_FLOAT:
                self.element_payload.append(
                    ExpressionLiteral(ELEMENT_ID_FLOAT, 0.0).parse(reader, layer + 1)
                )
                continue
            if token.token_id == TOKEN_ID_KEY_WORD_REF:
                raise Exception(
                    'parse_to_elements: Syntax error: "ref" should inside in a barrier'
                )
            if token.token_id == TOKEN_ID_KEY_WORD_SELECTOR:
                raise Exception(
                    'parse_to_elements: Syntax error: "selector" should inside in a barrier'
                )
            if token.token_id == TOKEN_ID_KEY_WORD_SCORE:
                raise Exception(
                    'parse_to_elements: Syntax error: "score" should inside in a barrier'
                )
            if token.token_id == TOKEN_ID_KEY_WORD_FUNC:
                raise Exception(
                    'parse_to_elements: Syntax error: "func" should inside in a barrier'
                )
            if token.token_id == TOKEN_ID_KEY_WORD_RETURN:
                raise Exception(
                    'parse_to_elements: Syntax error: "return" cannot be used in expression'
                )
            if token.token_id == TOKEN_ID_KEY_WORD_IF:
                raise Exception(
                    'parse_to_elements: Syntax error: "if" cannot be used in expression'
                )
            if token.token_id == TOKEN_ID_KEY_WORD_ELSE:
                raise Exception(
                    'parse_to_elements: Syntax error: "else" cannot be used in expression'
                )
            if token.token_id == TOKEN_ID_KEY_WORD_ELIF:
                raise Exception(
                    'parse_to_elements: Syntax error: "elif" cannot be used in expression'
                )
            if token.token_id == TOKEN_ID_KEY_WORD_FI:
                raise Exception(
                    'parse_to_elements: Syntax error: "fi" cannot be used in expression'
                )
            if token.token_id == TOKEN_ID_KEY_WORD_AND:
                self.element_payload.append(ExpressionNormal(ELEMENT_ID_AND))
                continue
            if token.token_id == TOKEN_ID_KEY_WORD_OR:
                self.element_payload.append(ExpressionNormal(ELEMENT_ID_OR))
                continue
            if token.token_id == TOKEN_ID_KEY_WORD_NOT:
                self.element_payload.append(ExpressionNormal(ELEMENT_ID_INVERSE))
                continue
            if token.token_id == TOKEN_ID_KEY_WORD_IN:
                self.element_payload.append(ExpressionNormal(ELEMENT_ID_IN))
                continue
            if token.token_id == TOKEN_ID_KEY_WORD_TRUE:
                self.element_payload.append(ExpressionLiteral(ELEMENT_ID_BOOL, True))
                continue
            if token.token_id == TOKEN_ID_KEY_WORD_FALSE:
                self.element_payload.append(ExpressionLiteral(ELEMENT_ID_BOOL, False))
                continue

    def is_variable(self, element):  # type: (ExpressionElement) -> bool
        if element.element_id in [
            ELEMENT_ID_VAR,
            ELEMENT_ID_EXPR,
            ELEMENT_ID_INT,
            ELEMENT_ID_BOOL,
            ELEMENT_ID_FLOAT,
            ELEMENT_ID_STR,
            ELEMENT_ID_REF,
            ELEMENT_ID_SELECTOR,
            ELEMENT_ID_SCORE,
            ELEMENT_ID_FUNC,
        ]:
            return True
        if isinstance(element, ExpressionOperator):
            return True
        return False

    def compact_operator(
        self, element_id, element_cls
    ):  # type: (int, type[ExpressionOperator]) -> None
        reader = AnyReader(self.element_payload)  # type: AnyReader
        self.element_payload = []  # type: list[ExpressionElement]

        while True:
            sub_elements = []  # type: list[ExpressionElement]

            element = reader.read()  # type: ExpressionElement | None
            if element is None:
                break
            if element.element_id != element_id:
                self.element_payload.append(element)
                continue
            self.element_payload = self.element_payload[:-1]

            if element_id == ELEMENT_ID_ADD or element_id == ELEMENT_ID_REMOVE:
                if reader.pointer() > 1:
                    operator = (
                        reader.unread().unread().must_read()
                    )  # type: ExpressionElement
                    if not self.is_variable(operator):
                        reader.contents().insert(
                            reader.pointer(), ExpressionLiteral(ELEMENT_ID_INT, 0)
                        )
                        _ = reader.must_read()
                        _ = reader.must_read()
                        self.element_payload.append(operator)
                    else:
                        _ = reader.must_read()
                else:
                    reader.contents().insert(0, ExpressionLiteral(ELEMENT_ID_INT, 0))
                    _ = reader.must_read()

            while True:
                _ = reader.unread().unread()  # type: Any
                var_a = reader.must_read()  # type: ExpressionElement
                _ = reader.must_read()  # type: Any
                var_b = reader.must_read()  # type: ExpressionElement

                if not self.is_variable(var_a):
                    raise Exception(
                        "compact_operator: Syntax error; unexpected={}".format(var_a)
                    )
                if not self.is_variable(var_b):
                    raise Exception(
                        "compact_operator: Syntax error; unexpected={}".format(var_b)
                    )
                if len(sub_elements) == 0:
                    sub_elements.append(var_a)
                sub_elements.append(var_b)

                next_op = reader.read()  # type: ExpressionElement | None
                if next_op is None or next_op.element_id != element_id:
                    if len(sub_elements) > 0:
                        self.element_payload.append(element_cls(sub_elements))
                    if next_op is not None:
                        reader.unread()
                    break

    def compact_inverse(self):  # type: () -> None
        reader = AnyReader(self.element_payload)  # type: AnyReader
        self.element_payload = []  # type: list[ExpressionElement]

        while True:
            element = reader.read()  # type: ExpressionElement | None
            if element is None:
                break
            if element.element_id == ELEMENT_ID_INVERSE:
                self.element_payload.append(ExpressionInverse([reader.must_read()]))
            else:
                self.element_payload.append(element)

    def parse(
        self, reader, layer=0, context=CONTEXT_PARSE_ASSIGN
    ):  # type: (SentenceReader, int, int) -> ExpressionCombine
        self.parse_to_elements(reader, layer, context)

        self.compact_operator(ELEMENT_ID_DIVIDE, ExpressionDivide)
        self.compact_operator(ELEMENT_ID_TIMES, ExpressionTimes)
        self.compact_operator(ELEMENT_ID_REMOVE, ExpressionRemove)
        self.compact_operator(ELEMENT_ID_ADD, ExpressionAdd)

        self.compact_operator(ELEMENT_ID_GREATER_THAN, ExpressionGreaterThan)
        self.compact_operator(ELEMENT_ID_LESS_THAN, ExpressionLessThan)
        self.compact_operator(ELEMENT_ID_GREATER_EQUAL, ExpressionGreaterEqual)
        self.compact_operator(ELEMENT_ID_LESS_EQUAL, ExpressionLessEqual)
        self.compact_operator(ELEMENT_ID_EQUAL, ExpressionEqual)
        self.compact_operator(ELEMENT_ID_NOT_EQUAL, ExpressionNotEqual)

        self.compact_operator(ELEMENT_ID_IN, ExpressionIn)
        self.compact_inverse()
        self.compact_operator(ELEMENT_ID_AND, ExpressionAnd)
        self.compact_operator(ELEMENT_ID_OR, ExpressionOr)

        if len(self.element_payload) != 1:
            self.element_payload = []
            raise Exception(
                "parse: Syntax error: Invalid compression (failed to compact the compression)"
            )
        return self
