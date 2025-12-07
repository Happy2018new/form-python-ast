from .define import (
    ExpressionElement,
    ExpressionOperator,
    ELEMENT_ID_ADD,
    ELEMENT_ID_REMOVE,
    ELEMENT_ID_TIMES,
    ELEMENT_ID_DIVIDE,
)


class ExpressionTimes(ExpressionOperator):
    element_id = ELEMENT_ID_TIMES  # type: int
    element_payload = []  # type: list[ExpressionElement]

    def __init__(self, element_payload=[]):  # type: (list[ExpressionElement]) -> None
        ExpressionOperator.__init__(self, element_payload)
        self.element_id = ELEMENT_ID_TIMES


class ExpressionDivide(ExpressionOperator):
    element_id = ELEMENT_ID_DIVIDE  # type: int
    element_payload = []  # type: list[ExpressionElement]

    def __init__(self, element_payload=[]):  # type: (list[ExpressionElement]) -> None
        ExpressionOperator.__init__(self, element_payload)
        self.element_id = ELEMENT_ID_DIVIDE


class ExpressionAdd(ExpressionOperator):
    element_id = ELEMENT_ID_ADD  # type: int
    element_payload = []  # type: list[ExpressionElement]

    def __init__(self, element_payload=[]):  # type: (list[ExpressionElement]) -> None
        ExpressionOperator.__init__(self, element_payload)
        self.element_id = ELEMENT_ID_ADD


class ExpressionRemove(ExpressionOperator):
    element_id = ELEMENT_ID_REMOVE  # type: int
    element_payload = []  # type: list[ExpressionElement]

    def __init__(self, element_payload=[]):  # type: (list[ExpressionElement]) -> None
        ExpressionOperator.__init__(self, element_payload)
        self.element_id = ELEMENT_ID_REMOVE
