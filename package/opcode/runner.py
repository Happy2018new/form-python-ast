TYPE_CHECKING = False
if TYPE_CHECKING:
    from typing import Callable

import json
from .define import (
    ConditionWithCode,
    OpcodeBase,
    OpcodeAssign,
    OpcodeCondition,
    OpcodeExpression,
    OpcodeReturn,
)
from ..expression.combine import ExpressionCombine
from ..expression.define import (
    ExpressionElement,
    TYPE_ENUM_BOOL,
    TYPE_ENUM_FLOAT,
    TYPE_ENUM_INT,
    TYPE_ENUM_STR,
    ELEMENT_ID_VAR,
    ELEMENT_ID_INT,
    ELEMENT_ID_BOOL,
    ELEMENT_ID_FLOAT,
    ELEMENT_ID_STR,
)
from ..expression.baisc import (
    ExpressionLiteral,
    ExpressionReference,
    ExpressionScore,
    ExpressionSelector,
    ExpressionFunction,
)
from ..expression.compute import (
    ExpressionTimes,
    ExpressionDivide,
    ExpressionAdd,
    ExpressionRemove,
)
from ..expression.compare import (
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


class GameInteract:
    selector = None  # type: Callable[[str], str] | None
    score = None  # type: Callable[[str, str], int] | None
    ref = None  # type: Callable[[int], int | bool | float | str] | None

    def __init__(
        self,
        selector=None,  # type: Callable[[str], str] | None
        score=None,  # type: Callable[[str, str], int] | None
        ref=None,  # type: Callable[[int], int | bool | float | str] | None
    ):  # type: (...) -> None
        self.selector = selector
        self.score = score
        self.ref = ref

    def _default_selector(self, target):  # type: (str) -> str
        _ = target
        return ""

    def _default_score(self, target, scoreboard):  # type: (str, str) -> int
        _, _ = target, scoreboard
        return 0

    def _default_ref(self, index):  # type: (int) -> int | bool | float | str
        _ = index
        return 0

    def is_empty_interact(self):  # type: () -> bool
        if self.selector is not None:
            return False
        if self.score is not None:
            return False
        if self.ref is not None:
            return False
        return True

    def selector_func(self):  # type: () -> Callable[[str], str]
        if self.selector is None:
            return self._default_selector
        return self.selector

    def score_func(self):  # type: () -> Callable[[str, str], int]
        if self.score is None:
            return self._default_score
        return self.score

    def ref_func(self):  # type: () -> Callable[[int], int | bool | float | str]
        if self.ref is None:
            return self._default_ref
        return self.ref


class CodeRunner:
    code_block = []  # type: list[OpcodeBase]
    interact = GameInteract()  # type: GameInteract
    builtins = {}  # type: dict[str, Callable[..., int | bool | float | str]]
    _variables = {}  # type: dict[str, int | bool | float | str]
    _return = None  # type: int | bool | float | str | None

    def __init__(
        self,
        code_block=[],  # type: list[OpcodeBase]
        interact=GameInteract(),  # type: GameInteract
        builtins={},  # type: dict[str, Callable[..., int | bool | float | str]]
    ):  # type: (...) -> None
        self.code_block = code_block if len(code_block) > 0 else []
        self.interact = interact if not interact.is_empty_interact() else GameInteract()
        self._init_builtins(builtins)
        self._variables = {}
        self._return = None

    def _init_builtins(
        self, builtins
    ):  # type: (dict[str, Callable[..., int | bool | float | str]]) -> None
        self.builtins = {}
        for key, value in builtins.items():
            self.builtins[key] = value
        if "int" not in self.builtins:
            self.builtins["int"] = lambda x: int(x)
        if "bool" not in self.builtins:
            self.builtins["bool"] = lambda x: bool(x)
        if "float" not in self.builtins:
            self.builtins["float"] = lambda x: float(x)
        if "str" not in self.builtins:
            self.builtins["str"] = lambda x: str(x)

    def _fast_normal_panic(self, code_block, err):  # type: (OpcodeBase, str) -> None
        raise Exception(
            "Runtime Error.\n\n- Error -\n  {}\n\n- Code -\n  {}".format(
                err, code_block.origin_line
            )
        )

    def _fast_condition_panic(
        self, condition, index=-1, err=""
    ):  # type: (ConditionWithCode, int, str) -> None
        prefix = "Runtime Error in condition.\n\n- Error -\n  {}\n\n- Condition -\n  {}".format(
            err, condition.state_line
        )
        if index != -1:
            prefix += "\n\n- Code -\n  {}".format(
                condition.code_block[index].origin_line
            )
        raise Exception(prefix)

    def _process_literal(
        self, element
    ):  # type: (ExpressionLiteral) -> int | bool | float | str
        if element.element_id == ELEMENT_ID_VAR:
            assert isinstance(element.element_payload, str)
            if element.element_payload not in self._variables:
                raise Exception(
                    "Variable {} used before assignment".format(
                        json.dumps(element.element_payload, ensure_ascii=False)
                    )
                )
            return self._variables[element.element_payload]

        if isinstance(element.element_payload, ExpressionCombine):
            value = self._process_element(element.element_payload)
            if element.element_id == ELEMENT_ID_INT:
                return int(value)
            elif element.element_id == ELEMENT_ID_BOOL:
                return bool(value)
            elif element.element_id == ELEMENT_ID_FLOAT:
                return float(value)
            elif element.element_id == ELEMENT_ID_STR:
                return str(value)
            return value

        return element.element_payload

    def _process_ref(
        self, element
    ):  # type: (ExpressionReference) -> int | bool | float | str
        index = self._process_element(element.element_payload[1])
        if isinstance(index, bool) or not isinstance(index, int):
            raise Exception(
                '_process_ref: The index for "ref" statement must be int; index={}'.format(
                    index
                )
            )
        value = self.interact.ref_func()(index)

        if element.element_payload[0] == TYPE_ENUM_BOOL:
            if not isinstance(value, bool):
                raise Exception(
                    '_process_ref: Assertion failed; expected="bool", value={}'.format(
                        value
                    )
                )
        elif element.element_payload[0] == TYPE_ENUM_INT:
            if not isinstance(value, int):
                raise Exception(
                    '_process_ref: Assertion failed; expected="int", value={}'.format(
                        value
                    )
                )
        elif element.element_payload[0] == TYPE_ENUM_FLOAT:
            if not isinstance(value, float):
                raise Exception(
                    '_process_ref: Assertion failed; expected="float", value={}'.format(
                        value
                    )
                )
        elif element.element_payload[0] == TYPE_ENUM_STR:
            if not isinstance(value, str):
                raise Exception(
                    '_process_ref: Assertion failed; expected="str", value={}'.format(
                        value
                    )
                )

        return value

    def _process_element(
        self, element
    ):  # type: (ExpressionElement) -> int | bool | float | str
        if isinstance(element, ExpressionLiteral):
            return self._process_literal(element)
        if isinstance(element, ExpressionReference):
            return self._process_ref(element)
        if isinstance(element, ExpressionSelector):
            return self.interact.selector_func()(element.element_payload)
        if isinstance(element, ExpressionScore):
            return self.interact.score_func()(
                element.element_payload[0],
                element.element_payload[1],
            )
        if isinstance(element, ExpressionFunction):
            if element.element_payload[0] not in self.builtins:
                raise Exception(
                    "Unknown function {} is called".format(
                        json.dumps(element.element_payload[0], ensure_ascii=False)
                    )
                )
            else:
                func = self.builtins[element.element_payload[0]]
                args = [self._process_element(i) for i in element.element_payload[1]]
                return func(*args)
        if isinstance(element, ExpressionTimes):
            temp = self._process_element(element.element_payload[0])
            for i in element.element_payload[1:]:
                temp *= self._process_element(i)  # type: ignore
            return temp
        if isinstance(element, ExpressionDivide):
            temp = self._process_element(element.element_payload[0])
            for i in element.element_payload[1:]:
                temp /= self._process_element(i)  # type: ignore
            return temp
        if isinstance(element, ExpressionAdd):
            temp = self._process_element(element.element_payload[0])
            for i in element.element_payload[1:]:
                temp += self._process_element(i)  # type: ignore
            return temp
        if isinstance(element, ExpressionRemove):
            temp = self._process_element(element.element_payload[0])
            for i in element.element_payload[1:]:
                temp -= self._process_element(i)  # type: ignore
            return temp
        if isinstance(element, ExpressionGreaterThan):
            left = self._process_element(element.element_payload[0])
            right = self._process_element(element.element_payload[1])
            return left > right  # type: ignore
        if isinstance(element, ExpressionLessThan):
            left = self._process_element(element.element_payload[0])
            right = self._process_element(element.element_payload[1])
            return left < right  # type: ignore
        if isinstance(element, ExpressionGreaterEqual):
            left = self._process_element(element.element_payload[0])
            right = self._process_element(element.element_payload[1])
            return left >= right  # type: ignore
        if isinstance(element, ExpressionLessEqual):
            left = self._process_element(element.element_payload[0])
            right = self._process_element(element.element_payload[1])
            return left <= right  # type: ignore
        if isinstance(element, ExpressionEqual):
            left = self._process_element(element.element_payload[0])
            right = self._process_element(element.element_payload[1])
            return left == right  # type: ignore
        if isinstance(element, ExpressionNotEqual):
            left = self._process_element(element.element_payload[0])
            right = self._process_element(element.element_payload[1])
            return left != right  # type: ignore
        if isinstance(element, ExpressionAnd):
            temp = self._process_element(element.element_payload[0])
            for i in element.element_payload[1:]:
                temp = temp and self._process_element(i)
            return temp
        if isinstance(element, ExpressionOr):
            temp = self._process_element(element.element_payload[0])
            for i in element.element_payload[1:]:
                temp = temp or self._process_element(i)
            return temp
        if isinstance(element, ExpressionIn):
            left = self._process_element(element.element_payload[0])
            right = self._process_element(element.element_payload[1])
            return left in right  # type: ignore
        if isinstance(element, ExpressionInverse):
            value = self._process_element(element.element_payload[0])
            return not value  # type: ignore
        if isinstance(element, ExpressionCombine):
            return self._process_element(element.element_payload[0])
        raise Exception(
            "_process_element: Unknown element is given; element={}".format(element)
        )

    def _process_block(self, code_block):  # type: (OpcodeBase) -> bool
        if isinstance(code_block, OpcodeAssign):
            name = code_block.opcode_payload[0]
            value = self._process_element(code_block.opcode_payload[1])
            self._variables[name] = value
            return False
        if isinstance(code_block, OpcodeExpression):
            self._return = self._process_element(code_block.opcode_payload)
            return False
        if isinstance(code_block, OpcodeReturn):
            self._return = self._process_element(code_block.opcode_payload)
            return True

        if isinstance(code_block, OpcodeCondition):
            for i in code_block.opcode_payload:
                cond = False

                if i.condition is None:
                    cond = True
                else:
                    try:
                        if self._process_element(i.condition):
                            cond = True
                    except Exception as e:
                        self._fast_condition_panic(i, -1, str(e))
                        raise Exception("unreachable")

                if cond:
                    for ind, val in enumerate(i.code_block):
                        try:
                            if self._process_block(val):
                                return True
                        except Exception as e:
                            self._fast_condition_panic(i, ind, str(e))
                            raise Exception("unreachable")
                    break
            return False

        return False

    def running(self):  # type: () -> int | bool | float | str
        self._variables = {}
        self._return = None

        for i in self.code_block:
            try:
                if self._process_block(i):
                    break
            except Exception as e:
                self._fast_normal_panic(i, str(e))
                raise Exception("unreachable")

        if self._return is None:
            raise Exception("Runtime Error: No return value after running the code")
        return self._return
