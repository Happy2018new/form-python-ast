# -*- coding: utf-8 -*-
from __future__ import division

BYTECODE_LOAD_CONST = 0  # (0, CONST)
BYTECODE_LOAD_VALUE = 1  # (1, VAR_INDEX)
BYTECODE_STORE_VALUE = 2  # (2, VAR_INDEX)
BYTECODE_LOOP_JUMP = 3  # (3, VAR_INDEX, JUMP_TO)
BYTECODE_LOOP_POP = 4  # (4)
BYTECODE_DIRECT_JUMP = 5  # (5, JUMP_TO)
BYTECODE_FALSE_JUMP = 6  # (6, JUMP_TO)
BYTECODE_TRUE_JUMP = 7  # (7, JUMP_TO)
BYTECODE_HANDLE_COMPUTE = 8  # (8, POP_LEN, (+, -, *, /))
BYTECODE_HANDLE_COMPARE = 9  # (9, (==, !=, <, >, <=, >=))
BYTECODE_HANDLE_LOGIC_ANDOR = 10  # (10, (and, or)); NOTE: Copy the compare result
BYTECODE_HANDLE_LOGIC_INNOT = 11  # (11, (not, in))
BYTECODE_HANDLE_CAST = 12  # (12, (int, bool, float, str))
BYTECODE_HANDLE_FUNC = 13  # (13, POP_LEN, FUNC_NAME)
BYTECODE_HANDLE_INTERACT = 14  # (14, (command, score, selector)) or (14, ref, REF_TYPE)
BYTECODE_STORE_RETURN_VAL = 15  # (15)
BYTECODE_PROGRAM_STOP_RUN = 16  # (16)
BYTECODE_INTERNAL_PANIC = 17  # (17, ERROR)

COMPUTE_TYPE_ADD = 0
COMPUTE_TYPE_REMOVE = 1
COMPUTE_TYPE_TIMES = 2
COMPUTE_TYPE_DIVIDE = 3

COMPARE_TYPE_EQUAL = 0
COMPARE_TYPE_NOT_EQUAL = 1
COMPARE_TYPE_LESS_THAN = 2
COMPARE_TYPE_GREATER_THAN = 3
COMPARE_TYPE_LESS_EQUAL = 4
COMPARE_TYPE_GREATER_EQUAL = 5

LOGIC_ANDOR_TYPE_AND = 0
LOGIC_ANDOR_TYPE_OR = 1

LOGIC_INNOT_TYPE_NOT = 0
LOGIC_INNOT_TYPE_IN = 1

CAST_TYPE_INT = 0
CAST_TYPE_BOOL = 1
CAST_TYPE_FLOAT = 2
CAST_TYPE_STR = 3

INTERACT_TYPE_COMMAND = 0
INTERACT_TYPE_SCORE = 1
INTERACT_TYPE_SELECTOR = 2
INTERACT_TYPE_REF = 3

REF_TYPE_INT = 0
REF_TYPE_BOOL = 1
REF_TYPE_FLOAT = 2
REF_TYPE_STR = 3

CHECK_POINT_TYPE_NORMAL = 0
CHECK_POINT_TYPE_CONDITION = 1
CHECK_POINT_TYPE_FOR_LOOP = 2


class VariableMapping:
    _name_to_index = {}  # type: dict[str, int]
    _index_to_name = []  # type: list[str]

    def __init__(self):  # type: () -> None
        self._name_to_index = {}
        self._index_to_name = []

    def __repr__(self):  # type: () -> str
        return "VariableMapping(name_to_index={}, index_to_name={})".format(
            self._name_to_index, self._index_to_name
        )

    def variables_count(self):  # type: () -> int
        return len(self._index_to_name)

    def index_by_name(self, varname, readonly=False):  # type: (str, bool) -> int | None
        if varname in self._name_to_index:
            return self._name_to_index[varname]

        if not readonly:
            varindex = len(self._index_to_name)
            self._name_to_index[varname] = varindex
            self._index_to_name.append(varname)
            return varindex

        return None

    def name_by_index(self, varindex):  # type: (int) -> str
        if varindex < 0 or varindex >= len(self._index_to_name):
            raise IndexError(
                "name_by_index: Index out of range [{}] with length {}".format(
                    varindex, len(self._index_to_name)
                )
            )
        return self._index_to_name[varindex]


class CheckPoint:
    point_type = 0  # type: int
    start_pc = 0  # type: int
    end_pc = 0  # type: int
    payload = []  # type: list[str]

    def __init__(
        self,
        point_type,  # type: int
        start_pc,  # type: int
        end_pc,  # type: int
        payload,  # type: list[str]
    ):  # type: (...) -> None
        self.point_type = point_type
        self.start_pc = start_pc
        self.end_pc = end_pc
        self.payload = payload

    def __repr__(self):  # type: () -> str
        return "CheckPoint(point_type={}, start_pc={}, end_pc={}, payload={})".format(
            self.point_type, self.start_pc, self.end_pc, self.payload
        )
