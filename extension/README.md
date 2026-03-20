# Form Python AST VS Code Extension

这个扩展用于你的自定义语言（基于 `docs` 中定义的语法）提供：
- 语法高亮
- 代码片段
- 代码补全（关键字、语句模板、可选库 API）
- 语法诊断（基础）
- 悬浮文档提示（Hover）
- 文档格式化（Format Document）

## 1. 功能说明

### 语法高亮覆盖
- 控制关键字：`if` `elif` `else` `fi` `for` `continue` `break` `rof` `return`
- 逻辑关键字：`and` `or` `not` `in`
- 类型关键字：`int` `bool` `float` `str`
- 布尔常量：`True` `False`
- 外部语句：`{selector, ...}` `{score, ...}` `{command, ...}` `{ref, ...}` `{func, ...}`
- 字符串（单引号）和转义字符
- 数字、运算符、括号和标点
- 点调用形式的函数名（例如 `math.sqrt`）

### 代码补全覆盖
- 关键字补全
- 语法模板补全：
  - `if..fi`
  - `if..else..fi`
  - `if..elif..else..fi`
  - `for..rof`
  - `{selector}` `{score}` `{command}` `{ref}` `{func}`
- 可选库函数补全（来自 `docs/optional.txt`），例如：
  - `math.*`
  - `strings.*`
  - `json.*`
  - `random.*`
  - `datetime_*.*`
  - `base64.*`

### {func, xxx} 函数签名
- 扩展内置了 optional 常用函数补全与签名兜底（不依赖工作区中是否存在 `optional` 目录）
- 当工作区存在 `optional/lib_*.py` 时，扩展还会自动解析其中的 `funcs["module.name"] = ...` 映射以提升签名精度
- 对于 `lambda` 和 `self.method` 两类定义，会提取参数列表并展示签名
- 在 `{func, xxx(...)}` 里输入 `(` 或 `,` 时会弹出 Signature Help
- 补全列表也会展示函数签名（例如 `math.log(x, base=math.e)`）
- 鼠标悬停在 `{func, xxx}` 的 `xxx` 上时，会显示详细信息：签名、参数列表与函数说明

### 语法诊断（基础）
- 检查 `if/fi`、`for/rof` 是否成对出现
- 检查 `elif`、`else` 是否在合法的 `if` 代码块内
- 检查同一个 `if` 中是否重复出现 `else`
- 检查 `if`、`elif`、`else`、`for` 语句是否以 `:` 结尾

### 悬浮文档（Hover）
将鼠标悬停在关键字或外部语句关键字上时，会显示简短语法提示。

### 文档格式化
支持 VS Code 的 `Format Document`：
- 自动根据 `if/elif/else/fi` 和 `for/rof` 调整缩进
- 自动使用当前编辑器的缩进选项（空格或 Tab）

## 2. 文件扩展名

该扩展默认识别以下文件扩展名：
- `.fpa`
- `.fpyast`
- `.formast`

如果你希望使用其他后缀，可以修改 `package.json` 的 `contributes.languages[0].extensions`。

## 3. 本地运行（调试）

在本目录执行：

```bash
npm install
npm run compile
```

然后在 VS Code 中按 `F5` 启动 Extension Development Host。

在新窗口里新建一个 `.fpa` 文件，输入示例代码验证高亮和补全：

```python
a = 1
if a > 0:
    line = 'say hello'
    {command, line}
else:
    return False
fi
```

你也可以继续验证：
- 把 `fi` 删掉，检查是否出现诊断错误提示
- 把鼠标悬停在 `selector` 或 `elif` 上，检查 Hover
- 执行 `Format Document`，检查缩进是否自动整理

## 4. 打包安装 VSIX

先安装打包工具：

```bash
npm install -g @vscode/vsce
```

在扩展目录执行：

```bash
vsce package
```

会生成 `.vsix` 文件。然后在 VS Code 中执行：
- `Extensions: Install from VSIX...`

选择该 `.vsix` 即可安装。

## 5. 目录结构

```text
form-python-ast-vscode-extension/
  .gitignore
  language-configuration.json
  package.json
  tsconfig.json
  README.md
  src/
    extension.ts
  syntaxes/
    form-python-ast.tmLanguage.json
  snippets/
    form-python-ast.code-snippets
```

## 6. 可继续增强的点

- 增加语法错误诊断（Diagnostics）
- 增加 Hover 文档提示
- 增加定义跳转（Go to Definition）
- 增加语义高亮（Semantic Tokens）
- 增加更严格的语法规则校验（例如变量命名、外部语句参数个数）

如果你需要，我可以下一步继续把“语法检查 + 实时报错提示”也补齐成一个完整的语言服务版本。
