# -*- coding: utf-8 -*-

TYPE_CHECKING = False
if TYPE_CHECKING:
    from typing import Callable

import random
from .object import ObjectManager


class Random:
    """
    Random 提供了随机数相关的内置函数
    """

    def __init__(self, manager):  # type: (ObjectManager) -> None
        """初始化并返回一个新的 Random

        Args:
            manager (ObjectManager):
                用于管理引用对象的对象管理器
        """
        self._manager = manager

    def sample(
        self, population_ptr, k, counts_ptr=None
    ):  # type: (int, int, int | None) -> int
        """
        sample chooses k unique random elements from a population sequence.

        Returns a new list containing elements from the population while
        leaving the original population unchanged. The resulting list is
        in selection order so that all sub-slices will also be valid random
        samples. This allows raffle winners (the sample) to be partitioned
        into grand prize and second place winners (the subslices).

        Members of the population need not be hashable or unique. If the
        population contains repeats, then each occurrence is a possible
        selection in the sample.

        Repeated elements can be specified one at a time or with the optional
        counts parameter. For example:
        ```
            sample(['red', 'blue'], counts=[4, 2], k=5)
        ```

        is equivalent to:
        ```
            sample(['red', 'red', 'red', 'red', 'blue', 'blue'], k=5)
        ```

        To choose a sample from a range of integers, use range() for the
        population argument. This is especially fast and space efficient
        for sampling from a large population:
        ```
            sample(range(10000000), 60)
        ```

        Args:
            population_ptr (int): The pointer points to the population sequence
            k (int): The number of unique elements to choose
            counts_ptr (int, optional):
                The pointer points to the counts sequence.
                If is is zero or None, then this field will not used.
                Defaults to None.

        Returns:
            int: The pointer points to the new list containing the chosen elements
        """
        if counts_ptr is None or counts_ptr == 0:
            return self._manager.ref(
                random.sample(self._manager.deref(population_ptr), k)
            )
        return self._manager.ref(
            random.sample(
                self._manager.deref(population_ptr),
                k,
                counts=self._manager.deref(counts_ptr),
            )
        )

    def shuffle(self, ptr):  # type: (int) -> bool
        """
        shuffle shuffles the given list in place,
        and always returns True.

        Args:
            ptr (int):
                The pointer points to the list to be shuffled

        Returns:
            bool: Always returns True
        """
        random.shuffle(self._manager.deref(ptr))
        return True

    def build_func(
        self,
        origin,  # type: dict[str, Callable[..., int | bool | float | str]]
    ):  # type: (...) -> None
        """
        build_func 构建 random 模块的内置函数，
        并将构建结果写入到传递的 origin 字典中

        Args:
            origin (dict[str, Callable[..., int | bool | float | str]]):
                用于存放所有内置函数的字典
        """
        funcs = {}  # type: dict[str, Callable[..., int | bool | float | str]]

        funcs["random.betavariate"] = lambda a, b: random.betavariate(a, b)
        funcs["random.choice"] = lambda ptr: self._manager.ref(
            random.choice(self._manager.deref(ptr))
        )
        funcs["random.expovariate"] = lambda lambd=1.0: random.expovariate(lambd)
        funcs["random.gammavariate"] = lambda alpha, beta: random.gammavariate(
            alpha, beta
        )
        funcs["random.gauss"] = lambda mu=0.0, sigma=1.0: random.gauss(mu, sigma)
        funcs["random.getrandbits"] = lambda k: random.getrandbits(k)
        funcs["random.lognormvariate"] = lambda mu, sigma: random.lognormvariate(
            mu, sigma
        )
        funcs["random.normalvariate"] = lambda mu=0.0, sigma=1.0: random.normalvariate(
            mu, sigma
        )
        funcs["random.paretovariate"] = lambda alpha: random.paretovariate(alpha)
        funcs["random.randint"] = lambda a, b: random.randint(a, b)
        funcs["random.random"] = lambda: random.random()
        funcs["random.randrange"] = lambda start, stop=None, step=1: random.randrange(
            start, stop, step
        )
        funcs["random.sample"] = self.sample
        funcs["random.shuffle"] = self.shuffle
        funcs["random.triangular"] = (
            lambda low=0.0, high=1.0, mode=None: random.triangular(low, high, mode)
        )
        funcs["random.uniform"] = lambda a, b: random.uniform(a, b)
        funcs["random.vonmisesvariate"] = lambda mu, kappa: random.vonmisesvariate(
            mu, kappa
        )
        funcs["random.weibullvariate"] = lambda alpha, beta: random.weibullvariate(
            alpha, beta
        )

        for key, value in funcs.items():
            origin[key] = value
