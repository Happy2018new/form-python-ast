from .define import (
    ConditionWithCode,
    OpcodeBase,
    OpcodeAssign,
    OpcodeCondition,
    OpcodeExpression,
    OpcodeReturn,
)
from ..reader.string_reader import StringReader
from ..expression.combine import ExpressionCombine
from ..expression.define import CONTEXT_PARSE_ASSIGN, CONTEXT_PARSE_IF
from ..token.sentence import Sentence, SentenceReader
from ..token.token import (
    Token,
    TOKEN_ID_WORD,
    TOKEN_ID_ASSIGN,
    TOKEN_ID_COLON,
    TOKEN_ID_SEPSEPARATE,
    TOKEN_ID_KEY_WORD_RETURN,
    TOKEN_ID_KEY_WORD_IF,
    TOKEN_ID_KEY_WORD_ELSE,
    TOKEN_ID_KEY_WORD_ELIF,
    TOKEN_ID_KEY_WORD_FI,
)


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
        if True:
            # Part that before the problem
            if ptr1 - 30 > 0:
                code += "..."
                code += self.code[ptr1 - 30 : ptr1]
            else:
                code += self.code[:ptr1]
            # Problem part
            code += ">>"
            code += self.code[ptr1:ptr2]
            code += "<<"
            # Part that after the problem
            if ptr2 + 30 < len(self.code):
                code += self.code[ptr2 : ptr2 + 30]
                code += "..."
            else:
                code += self.code[ptr2:]

        blocks = code.split("\n")
        prefix = ["  " + i for i in blocks]
        while True:
            if len(prefix) == 0:
                break
            if len(prefix[0].strip()) == 0:
                prefix = prefix[1:]
            else:
                break

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

    def _validate_var_name(self, token, ptr1, ptr2):  # type: (Token, int, int) -> None
        if "'" in token.token_payload or '"' in token.token_payload:
            self._fast_sentence_panic(
                ptr1, ptr2, "Variable name should not contain quotes"
            )
        if "." in token.token_payload:
            self._fast_sentence_panic(
                ptr1, ptr2, "Variable name should not contain dots"
            )
        for i in ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]:
            if token.token_payload.startswith(i):
                self._fast_sentence_panic(
                    ptr1,
                    ptr2,
                    "Variable name should not start with number ({})".format(i),
                )

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

    def _parse_expression(
        self, context=CONTEXT_PARSE_ASSIGN, panic=True
    ):  # type: (int, bool) -> ExpressionCombine
        ptr = self.reader.pointer()
        try:
            expression = ExpressionCombine().parse(self.reader, 0, context)
            if context == CONTEXT_PARSE_ASSIGN:
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
        sub_ptr = self.reader.pointer()
        sub_token = self.reader.read()

        if sub_token is None or sub_token.token_id != TOKEN_ID_ASSIGN:
            self._fast_sentence_panic(
                sub_ptr,
                self.reader.pointer(),
                'Assign statement should use "=" after variable name',
            )
            raise Exception("unreachable")

        return OpcodeAssign(
            (token.token_payload, self._parse_expression(CONTEXT_PARSE_ASSIGN, True)),
            self._get_line_code(ptr, self.reader.pointer()),
        )

    def _parse_return(self, ptr):  # type: (int) -> OpcodeReturn
        return OpcodeReturn(
            self._parse_expression(CONTEXT_PARSE_ASSIGN, True),
            self._get_line_code(ptr, self.reader.pointer()),
        )

    def _parse_condition(self, ptr):  # type: (int) -> OpcodeCondition
        conditions = [
            ConditionWithCode(
                self._parse_expression(CONTEXT_PARSE_IF, True),
                self._get_line_code(ptr, self.reader.pointer()),
                [],
            )
        ]

        while True:
            sub_ptr = self.reader.pointer()
            try:
                conditions[-1].code_block.append(
                    OpcodeExpression(
                        self._parse_expression(CONTEXT_PARSE_ASSIGN, False),
                        self._get_line_code(sub_ptr, self.reader.pointer()),
                    )
                )
                continue
            except Exception:
                self.reader.set_pointer(sub_ptr)

            sub_ptr = self.reader.pointer()
            sub_token = self.reader.read()
            if sub_token is None:
                self._fast_sentence_panic(
                    sub_ptr, self.reader.pointer(), 'If statement not closed with "fi"'
                )
                raise Exception("unreachable")

            if sub_token.token_id == TOKEN_ID_WORD:
                assign = self._parse_assign(sub_ptr, sub_token)
                conditions[-1].code_block.append(assign)
            elif sub_token.token_id == TOKEN_ID_KEY_WORD_IF:
                condition = self._parse_condition(sub_ptr)
                conditions[-1].code_block.append(condition)
            elif sub_token.token_id == TOKEN_ID_KEY_WORD_ELIF:
                conditions.append(
                    ConditionWithCode(
                        self._parse_expression(CONTEXT_PARSE_IF, True),
                        self._get_line_code(sub_ptr, self.reader.pointer()),
                        [],
                    )
                )
            elif sub_token.token_id == TOKEN_ID_KEY_WORD_ELSE:
                colon = self.reader.read()
                if colon is None or colon.token_id != TOKEN_ID_COLON:
                    self._fast_sentence_panic(
                        sub_ptr,
                        self.reader.pointer(),
                        'Else statement should use ":" after the expression',
                    )
                conditions.append(
                    ConditionWithCode(
                        None, self._get_line_code(sub_ptr, self.reader.pointer()), []
                    )
                )
            elif sub_token.token_id == TOKEN_ID_KEY_WORD_RETURN:
                conditions[-1].code_block.append(self._parse_return(sub_ptr))
            elif sub_token.token_id == TOKEN_ID_SEPSEPARATE:
                continue
            elif sub_token.token_id == TOKEN_ID_KEY_WORD_FI:
                self._validate_next_line(sub_ptr, True)
                break
            else:
                self._fast_sentence_panic(
                    sub_ptr,
                    self.reader.pointer(),
                    "Unexpected token; sub_token={}".format(sub_token),
                )

            self._validate_next_line(sub_ptr, False)

        return OpcodeCondition(conditions)

    def parse(self):  # type: () -> CodeParser
        while True:
            ptr = self.reader.pointer()
            try:
                self.code_block.append(
                    OpcodeExpression(
                        self._parse_expression(CONTEXT_PARSE_ASSIGN, False),
                        self._get_line_code(ptr, self.reader.pointer()),
                    )
                )
                continue
            except Exception:
                self.reader.set_pointer(ptr)

            ptr = self.reader.pointer()
            token = self.reader.read()
            if token is None:
                break

            if token.token_id == TOKEN_ID_WORD:
                self.code_block.append(self._parse_assign(ptr, token))
            elif token.token_id == TOKEN_ID_KEY_WORD_IF:
                self.code_block.append(self._parse_condition(ptr))
            elif token.token_id == TOKEN_ID_KEY_WORD_RETURN:
                self.code_block.append(self._parse_return(ptr))
            elif token.token_id == TOKEN_ID_SEPSEPARATE:
                continue
            else:
                self._fast_sentence_panic(
                    ptr,
                    self.reader.pointer(),
                    "Unexpected token; sub_token={}".format(token),
                )

            self._validate_next_line(ptr, False)

        return self
