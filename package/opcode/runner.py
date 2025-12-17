import json
from .external import GameInteract, BuiltInFunction
from .define import (
    ConditionWithCode,
    ForLoopCodeBlock,
    OpcodeBase,
    OpcodeAssign,
    OpcodeCondition,
    OpcodeForLoop,
    OpcodeContinue,
    OpcodeBreak,
    OpcodeDelete,
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
    ExpressionSelector,
    ExpressionScore,
    ExpressionCommand,
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

STATES_KEEP_RUNNING = 0
STATES_LOOP_CONTINUE = 1
STATES_LOOP_BREAK = 2
STATES_CODE_RETURN = 3

EMPTY_GAME_INTERACT = GameInteract()
EMPTY_BUILTIN_FUNCTION = BuiltInFunction()


class CodeBlockException(Exception):
    pass


class CodeRunner:
    code_block = []  # type: list[OpcodeBase]
    _interact = EMPTY_GAME_INTERACT  # type: GameInteract
    _builtins = EMPTY_BUILTIN_FUNCTION  # type: BuiltInFunction
    _variables = {}  # type: dict[str, int | bool | float | str]
    _return = None  # type: int | bool | float | str | None

    def __init__(
        self,
        code_block=[],  # type: list[OpcodeBase]
    ):  # type: (...) -> None
        self.code_block = code_block if len(code_block) > 0 else []
        self._interact = EMPTY_GAME_INTERACT
        self._builtins = EMPTY_BUILTIN_FUNCTION
        self._variables = {}
        self._return = None

    def _fast_normal_panic(self, code_block, err):  # type: (OpcodeBase, str) -> None
        raise Exception(
            "Runtime Error.\n\n- Error -\n  {}\n\n- Code -\n  {}".format(
                err, code_block.origin_line
            )
        )

    def _fast_condition_panic(
        self, condition, index=-1, err=""
    ):  # type: (ConditionWithCode, int, str) -> None
        prefix = "Runtime Error in Condition.\n\n- Error -\n  {}\n\n- Condition -\n  {}".format(
            err, condition.state_line
        )
        if index != -1:
            prefix += "\n\n- Code -\n  {}".format(
                condition.code_block[index].origin_line
            )
        raise CodeBlockException(prefix)

    def _fast_for_loop_panic(
        self, for_loop, index=-1, err=""
    ):  # type: (ForLoopCodeBlock, int, str) -> None
        prefix = "Runtime Error in For Loop.\n\n- Error -\n  {}\n\n- For Loop -\n  {}".format(
            err, for_loop.state_line
        )
        if index != -1:
            prefix += "\n\n- Code -\n  {}".format(
                for_loop.code_block[index].origin_line
            )
        raise CodeBlockException(prefix)

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
                'The index for "ref" statement must be int; index={}'.format(index)
            )
        value = self._interact.ref_func()(index)

        if element.element_payload[0] == TYPE_ENUM_BOOL:
            if not isinstance(value, bool):
                raise Exception(
                    "Assertion failed: Expect a bool but got {}".format(value)
                )
        elif element.element_payload[0] == TYPE_ENUM_INT:
            if not isinstance(value, int):
                raise Exception(
                    "Assertion failed: Expect an int but got {}".format(value)
                )
        elif element.element_payload[0] == TYPE_ENUM_FLOAT:
            if not isinstance(value, float):
                raise Exception(
                    "Assertion failed: Expect a float but got {}".format(value)
                )
        elif element.element_payload[0] == TYPE_ENUM_STR:
            if not isinstance(value, str):
                raise Exception(
                    "Assertion failed: Expect a str but got {}".format(value)
                )

        return value

    def _process_selector(self, element):  # type: (ExpressionSelector) -> str
        assert element.element_payload is not None
        value = self._process_element(element.element_payload)
        if not isinstance(value, str):
            raise Exception(
                'The argument for "selector" must be str; value={}'.format(value)
            )
        return self._interact.selector_func()(value)

    def _process_score(self, element):  # type: (ExpressionScore) -> int
        target = self._process_element(element.element_payload[0])
        if not isinstance(target, str):
            raise Exception(
                'The target argument for "score" must be str; target={}'.format(target)
            )
        scoreboard = self._process_element(element.element_payload[1])
        if not isinstance(scoreboard, str):
            raise Exception(
                'The scoreboard argument for "score" must be str; scoreboard={}'.format(
                    scoreboard
                )
            )
        return self._interact.score_func()(target, scoreboard)

    def _process_command(self, element):  # type: (ExpressionCommand) -> int
        assert element.element_payload is not None
        command = self._process_element(element.element_payload)
        if not isinstance(command, str):
            raise Exception(
                'The argument for "command" must be str; value={}'.format(command)
            )
        return self._interact.command_func()(command)

    def _process_element(
        self, element
    ):  # type: (ExpressionElement) -> int | bool | float | str
        if isinstance(element, ExpressionLiteral):
            return self._process_literal(element)
        if isinstance(element, ExpressionReference):
            return self._process_ref(element)
        if isinstance(element, ExpressionSelector):
            return self._process_selector(element)
        if isinstance(element, ExpressionScore):
            return self._process_score(element)
        if isinstance(element, ExpressionCommand):
            return self._process_command(element)
        if isinstance(element, ExpressionFunction):
            name = element.element_payload[0]
            func = self._builtins.get_func(name)
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
                if not temp:
                    return temp
            return temp
        if isinstance(element, ExpressionOr):
            temp = self._process_element(element.element_payload[0])
            for i in element.element_payload[1:]:
                temp = temp or self._process_element(i)
                if temp:
                    return temp
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
        raise Exception("Unknown element is given; element={}".format(element))

    def _process_block(self, code_block):  # type: (OpcodeBase) -> int
        if isinstance(code_block, OpcodeAssign):
            name = code_block.opcode_payload[0]
            value = self._process_element(code_block.opcode_payload[1])
            self._variables[name] = value
            return STATES_KEEP_RUNNING
        if isinstance(code_block, OpcodeContinue):
            return STATES_LOOP_CONTINUE
        if isinstance(code_block, OpcodeBreak):
            return STATES_LOOP_BREAK
        if isinstance(code_block, OpcodeExpression):
            self._return = self._process_element(code_block.opcode_payload)
            return STATES_KEEP_RUNNING
        if isinstance(code_block, OpcodeDelete):
            name = code_block.opcode_payload
            if name in self._variables:
                del self._variables[name]
            return STATES_KEEP_RUNNING
        if isinstance(code_block, OpcodeReturn):
            self._return = self._process_element(code_block.opcode_payload)
            return STATES_CODE_RETURN

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
                            command = self._process_block(val)
                            if command != STATES_KEEP_RUNNING:
                                return command
                        except Exception as e:
                            if isinstance(e, CodeBlockException):
                                raise e
                            else:
                                self._fast_condition_panic(i, ind, str(e))
                                raise Exception("unreachable")
                    break
            return STATES_KEEP_RUNNING

        if isinstance(code_block, OpcodeForLoop):
            assert code_block.opcode_payload is not None
            for_loop = code_block.opcode_payload
            variable = for_loop.variable

            try:
                repeat_times = self._process_element(for_loop.repeat_times)
            except Exception as e:
                self._fast_for_loop_panic(for_loop, -1, str(e))
                raise Exception("unreachable")
            if not isinstance(repeat_times, int) or isinstance(repeat_times, bool):
                self._fast_for_loop_panic(
                    for_loop, -1, "The repeat times of for loop must be int"
                )
                raise Exception("unreachable")

            for i in range(repeat_times):
                self._variables[variable] = i
                for ind, val in enumerate(for_loop.code_block):
                    try:
                        command = self._process_block(val)
                        if command == STATES_LOOP_CONTINUE:
                            break
                        if command == STATES_LOOP_BREAK:
                            return STATES_KEEP_RUNNING
                        if command == STATES_CODE_RETURN:
                            return STATES_CODE_RETURN
                    except Exception as e:
                        if isinstance(e, CodeBlockException):
                            raise e
                        else:
                            self._fast_for_loop_panic(for_loop, ind, str(e))
                            raise Exception("unreachable")
            return STATES_KEEP_RUNNING

        return STATES_KEEP_RUNNING

    def _running(
        self, require_return
    ):  # type: (bool) -> int | bool | float | str | None
        for i in self.code_block:
            try:
                command = self._process_block(i)
                if command == STATES_CODE_RETURN:
                    break
                if command != STATES_KEEP_RUNNING:
                    raise Exception(
                        "Continue and break statement only accepted under for loop code block"
                    )
            except Exception as e:
                if isinstance(e, CodeBlockException):
                    raise e
                else:
                    self._fast_normal_panic(i, str(e))
                    raise Exception("unreachable")

        if require_return and self._return is None:
            raise Exception("Runtime Error: No return value after running the code")
        return self._return

    def running(
        self,
        require_return=True,
        interact=EMPTY_GAME_INTERACT,
        builtins=EMPTY_BUILTIN_FUNCTION,
    ):  # type: (bool, GameInteract, BuiltInFunction) -> int | bool | float | str | None
        self._interact = interact
        self._builtins = builtins
        self._variables = {}
        self._return = None

        try:
            return self._running(require_return)
        finally:
            self._builtins = EMPTY_BUILTIN_FUNCTION
            self._interact = EMPTY_GAME_INTERACT
            self._variables = {}
            self._return = None
