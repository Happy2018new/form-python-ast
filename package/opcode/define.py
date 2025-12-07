TYPE_CHECKING = False
if TYPE_CHECKING:
    from typing import Any

import json
from ..expression.combine import ExpressionCombine

OPCODE_ASSIGN = 0
OPCODE_CONDITION = 1
OPCODE_EXPRESSION = 3
OPCODE_RETURN = 2

OPCODE_ID_TO_NAME = {
    OPCODE_ASSIGN: "assign",
    OPCODE_CONDITION: "condition",
    OPCODE_EXPRESSION: "expression",
    OPCODE_RETURN: "return",
}


class ConditionWithCode:
    condition = None  # type: ExpressionCombine | None
    state_line = ""  # type: str
    code_block = []  # type: list[OpcodeBase]

    def __init__(
        self, condition, state_line, code_block=[]
    ):  # type: (ExpressionCombine | None, str, list[OpcodeBase]) -> None
        self.condition = condition
        self.state_line = state_line
        self.code_block = code_block if len(code_block) > 0 else []


class OpcodeBase:
    opcode_id = 0  # type: int
    opcode_payload = None  # type: Any
    origin_line = ""  # type: str

    def __init__(
        self, opcode_id, opcode_payload, origin_line=""
    ):  # type: (int, Any, str) -> None
        self.opcode_id = opcode_id
        self.opcode_payload = opcode_payload
        self.origin_line = origin_line

    def __repr__(self):  # type: () -> str
        return "OpcodeBase(id={}, name={}, payload={}, line={})".format(
            self.opcode_id,
            OPCODE_ID_TO_NAME[self.opcode_id],
            self.opcode_payload,
            json.dumps(self.origin_line, ensure_ascii=False),
        )


class OpcodeAssign(OpcodeBase):
    opcode_id = OPCODE_ASSIGN  # type: int
    opcode_payload = ("", ExpressionCombine())  # type: tuple[str, ExpressionCombine]
    origin_line = ""  # type: str

    def __init__(
        self, payload, line
    ):  # type: (tuple[str, ExpressionCombine], str) -> None
        OpcodeBase.__init__(self, OPCODE_ASSIGN, payload, line)


class OpcodeCondition(OpcodeBase):
    opcode_id = OPCODE_CONDITION  # type: int
    opcode_payload = []  # type: list[ConditionWithCode]
    origin_line = "fi"

    def __init__(self, payload):  # type: (list[ConditionWithCode]) -> None
        OpcodeBase.__init__(self, OPCODE_CONDITION, payload, "fi")


class OpcodeExpression(OpcodeBase):
    opcode_id = OPCODE_EXPRESSION  # type: int
    opcode_payload = ExpressionCombine()  # type: ExpressionCombine
    origin_line = ""  # type: str

    def __init__(self, payload, line):  # type: (ExpressionCombine, str) -> None
        OpcodeBase.__init__(self, OPCODE_EXPRESSION, payload, line)


class OpcodeReturn(OpcodeBase):
    opcode_id = OPCODE_RETURN  # type: int
    opcode_payload = ExpressionCombine()  # type: ExpressionCombine
    origin_line = ""  # type: str

    def __init__(self, payload, line):  # type: (ExpressionCombine, str) -> None
        OpcodeBase.__init__(self, OPCODE_RETURN, payload, line)
