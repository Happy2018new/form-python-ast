import json

TOKEN_ID_WORD = 0
TOKEN_ID_ASSIGN = 1
TOKEN_ID_LEFT_ANGLE_BRACKET = 2
TOKEN_ID_RIGHT_ANGLE_BRACKET = 3
TOKEN_ID_LEFT_BARRIER = 4
TOKEN_ID_RIGHT_BARRIER = 5
TOKEN_ID_COLON = 6
TOKEN_ID_PLUS = 7
TOKEN_ID_MINUS = 8
TOKEN_ID_ASTERISK = 9
TOKEN_ID_SLASH = 10
TOKEN_ID_SINGLE_QUOTE = 11
TOKEN_ID_LEFT_BRACKET = 12
TOKEN_ID_RIGHT_BRACKET = 13
TOKEN_ID_COMMA = 14
TOKEN_ID_EXCLAMATION = 15
TOKEN_ID_SEPSEPARATE = 16
TOKEN_ID_KEY_WORD_INT = 17
TOKEN_ID_KEY_WORD_BOOL = 18
TOKEN_ID_KEY_WORD_STR = 19
TOKEN_ID_KEY_WORD_FLOAT = 20
TOKEN_ID_KEY_WORD_REF = 21
TOKEN_ID_KEY_WORD_SELECTOR = 22
TOKEN_ID_KEY_WORD_SCORE = 23
TOKEN_ID_KEY_WORD_COMMAND = 24
TOKEN_ID_KEY_WORD_FUNC = 25
TOKEN_ID_KEY_WORD_RETURN = 26
TOKEN_ID_KEY_WORD_IF = 27
TOKEN_ID_KEY_WORD_ELSE = 28
TOKEN_ID_KEY_WORD_ELIF = 29
TOKEN_ID_KEY_WORD_FI = 30
TOKEN_ID_KEY_WORD_FOR = 31
TOKEN_ID_KEY_WORD_CONTINUE = 32
TOKEN_ID_KEY_WORD_BREAK = 33
TOKEN_ID_KEY_WORD_ROF = 34
TOKEN_ID_KEY_WORD_DEL = 35
TOKEN_ID_KEY_WORD_AND = 36
TOKEN_ID_KEY_WORD_OR = 37
TOKEN_ID_KEY_WORD_NOT = 38
TOKEN_ID_KEY_WORD_IN = 39
TOKEN_ID_KEY_WORD_TRUE = 40
TOKEN_ID_KEY_WORD_FALSE = 41

CHAR_TO_TOKEN_ID = {
    "=": TOKEN_ID_ASSIGN,
    "<": TOKEN_ID_LEFT_ANGLE_BRACKET,
    ">": TOKEN_ID_RIGHT_ANGLE_BRACKET,
    "{": TOKEN_ID_LEFT_BARRIER,
    "}": TOKEN_ID_RIGHT_BARRIER,
    ":": TOKEN_ID_COLON,
    "+": TOKEN_ID_PLUS,
    "-": TOKEN_ID_MINUS,
    "*": TOKEN_ID_ASTERISK,
    "/": TOKEN_ID_SLASH,
    "'": TOKEN_ID_SINGLE_QUOTE,
    "(": TOKEN_ID_LEFT_BRACKET,
    ")": TOKEN_ID_RIGHT_BRACKET,
    ",": TOKEN_ID_COMMA,
    "!": TOKEN_ID_EXCLAMATION,
    "\n": TOKEN_ID_SEPSEPARATE,
    "|": TOKEN_ID_SEPSEPARATE,
}

KEY_WORD_TO_TOKEN_ID = {
    "int": TOKEN_ID_KEY_WORD_INT,
    "bool": TOKEN_ID_KEY_WORD_BOOL,
    "str": TOKEN_ID_KEY_WORD_STR,
    "float": TOKEN_ID_KEY_WORD_FLOAT,
    "ref": TOKEN_ID_KEY_WORD_REF,
    "selector": TOKEN_ID_KEY_WORD_SELECTOR,
    "score": TOKEN_ID_KEY_WORD_SCORE,
    "command": TOKEN_ID_KEY_WORD_COMMAND,
    "func": TOKEN_ID_KEY_WORD_FUNC,
    "return": TOKEN_ID_KEY_WORD_RETURN,
    "if": TOKEN_ID_KEY_WORD_IF,
    "else": TOKEN_ID_KEY_WORD_ELSE,
    "elif": TOKEN_ID_KEY_WORD_ELIF,
    "fi": TOKEN_ID_KEY_WORD_FI,
    "for": TOKEN_ID_KEY_WORD_FOR,
    "continue": TOKEN_ID_KEY_WORD_CONTINUE,
    "break": TOKEN_ID_KEY_WORD_BREAK,
    "rof": TOKEN_ID_KEY_WORD_ROF,
    "del": TOKEN_ID_KEY_WORD_DEL,
    "and": TOKEN_ID_KEY_WORD_AND,
    "or": TOKEN_ID_KEY_WORD_OR,
    "not": TOKEN_ID_KEY_WORD_NOT,
    "in": TOKEN_ID_KEY_WORD_IN,
    "True": TOKEN_ID_KEY_WORD_TRUE,
    "False": TOKEN_ID_KEY_WORD_FALSE,
}

TOKEN_ID_TO_NAME = {}
for key, value in CHAR_TO_TOKEN_ID.items():
    TOKEN_ID_TO_NAME[value] = key
for key, value in KEY_WORD_TO_TOKEN_ID.items():
    TOKEN_ID_TO_NAME[value] = key
TOKEN_ID_TO_NAME[TOKEN_ID_WORD] = "word"
TOKEN_ID_TO_NAME[TOKEN_ID_SEPSEPARATE] = "|"


class Token:
    token_id = 0
    token_payload = ""
    ori_start_ptr = 0
    ori_end_ptr = 0

    def __init__(
        self, token_id, token_payload="", ori_start_ptr=0, ori_end_ptr=0
    ):  # type: (int, str, int, int) -> None
        self.token_id = token_id
        self.token_payload = token_payload
        self.ori_start_ptr = ori_start_ptr
        self.ori_end_ptr = ori_end_ptr

    def __repr__(self):  # type: () -> str
        prefix = "Token(id={}, name={}".format(
            self.token_id,
            json.dumps(TOKEN_ID_TO_NAME[self.token_id], ensure_ascii=False),
        )
        if len(self.token_payload) > 0:
            prefix += ", payload={}".format(
                json.dumps(self.token_payload, ensure_ascii=False)
            )
        return prefix + ", ori_start_ptr={}, ori_end_ptr={})".format(
            self.ori_start_ptr, self.ori_end_ptr
        )
