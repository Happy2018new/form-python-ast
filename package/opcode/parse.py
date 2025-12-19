# -*- coding: utf-8 -*-

from .define import (
    ConditionWithCode,
    ForLoopCodeBlock,
    OpcodeBase,
    OpcodeAssign,
    OpcodeCondition,
    OpcodeForLoop,
    OpcodeContinue,
    OpcodeBreak,
    OpcodeExpression,
    OpcodeReturn,
)
from ..expression.combine import ExpressionCombine
from ..expression.define import (
    CONTEXT_PARSE_ASSIGN,
    CONTEXT_PARSE_IF,
    CONTEXT_PARSE_FOR,
)
from ..reader.string_reader import StringReader
from ..token.sentence import Sentence, SentenceReader
from ..token.token import (
    Token,
    TOKEN_ID_WORD,
    TOKEN_ID_ASSIGN,
    TOKEN_ID_COLON,
    TOKEN_ID_COMMA,
    TOKEN_ID_SEPSEPARATE,
    TOKEN_ID_KEY_WORD_RETURN,
    TOKEN_ID_KEY_WORD_IF,
    TOKEN_ID_KEY_WORD_ELSE,
    TOKEN_ID_KEY_WORD_ELIF,
    TOKEN_ID_KEY_WORD_FI,
    TOKEN_ID_KEY_WORD_FOR,
    TOKEN_ID_KEY_WORD_CONTINUE,
    TOKEN_ID_KEY_WORD_BREAK,
    TOKEN_ID_KEY_WORD_ROF,
)

ORD_ZERO, ORD_NINE = ord("0"), ord("9")
DEFAULT_EMPTY_EXCEPTION = Exception()


class CodeParser:
    code = ""  # type: str
    reader = SentenceReader()  # type: SentenceReader
    code_block = []  # type: list[OpcodeBase]

    def __init__(self, code=""):  # type: (str) -> None
        self.code = code + "\n"
        sentence = Sentence(StringReader(self.code))

        ptr1, ptr2, err = sentence.parse_all()
        if err is not None:
            self._fast_normal_panic(ptr1, ptr2, err)
            raise Exception("unreachable")

        self.reader = SentenceReader(sentence.tokens)
        self.code_block = []

    def _format_problem_normal(self, ptr1, ptr2):  # type: (int, int) -> str
        code = ""
        left_overflow = False
        right_overflow = False
        if True:
            # Part that before the problem
            if ptr1 - 30 > 0:
                code += "...\n"
                code += self.code[ptr1 - 30 : ptr1]
                left_overflow = True
            else:
                code += self.code[:ptr1]
            # Problem part
            code += ">>"
            code += self.code[ptr1:ptr2]
            code += "<<"
            # Part that after the problem
            if ptr2 + 30 < len(self.code):
                code += self.code[ptr2 : ptr2 + 30]
                code += "\n..."
                right_overflow = True
            else:
                code += self.code[ptr2:]

        blocks = code.split("\n")
        states = [True] * len(blocks)
        start, end = 0, len(blocks) - 1
        if left_overflow and blocks[0] == "...":
            start += 1
        if right_overflow and blocks[-1] == "...":
            end -= 1
        for i in range(start, end + 1):
            if blocks[i].strip() == "":
                states[i] = False
            else:
                break
        for i in range(end, start - 1, -1):
            if blocks[i].strip() == "":
                states[i] = False
            else:
                break

        prefix = ["  " + value for index, value in enumerate(blocks) if states[index]]
        return "\n".join(prefix).rstrip()

    def _format_problem_sentence(self, ptr1, ptr2):  # type: (int, int) -> str
        contents = self.reader.contents()

        ptr1 = min(max(0, ptr1), len(contents) - 1)
        ptr2 = min(max(0, ptr2), len(contents) - 1)
        if ptr1 == ptr2:
            ptr2 += 1

        return self._format_problem_normal(
            contents[ptr1].ori_start_ptr, contents[ptr2 - 1].ori_end_ptr
        )

    def _fast_normal_panic(self, ptr1, ptr2, err):  # type: (int, int, str) -> None
        raise Exception(
            "Syntax Error.\n\n- Error -\n  {}\n\n- Code -\n{}".format(
                err, self._format_problem_normal(ptr1, ptr2)
            )
        )

    def _fast_sentence_panic(self, ptr1, ptr2, err):  # type: (int, int, str) -> None
        raise Exception(
            "Syntax Error.\n\n- Error -\n  {}\n\n- Code -\n{}".format(
                err, self._format_problem_sentence(ptr1, ptr2)
            )
        )

    def _get_line_code(self, ptr1, ptr2):  # type: (int, int) -> str
        contents = self.reader.contents()
        ptr1 = min(max(0, ptr1), len(contents) - 1)
        ptr2 = min(max(0, ptr2), len(contents) - 1)
        if ptr1 == ptr2:
            ptr2 += 1

        ptr1 = contents[ptr1].ori_start_ptr
        ptr2 = contents[ptr2 - 1].ori_end_ptr
        code = self.code[ptr1:ptr2]

        while code.endswith("|"):
            code = code[:-1]
        return code.strip()

    def _validate_next_token(
        self, ptr, token_id, error
    ):  # type: (int, int, str) -> None
        token = self.reader.read()
        if token is None or token.token_id != token_id:
            self._fast_sentence_panic(ptr, self.reader.pointer(), error)
            raise Exception("unreachable")

    def _validate_var_name(self, token, ptr1, ptr2):  # type: (Token, int, int) -> None
        if "'" in token.token_payload or '"' in token.token_payload:
            self._fast_sentence_panic(
                ptr1, ptr2, "Variable name should not contain quotes"
            )
            raise Exception("unreachable")
        if "." in token.token_payload:
            self._fast_sentence_panic(
                ptr1, ptr2, "Variable name should not contain dots"
            )
            raise Exception("unreachable")
        if ORD_ZERO <= ord(token.token_payload[0]) <= ORD_NINE:
            self._fast_sentence_panic(
                ptr1,
                ptr2,
                "Variable name should not start with number ({})".format(
                    token.token_payload[0]
                ),
            )
            raise Exception("unreachable")

    def _validate_next_line(self, ptr, unread=False):  # type: (int, bool) -> None
        token = self.reader.read()
        if token is None:
            return
        if token.token_id != TOKEN_ID_SEPSEPARATE:
            self._fast_sentence_panic(
                ptr,
                self.reader.pointer(),
                'You must write statements line by line or use "|" to represent a new line',
            )
            raise Exception("unreachable")
        if unread:
            self.reader.unread()

    def _parse_variable(self, ptr):  # type: (int) -> str
        token = self.reader.read()
        if token is None:
            self._fast_sentence_panic(
                ptr, self.reader.pointer(), "Unexpected EOF when reading variable name"
            )
            raise Exception("unreachable")
        if token.token_id != TOKEN_ID_WORD:
            self._fast_sentence_panic(
                ptr,
                self.reader.pointer(),
                "Expected a variable name but got {}".format(token),
            )
            raise Exception("unreachable")
        return token.token_payload

    def _parse_expression(
        self, context=CONTEXT_PARSE_ASSIGN, panic=True, unread=False
    ):  # type: (int, bool, bool) -> ExpressionCombine
        ptr = self.reader.pointer()
        try:
            expression = ExpressionCombine().parse(self.reader, 0, context)
            if unread:
                self.reader.unread()
        except Exception as e:
            if panic:
                self._fast_sentence_panic(ptr, self.reader.pointer(), str(e))
                raise Exception("unreachable")
            else:
                raise e
        return expression

    def _parse_assign(self, ptr, token):  # type: (int, Token) -> OpcodeAssign
        self._validate_var_name(token, ptr, self.reader.pointer())
        self._validate_next_token(
            self.reader.pointer(),
            TOKEN_ID_ASSIGN,
            'Assign statement should use "=" after variable name',
        )
        return OpcodeAssign(
            (
                token.token_payload,
                self._parse_expression(CONTEXT_PARSE_ASSIGN, True, True),
            ),
            self._get_line_code(ptr, self.reader.pointer()),
        )

    def _parse_return(self, ptr):  # type: (int) -> OpcodeReturn
        return OpcodeReturn(
            self._parse_expression(CONTEXT_PARSE_ASSIGN, True, True),
            self._get_line_code(ptr, self.reader.pointer()),
        )

    def _parse_code(
        self, ptr
    ):  # type: (int) -> tuple[OpcodeBase | None, tuple[Token, int, int, Exception] | None]
        expr_start_ptr = self.reader.pointer()
        expr_end_ptr = expr_start_ptr
        expr_parse_err = DEFAULT_EMPTY_EXCEPTION
        try:
            return (
                OpcodeExpression(
                    self._parse_expression(CONTEXT_PARSE_ASSIGN, False, True),
                    self._get_line_code(expr_start_ptr, self.reader.pointer()),
                ),
                None,
            )
        except Exception as e:
            expr_end_ptr, expr_parse_err = self.reader.pointer(), e
            self.reader.set_pointer(expr_start_ptr)

        ptr = self.reader.pointer()
        token = self.reader.read()
        if token is None:
            return None, None

        if token.token_id == TOKEN_ID_WORD:
            return self._parse_assign(ptr, token), None
        if token.token_id == TOKEN_ID_KEY_WORD_IF:
            return self._parse_condition(ptr), None
        if token.token_id == TOKEN_ID_KEY_WORD_FOR:
            return self._parse_for_loop(ptr), None
        if token.token_id == TOKEN_ID_KEY_WORD_RETURN:
            return self._parse_return(ptr), None
        if token.token_id == TOKEN_ID_KEY_WORD_CONTINUE:
            code = self._get_line_code(ptr, self.reader.pointer())
            return OpcodeContinue(code), None
        if token.token_id == TOKEN_ID_KEY_WORD_BREAK:
            code = self._get_line_code(ptr, self.reader.pointer())
            return OpcodeBreak(code), None

        return None, (token, expr_start_ptr, expr_end_ptr, expr_parse_err)

    def _parse_condition(self, ptr):  # type: (int) -> OpcodeCondition
        conditions = [
            ConditionWithCode(
                self._parse_expression(CONTEXT_PARSE_IF, True, False),
                self._get_line_code(ptr, self.reader.pointer()),
                [],
            )
        ]

        while True:
            sub_ptr = self.reader.pointer()
            opcode, further = self._parse_code(sub_ptr)

            if opcode is not None:
                conditions[-1].code_block.append(opcode)
                self._validate_next_line(sub_ptr, False)
                continue
            if further is None:
                self._fast_sentence_panic(
                    sub_ptr, self.reader.pointer(), 'If statement not closed with "fi"'
                )
                raise Exception("unreachable")

            if further[0].token_id == TOKEN_ID_KEY_WORD_ELIF:
                conditions.append(
                    ConditionWithCode(
                        self._parse_expression(CONTEXT_PARSE_IF, True, False),
                        self._get_line_code(sub_ptr, self.reader.pointer()),
                        [],
                    )
                )
            elif further[0].token_id == TOKEN_ID_KEY_WORD_ELSE:
                self._validate_next_token(
                    self.reader.pointer(),
                    TOKEN_ID_COLON,
                    'Else statement should use ":" after the expression',
                )
                conditions.append(
                    ConditionWithCode(
                        None, self._get_line_code(sub_ptr, self.reader.pointer()), []
                    )
                )
            elif further[0].token_id == TOKEN_ID_KEY_WORD_FI:
                self._validate_next_line(sub_ptr, True)
                break
            elif further[0].token_id == TOKEN_ID_SEPSEPARATE:
                continue
            else:
                self._fast_sentence_panic(further[1], further[2], str(further[3]))
                raise Exception("unreachable")

            self._validate_next_line(sub_ptr, False)

        return OpcodeCondition(conditions)

    def _parse_for_loop(self, ptr):  # type: (int) -> OpcodeForLoop
        variable = self._parse_variable(ptr)
        self._validate_next_token(
            self.reader.pointer(),
            TOKEN_ID_COMMA,
            'For loop should use "," before the expression',
        )

        repeat_times = self._parse_expression(CONTEXT_PARSE_FOR, True, False)
        end_expr_ptr = self.reader.pointer()
        self._validate_next_line(ptr, False)

        code_block = []  # type: list[OpcodeBase]
        while True:
            sub_ptr = self.reader.pointer()
            opcode, further = self._parse_code(sub_ptr)

            if opcode is not None:
                code_block.append(opcode)
                self._validate_next_line(sub_ptr, False)
                continue
            if further is None:
                self._fast_sentence_panic(
                    sub_ptr, self.reader.pointer(), 'For loop not closed with "rof"'
                )
                raise Exception("unreachable")

            if further[0].token_id == TOKEN_ID_KEY_WORD_ROF:
                self._validate_next_line(sub_ptr, True)
                break
            elif further[0].token_id == TOKEN_ID_SEPSEPARATE:
                continue
            else:
                self._fast_sentence_panic(further[1], further[2], str(further[3]))
                raise Exception("unreachable")

        return OpcodeForLoop(
            ForLoopCodeBlock(
                variable,
                repeat_times,
                self._get_line_code(ptr, end_expr_ptr),
                code_block,
            )
        )

    def parse(self):  # type: () -> CodeParser
        while True:
            ptr = self.reader.pointer()
            opcode, further = self._parse_code(ptr)

            if opcode is not None:
                self.code_block.append(opcode)
                self._validate_next_line(ptr, False)
                continue
            if further is None:
                break
            if further[0].token_id == TOKEN_ID_SEPSEPARATE:
                continue

            self._fast_sentence_panic(further[1], further[2], str(further[3]))
            raise Exception("unreachable")

        return self
