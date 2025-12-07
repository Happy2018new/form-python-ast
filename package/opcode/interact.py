TYPE_CHECKING = False
if TYPE_CHECKING:
    from typing import Callable


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
