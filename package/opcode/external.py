TYPE_CHECKING = False
if TYPE_CHECKING:
    from typing import Any, Callable

import json


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


class BuiltInFunction:
    static = {}  # type: dict[str, Callable[..., int | bool | float | str]]
    dynamic = {}  # type: dict[str, Callable[..., int | bool | float | str]]

    def __init__(
        self,
        static={},  # type: dict[str, Callable[..., int | bool | float | str]]
        dynamic={},  # type: dict[str, Callable[..., int | bool | float | str]]
    ):  # type: (...) -> None
        self.static = static if len(static) > 0 else {}
        self.dynamic = dynamic if len(dynamic) > 0 else {}

    def _int(self, value):  # type: (Any) -> int
        return int(value)

    def _bool(self, value):  # type: (Any) -> bool
        return bool(value)

    def _float(self, value):  # type: (Any) -> float
        return float(value)

    def _str(self, value):  # type: (Any) -> str
        return str(value)

    def get_func(
        self, func_name
    ):  # type: (str) -> Callable[..., int | bool | float | str]
        if func_name == "int":
            return BuiltInFunction()._int
        if func_name == "bool":
            return BuiltInFunction()._bool
        if func_name == "float":
            return BuiltInFunction()._float
        if func_name == "str":
            return BuiltInFunction()._str

        if func_name in self.static:
            return self.static[func_name]
        if func_name in self.dynamic:
            return self.dynamic[func_name]

        raise Exception(
            "get_func: Unknown function {} is called".format(
                json.dumps(func_name, ensure_ascii=False)
            )
        )
