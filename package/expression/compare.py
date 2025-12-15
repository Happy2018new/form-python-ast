from .define import (
    ExpressionElement,
    ELEMENT_ID_EQUAL,
    ELEMENT_ID_LESS_THAN,
    ELEMENT_ID_GREATER_THAN,
    ELEMENT_ID_LESS_EQUAL,
    ELEMENT_ID_GREATER_EQUAL,
    ELEMENT_ID_NOT_EQUAL,
    ELEMENT_ID_AND,
    ELEMENT_ID_OR,
    ELEMENT_ID_IN,
    ELEMENT_ID_INVERSE,
)


class ExpressionOperator(ExpressionElement):
    element_id = 0  # type: int
    element_payload = []  # type: list[ExpressionElement]

    def __init__(self, element_payload=[]):  # type: (list[ExpressionElement]) -> None
        self.element_id = 0
        self.element_payload = element_payload if len(element_payload) > 0 else []


class ExpressionGreaterThan(ExpressionOperator):
    element_id = 0  # type: int
    element_payload = []  # type: list[ExpressionElement]

    def __init__(self, element_payload):  # type: (list[ExpressionElement]) -> None
        if len(element_payload) != 2:
            raise Exception(
                'ExpressionGreaterThan/__init__: Only 2 parameters are accepted for operator ">"; element_payload={}'.format(
                    element_payload
                )
            )
        ExpressionOperator.__init__(self, element_payload)
        self.element_id = ELEMENT_ID_GREATER_THAN


class ExpressionLessThan(ExpressionOperator):
    element_id = 0  # type: int
    element_payload = []  # type: list[ExpressionElement]

    def __init__(self, element_payload):  # type: (list[ExpressionElement]) -> None
        if len(element_payload) != 2:
            raise Exception(
                'ExpressionLessThan/__init__: Only 2 parameters are accepted for operator "<"; element_payload={}'.format(
                    element_payload
                )
            )
        ExpressionOperator.__init__(self, element_payload)
        self.element_id = ELEMENT_ID_LESS_THAN


class ExpressionGreaterEqual(ExpressionOperator):
    element_id = 0  # type: int
    element_payload = []  # type: list[ExpressionElement]

    def __init__(self, element_payload):  # type: (list[ExpressionElement]) -> None
        if len(element_payload) != 2:
            raise Exception(
                'ExpressionGreaterEqual/__init__: Only 2 parameters are accepted for operator ">="; element_payload={}'.format(
                    element_payload
                )
            )
        ExpressionOperator.__init__(self, element_payload)
        self.element_id = ELEMENT_ID_GREATER_EQUAL


class ExpressionLessEqual(ExpressionOperator):
    element_id = 0  # type: int
    element_payload = []  # type: list[ExpressionElement]

    def __init__(self, element_payload):  # type: (list[ExpressionElement]) -> None
        if len(element_payload) != 2:
            raise Exception(
                'ExpressionLessEqual/__init__: Only 2 parameters are accepted for operator "<="; element_payload={}'.format(
                    element_payload
                )
            )
        ExpressionOperator.__init__(self, element_payload)
        self.element_id = ELEMENT_ID_LESS_EQUAL


class ExpressionEqual(ExpressionOperator):
    element_id = 0  # type: int
    element_payload = []  # type: list[ExpressionElement]

    def __init__(self, element_payload):  # type: (list[ExpressionElement]) -> None
        if len(element_payload) != 2:
            raise Exception(
                'ExpressionEqual/__init__: Only 2 parameters are accepted for operator "=="; element_payload={}'.format(
                    element_payload
                )
            )
        ExpressionOperator.__init__(self, element_payload)
        self.element_id = ELEMENT_ID_EQUAL


class ExpressionNotEqual(ExpressionOperator):
    element_id = 0  # type: int
    element_payload = []  # type: list[ExpressionElement]

    def __init__(self, element_payload):  # type: (list[ExpressionElement]) -> None
        if len(element_payload) != 2:
            raise Exception(
                'ExpressionNotEqual/__init__: Only 2 parameters are accepted for operator "!="; element_payload={}'.format(
                    element_payload
                )
            )
        ExpressionOperator.__init__(self, element_payload)
        self.element_id = ELEMENT_ID_NOT_EQUAL


class ExpressionAnd(ExpressionOperator):
    element_id = 0  # type: int
    element_payload = []  # type: list[ExpressionElement]

    def __init__(self, element_payload=[]):  # type: (list[ExpressionElement]) -> None
        ExpressionOperator.__init__(self, element_payload)
        self.element_id = ELEMENT_ID_AND


class ExpressionOr(ExpressionOperator):
    element_id = 0  # type: int
    element_payload = []  # type: list[ExpressionElement]

    def __init__(self, element_payload=[]):  # type: (list[ExpressionElement]) -> None
        ExpressionOperator.__init__(self, element_payload)
        self.element_id = ELEMENT_ID_OR


class ExpressionIn(ExpressionOperator):
    element_id = 0  # type: int
    element_payload = []  # type: list[ExpressionElement]

    def __init__(self, element_payload):  # type: (list[ExpressionElement]) -> None
        if len(element_payload) != 2:
            raise Exception(
                'ExpressionIn/__init__: Only 2 parameters are accepted for operator "in"; element_payload={}'.format(
                    element_payload
                )
            )
        ExpressionOperator.__init__(self, element_payload)
        self.element_id = ELEMENT_ID_IN


class ExpressionInverse(ExpressionOperator):
    element_id = 0  # type: int
    element_payload = []  # type: list[ExpressionElement]

    def __init__(self, element_payload):  # type: (list[ExpressionElement]) -> None
        if len(element_payload) != 1:
            raise Exception(
                'ExpressionInverse/__init__: Only 1 parameter is accepted for operator "not"; element_payload={}'.format(
                    element_payload
                )
            )
        ExpressionOperator.__init__(self, element_payload)
        self.element_id = ELEMENT_ID_INVERSE
