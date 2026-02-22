# 目录
- [目录](#目录)
- [概述](#概述)
- [目的](#目的)
  - [综述](#综述)
  - [例子](#例子)
  - [结论](#结论)
- [编程语法](#编程语法)
- [快速上手](#快速上手)
- [注意事项](#注意事项)
- [可选依赖库](#可选依赖库)
- [性能](#性能)
  - [概述](#概述-1)
  - [测试用例一](#测试用例一)
  - [测试用例二](#测试用例二)
  - [测试用例三](#测试用例三)
  - [测试用例四](#测试用例四)
  - [测试用例五](#测试用例五)





# 概述
**Form Python AST** 是基于纯 **Python** 开发的 **AST** 抽象语法树解析器。<br/>
它在形式上定义了一种脚本语言，并提供了解析源代码、编译（为抽象语法树）和运行它的功能。





# 目的
## 综述
在 **Minecraft** 基岩版中，人们通过[文本组件](https://zh.minecraft.wiki/w/%E6%96%87%E6%9C%AC%E7%BB%84%E4%BB%B6#%E5%9F%BA%E5%B2%A9%E7%89%88)来显示标题文本和聊天栏信息。<br/>
文本组件是由 `rawtext` 包裹的列表，目前被广泛用于 `titleraw` 和 `tellraw` 命令。

在基岩版中，文本组件可以用于翻译本地化键名、解析实体名和分数。<br/>
在实践中，它也具有一定的条件判断功能，从而使得单命令方块彩虹条等实践成为现实。

然而，原有的条件判断不是被特别设计的，它更像是一个特性。<br/>
因此，通过利用该特性来处理文本显示实际上并不方便。

具体来说，文本组件在单个条件判断的块中，它只能支持有限次条件测试。<br/>
对于更多的条件测试，则必须通过嵌套文本组件，或展平（平铺）多个条件判断块。



## 例子
例如，下方的这个文本组件用于补全分数的前导零，<br>
并且只会处理具有标签 **square:helper** 的实体。

保证该实体只有 `1` 个，并且其在 `square` 上的分数是非负整数。<br/>
那么，它会这样处理该实体在 `square` 的分数，然后把处理的结果给显示出来。
- 233333 => 233333
- 23333 => 023333
- 2333 => 002333
- 233 => 000233
- 23 => 000023
- 2 => 000002

下面是对应的 **JSON** 文本组件。
```json
{
    "translate": "%%5",
    "with": {
        "rawtext": [
            {
                "selector": "@e[tag=square:helper,scores={square=10000..99999}]"
            },
            {
                "selector": "@e[tag=square:helper,scores={square=!..999,square=!100000..}]"
            },
            {
                "selector": "@e[tag=square:helper,scores={square=!..99,square=!100000..}]"
            },
            {
                "selector": "@e[tag=square:helper,scores={square=..999999}]"
            },
            {
                "rawtext": [
                    {
                        "text": "0"
                    },
                    {
                        "score": {
                            "objective": "square",
                            "name": "@e[tag=square:helper]"
                        }
                    }
                ]
            },
            {
                "rawtext": [
                    {
                        "text": "00"
                    },
                    {
                        "score": {
                            "objective": "square",
                            "name": "@e[tag=square:helper]"
                        }
                    }
                ]
            },
            {
                "rawtext": [
                    {
                        "text": "000"
                    },
                    {
                        "score": {
                            "objective": "square",
                            "name": "@e[tag=square:helper]"
                        }
                    }
                ]
            },
            {
                "translate": "%%3",
                "with": {
                    "rawtext": [
                        {
                            "selector": "@e[tag=square:helper,scores={square=10..99}]"
                        },
                        {
                            "selector": "@e[tag=square:helper,scores={square=1..99}]"
                        },
                        {
                            "rawtext": [
                                {
                                    "text": "0000"
                                },
                                {
                                    "score": {
                                        "objective": "square",
                                        "name": "@e[tag=square:helper]"
                                    }
                                }
                            ]
                        },
                        {
                            "rawtext": [
                                {
                                    "text": "00000"
                                },
                                {
                                    "score": {
                                        "objective": "square",
                                        "name": "@e[tag=square:helper]"
                                    }
                                }
                            ]
                        },
                        {
                            "rawtext": [
                                {
                                    "score": {
                                        "objective": "square",
                                        "name": "@e[tag=square:helper]"
                                    }
                                }
                            ]
                        }
                    ]
                }
            }
        ]
    }
}
```

很显然这是非常复杂的写法，并且非常难以阅读。<br/>
然而，上面的逻辑实际上可以被简化为这样的伪代码。

```python
if {func, game.has_tag('@s', 'square:helper')}:
    number = {score, '@s', 'square'}
    if number >= 100000:
        return str(number)
    elif number >= 10000:
        return '0' + str(number)
    elif number >= 1000:
        return '00' + str(number)
    elif number >= 100:
        return '000' + str(number)
    elif number >= 10:
        return '0000' + str(number)
    elif number >= 0:
        return '00000' + str(number)
    fi
fi
```

另外，如果你有一些数学头脑，<br/>
那么它还可以被继续简化为下面的形式。
```python
if {func, game.has_tag('@s', 'square:helper')}:
    number = {score, '@s', 'square'}
    if number > 0:
        log_ans = {func, math.log(number, 10)}
        log_ans = int(log_ans)
        return '0'*(5-log_ans) + str(number)
    fi
fi

return '000000'
```



## 结论
基于上面给出的例子，我们可以很明显的看出文本组件的局限性。<br/>
因此，本项目希望提供一种方式，摆脱文本组件的复杂写法。<br/>
即，通过提供一种具备可编程性的编程语言来替代原生的文本组件。





# 编程语法
- [概述](./docs/overview.md)
- [基本数据类型](./docs/data_type.md)
- [运算](./docs/compute.md)
- [与游戏进行交互、调用函数](./docs/external.md)
- [表达式、括号和强制类型转换](./docs/expression.md)
- [语句](./docs/statement.md)
- [教程](./docs/tutorial.md)





# 快速上手
使用版本至少达到 **2.7** 的 **Python** 运行下面的代码。
```python
# -*- coding: utf-8 -*-

import package

code = """
repeat = 6
total = 2*repeat-1

for i, repeat:
    star = 2*i + 1
    space = int((total-star)/2)
    line = ' '*space + '*'*star + ' '*space
    {func, print(line)}
rof

for i, repeat-1:
    star = 2*(repeat-(i+1)) - 1
    space = int((total-star)/2)
    line = ' '*space + '*'*star + ' '*space
    {func, print(line)}
rof

return 'SUCCESS'
"""


def print_func(value):  # type: (...) -> int
    print(value)
    return 0


try:
    parser = package.CodeParser(code).parse()
    builtins = package.BuiltInFunction(static={"print": print_func})
    runner = package.CodeRunner(parser.code_block)
    print(runner.running(builtins=builtins))
except Exception as e:
    print(e)
```

如果一切工作正常，您的控制台将打印下面的行。
```python
     *     
    ***    
   *****   
  *******  
 ********* 
***********
 ********* 
  *******  
   *****   
    ***    
     *     
SUCCESS
```

这一部分指定了要让该编程语言运行的代码。
```python
code = """
repeat = 6
total = 2*repeat-1

for i, repeat:
    star = 2*i + 1
    space = int((total-star)/2)
    line = ' '*space + '*'*star + ' '*space
    {func, print(line)}
rof

for i, repeat-1:
    star = 2*(repeat-(i+1)) - 1
    space = int((total-star)/2)
    line = ' '*space + '*'*star + ' '*space
    {func, print(line)}
rof

return 'SUCCESS'
"""
```

您可以修改它以让该编程语言运行其他代码。

另，因本项目有着详尽的注释，故本处不再描述您如何设置游戏交互相关的函数。<br/>
这意味着您更被推荐通过阅读注释来自行探索本编程语言所具有的其他细节。





# 注意事项
如果您要在主要版本小于 3 的 **Python** 上使用该库，请确保您已经执行了下面的代码。
```python
import sys

sys = reload(sys)
sys.setdefaultencoding("utf-8")
```
这意味着它会将默认编码格式从 `ascii` 切换为 `utf-8`，从而可以兼容中文等字符。





# 可选依赖库
您可以通过使用 [optional](./optional) 中的代码来为该编程语言的使用者提供更多的内建函数。<br/>
应说明的是，正如该模块的名字一样，这意味着该模块是可选的，即编程语言并没有内置它们——决定权在你。

下面（或[此处](./docs/optional.txt)）列出了该模块已经实现了的扩展函数。<br/>
它在理论上应覆盖了玩家在游戏中的大多数场景。

- 基本的，操作底层 **Python** 对象的能力
- 高级的，通过反射来操作底层对象的能力
- 针对切片（列表）的支持
- 针对映射（字典、有序字典）的支持
- 针对元组的支持
- 针对集合的支持
- 针对字符串的拓展函数
- 针对 **UUID** 的支持
- 基本的，时间相关的操作
- 数学计算
- 随机数生成
- **JSON** 序列化和反序列化
- 二进制编码
- 高级的，日期相关的操作
- **Base64** 编码





# 性能
## 概述
下方所有测试都是在该中央处理器搭载的个人笔记本电脑进行的。<br/>
并且，所有数据都最多精确到小数点后两位，并采用四舍五入处理。

```
Intel(R) Core(TM) i7-14650HX

基准速度: 2.20 GHz
插槽: 1
内核: 16
逻辑处理器: 24
虚拟化: 已启用

L1 缓存: 1.4 MB
L2 缓存: 24.0 MB
L3 缓存: 30.0 MB
```



## 测试用例一
```python
1
```

| 解释器      | 0.05s 内解析次数 | 0.05s 内运行次数 | 1s 内运行次数 | 单次运行的操作次数（估计） | 操作次数/秒 |
| ----------- | ---------------- | ---------------- | ------------- | -------------------------- | ----------- |
| Python 3.14 | 3239.32          | 101956.03        | 2039120.6     | 1.0                        | 2.04 M/s    |
| Python 2.7  | 1536.57          | 38390.66         | 767813.2      | 1.0                        | 0.77 M/s    |
| PyPy 2.7    | 12500.01         | 1620220.37       | 32404407.4    | 1.0                        | 32.40 M/s   |



## 测试用例二
```python
1+1
```

| 解释器      | 0.05s 内解析次数 | 0.05s 内运行次数 | 1s 内运行次数 | 单次运行的操作次数（估计） | 操作次数/秒 |
| ----------- | ---------------- | ---------------- | ------------- | -------------------------- | ----------- |
| Python 3.14 | 2208.50          | 65268.65         | 1305373.0     | 1.0                        | 1.31 M/s    |
| Python 2.7  | 1112.10          | 25278.06         | 505561.2      | 1.0                        | 0.51 M/s    |
| PyPy 2.7    | 9433.96          | 760571.96        | 15211439.2    | 1.0                        | 15.21 M/s   |



## 测试用例三
```python
total=0
for i, 100:
    total=total+i
rof
return total
```

| 解释器      | 0.05s 内解析次数 | 0.05s 内运行次数 | 1s 内运行次数 | 单次运行的操作次数（估计） | 操作次数/秒 |
| ----------- | ---------------- | ---------------- | ------------- | -------------------------- | ----------- |
| Python 3.14 | 432.43           | 731.09           | 14621.8       | 102.0                      | 1.49 M/s    |
| Python 2.7  | 243.88           | 327.35           | 6547.0        | 102.0                      | 0.67 M/s    |
| PyPy 2.7    | 3846.15          | 6823.70          | 136474.0      | 102.0                      | 13.92 M/s   |



## 测试用例四
```python
r=15
a=0
b=1
total=0

for _, r*2:
    temp = a
    a = b
    b = temp + b
    total = total + a
rof

return total
```

| 解释器      | 0.05s 内解析次数 | 0.05s 内运行次数 | 1s 内运行次数 | 单次运行的操作次数（估计） | 操作次数/秒 |
| ----------- | ---------------- | ---------------- | ------------- | -------------------------- | ----------- |
| Python 3.14 | 179.56           | 861.49           | 17229.8       | 126.0                      | 2.17 M/s    |
| Python 2.7  | 96.55            | 378.62           | 7572.4        | 126.0                      | 0.95 M/s    |
| PyPy 2.7    | 1947.04          | 8198.33          | 163966.6      | 126.0                      | 20.66 M/s   |



## 测试用例五
```python
repeat = 6
star = -1
result = ''

for _, repeat:
    star = star + 2
    line = 'say ' + '*'*star
    result = result + line + '\n'
rof

for _, repeat-1:
    star = star - 2
    line = 'say ' + '*'*star
    result = result + line + '\n'
rof

return result
```

| 解释器      | 0.05s 内解析次数 | 0.05s 内运行次数 | 1s 内运行次数 | 单次运行的操作次数（估计） | 操作次数/秒 |
| ----------- | ---------------- | ---------------- | ------------- | -------------------------- | ----------- |
| Python 3.14 | 119.54           | 1653.85          | 33077.0       | 43.5                       | 1.44 M/s    |
| Python 2.7  | 63.26            | 712.05           | 14241.0       | 43.5                       | 0.62 M/s    |
| PyPy 2.7    | 9505.70          | 14328.29         | 286565.8      | 43.5                       | 12.47 M/s   |