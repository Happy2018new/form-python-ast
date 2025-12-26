# 目录
- [目录](#目录)
- [概述](#概述)
- [目的](#目的)
  - [综述](#综述)
  - [例子](#例子)
  - [结论](#结论)
- [编程语法](#编程语法)
  - [概述](#概述-1)
  - [基本数据类型](#基本数据类型)
  - [运算](#运算)
  - [与游戏进行交互](#与游戏进行交互)
  - [表达式和括号](#表达式和括号)





# 概述
**Form Python AST** 是基于纯 **Python** 开发的 **AST** 抽象语法树解析器。<br/>
它在形式上定义了一种新的编程语言，并提供了相应的源代码解析、编译和运行的功能。





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
    elif number >= 1:
        return '00000' + str(number)
    fi
fi

return '000000'
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
## 概述
目前支持的数据类型如下。
- 整数
- 布尔值
- 浮点数
- 字符串

目前支持的基本操作如下。
- 表达式求值
- 变量赋值
- 代码返回值

支持的代码块分别如下。
- 条件代码块
- 循环代码块



## 基本数据类型
另见 [data_type.md](./docs/data_type.md)



## 运算
另见 [compute.md](./docs/compute.md)



## 与游戏进行交互
另见 [external.md](./docs/external.md)



## 表达式和括号
另见 [expression.md](./docs/expression.md)