import * as vscode from "vscode";
import * as fs from "node:fs";
import * as path from "node:path";

const KEYWORDS = [
    "if",
    "elif",
    "else",
    "fi",
    "for",
    "continue",
    "break",
    "rof",
    "return",
    "and",
    "or",
    "not",
    "in",
    "True",
    "False",
    "int",
    "bool",
    "float",
    "str"
];

const EXTERNAL_STATEMENTS = ["selector", "score", "command", "ref", "func"];

let DISCOVERED_APIS: string[] = [];

interface FunctionSignature {
    label: string;
    parameters: string[];
    source: "workspace" | "builtin";
    sourceFile?: string;
    description?: string;
    returnType?: string;
}

interface MappingInfo {
    params: string[];
    description?: string;
    returnType?: string;
    rhs?: string;
}

const FUNCTION_SIGNATURES = new Map<string, FunctionSignature>();

function createSignature(
    name: string,
    params: string[],
    source: FunctionSignature["source"],
    sourceFile?: string,
    description?: string,
    returnType?: string
): FunctionSignature {
    return {
        label: `${name}(${params.join(", ")})`,
        parameters: params,
        source,
        sourceFile,
        description,
        returnType
    };
}

function normalizeParamList(raw: string): string[] {
    const cleaned = raw
        .replace(/#.*$/g, "")
        .replace(/\/\*.*?\*\//g, "")
        .trim();

    if (!cleaned) {
        return [];
    }

    return cleaned
        .split(",")
        .map((part) => part.trim())
        .filter((part) => part.length > 0)
        .map((part) => part.replace(/^\*\*?/, "").trim())
        .filter((part) => part !== "self");
}

interface MethodInfo {
    params: string[];
    description?: string;
    returnType?: string;
}

interface TypeCommentInfo {
    paramTypes: string[];
    returnType?: string;
}

interface DocstringTypeInfo {
    paramTypes: Map<string, string>;
    returnType?: string;
}

function splitTopLevelComma(text: string): string[] {
    const result: string[] = [];
    let current = "";
    let depth = 0;

    for (const ch of text) {
        if (ch === "(" || ch === "[" || ch === "{") {
            depth += 1;
            current += ch;
            continue;
        }
        if (ch === ")" || ch === "]" || ch === "}") {
            depth = Math.max(0, depth - 1);
            current += ch;
            continue;
        }
        if (ch === "," && depth === 0) {
            result.push(current.trim());
            current = "";
            continue;
        }
        current += ch;
    }

    if (current.trim().length > 0) {
        result.push(current.trim());
    }

    return result;
}

function parseTypeComment(defText: string): TypeCommentInfo | undefined {
    const match = defText.match(/#\s*type:\s*\(([\s\S]*?)\)\s*->\s*([^\n#]+)/);
    if (!match) {
        return undefined;
    }

    const paramsPart = match[1].trim();
    const returnType = match[2].trim();
    const paramTypes = paramsPart.length > 0 ? splitTopLevelComma(paramsPart) : [];

    return {
        paramTypes,
        returnType: returnType.length > 0 ? returnType : undefined
    };
}

function parseDocstringTypes(docText: string): DocstringTypeInfo {
    const paramTypes = new Map<string, string>();
    let returnType: string | undefined;

    const argsSectionMatch = docText.match(/(?:^|\n)\s*Args:\s*([\s\S]*?)(?:\n\s*(?:Raises|Returns|Examples|Notes|Attributes):|$)/i);
    if (argsSectionMatch) {
        const argsText = argsSectionMatch[1];
        const argRegex = /^\s*([A-Za-z_][A-Za-z0-9_]*)\s*\(([^)]+)\)\s*:/gm;
        for (const m of argsText.matchAll(argRegex)) {
            paramTypes.set(m[1], m[2].trim());
        }
    }

    const returnsSectionMatch = docText.match(/(?:^|\n)\s*Returns:\s*([\s\S]*?)(?:\n\s*(?:Raises|Args|Examples|Notes|Attributes):|$)/i);
    if (returnsSectionMatch) {
        const returnsText = returnsSectionMatch[1].trim();
        const firstTypedLine = returnsText.match(/^\s*([^:\n]+)\s*:/m);
        if (firstTypedLine) {
            returnType = firstTypedLine[1].trim();
        }
    }

    return { paramTypes, returnType };
}

function getParamBaseName(param: string): string {
    const eq = param.indexOf("=");
    const left = eq >= 0 ? param.slice(0, eq) : param;
    return left.replace(/^\*\*?/, "").trim();
}

function readLineAt(text: string, index: number): string {
    const lineStart = text.lastIndexOf("\n", Math.max(0, index - 1)) + 1;
    const lineEndCandidate = text.indexOf("\n", index);
    const lineEnd = lineEndCandidate >= 0 ? lineEndCandidate : text.length;
    return text.slice(lineStart, lineEnd);
}

function attachTypeToParam(param: string, typeText?: string): string {
    if (!typeText || typeText.trim().length === 0) {
        return param;
    }

    if (param.includes(":")) {
        return param;
    }

    const eq = param.indexOf("=");
    if (eq >= 0) {
        const left = param.slice(0, eq).trim();
        const right = param.slice(eq + 1).trim();
        return `${left}: ${typeText.trim()} = ${right}`;
    }

    return `${param.trim()}: ${typeText.trim()}`;
}

function cleanDocText(text: string): string {
    const normalized = text.replace(/\r/g, "").trim();

    // Keep only the leading summary block; cut structured sections aggressively.
    const sectionMarker =
        /(\b(args?|parameters?|returns?|raises?|examples?|notes?|attributes?)\s*:|\b参数\s*:|\b返回\s*:|\b异常\s*:)/i;
    const markerMatch = normalized.match(sectionMarker);
    const beforeSections = markerMatch
        ? normalized.slice(0, markerMatch.index ?? normalized.length)
        : normalized;

    const lines = beforeSections
        .split("\n")
        .map((line) => line.trim())
        .filter((line) => line.length > 0)
        .filter((line) => !line.startsWith("- "))
        .filter((line) => !line.startsWith("* "));

    if (lines.length === 0) {
        return "";
    }

    const compact = lines.join(" ").replace(/\s+/g, " ").trim();
    const sentenceMatch = compact.match(/^(.{0,160}?[。.!?])(?:\s|$)/);
    if (sentenceMatch) {
        return sentenceMatch[1].trim();
    }

    return compact.slice(0, 160).trim();
}

function humanizeName(name: string): string {
    return name.replace(/_/g, " ");
}

function getSpecificApiDescription(apiName: string): string | undefined {
    const exact = new Map<string, string>([
        ["math.sqrt", "返回 x 的平方根。"],
        ["math.trunc", "返回 x 的截断整数部分。"],
        ["math.sin", "返回 x 的正弦值（弧度）。"],
        ["math.cos", "返回 x 的余弦值（弧度）。"],
        ["math.tan", "返回 x 的正切值（弧度）。"],
        ["math.pow", "返回 x 的 y 次幂。"],
        ["math.powmod", "返回 (x ** y) % mod 的结果。"],
        ["math.log", "返回对数值，可指定底数。"],
        ["math.log10", "返回以 10 为底的对数。"],
        ["math.factorial", "返回 x 的阶乘。"],
        ["math.ceil", "返回不小于 x 的最小整数。"],
        ["math.floor", "返回不大于 x 的最大整数。"],
        ["math.round", "按指定位数对数值进行四舍五入。"],
        ["json.dumps", "将对象序列化为 JSON 字符串。"],
        ["json.loads", "将 JSON 字符串反序列化为对象。"],
        ["json.fast_dumps", "快速将对象序列化为 JSON 字符串。"],
        ["json.fast_loads", "快速将 JSON 字符串反序列化为对象。"],
        ["uuid.new", "创建并返回新的 UUID 对象引用。"],
        ["uuid.string", "返回 UUID 的字符串表示。"],
        ["uuid.hex", "返回 UUID 的十六进制字符串。"],
        ["time.time", "返回当前 Unix 时间戳（秒）。"],
        ["time.strftime", "按格式字符串格式化时间。"],
        ["time.strptime", "按格式将字符串解析为时间结构。"],
        ["strings.upper", "将字符串转换为大写。"],
        ["strings.lower", "将字符串转换为小写。"],
        ["strings.split", "按分隔符拆分字符串。"],
        ["strings.replace", "替换字符串中的子串并返回新字符串。"],
        ["strings.strip", "移除字符串两端空白字符。"],
        ["strings.find", "返回子串首次出现的位置，未找到返回 -1。"],
        ["strings.startswith", "判断字符串是否以指定前缀开头。"],
        ["strings.endswith", "判断字符串是否以指定后缀结尾。"],
        ["maps.keys", "返回映射中所有键的集合/序列引用。"],
        ["maps.values", "返回映射中所有值的集合/序列引用。"],
        ["maps.items", "返回映射中所有键值对的集合/序列引用。"],
        ["slices.sort", "对序列进行排序。"],
        ["slices.reverse", "反转序列元素顺序。"],
        ["slices.binsearch", "在有序序列中执行二分查找。"],
        ["object.ref", "为对象创建并返回托管引用。"],
        ["object.deref", "解引用指针并返回原始对象。"],
        ["object.release", "释放对象引用。"],
        ["object.is_ptr", "判断给定值是否为有效指针引用。"],
        ["object.is_none", "判断引用是否指向 None。"],
        ["reflect.call", "调用函数引用并返回结果。"],
        ["reflect.getattr", "读取对象属性并返回其值。"],
        ["reflect.setattr", "设置对象属性值。"],
        ["reflect.delattr", "删除对象属性。"],
        ["reflect.deepcopy", "深拷贝对象并返回新引用。"]
    ]);
    if (exact.has(apiName)) {
        return exact.get(apiName);
    }

    const [moduleName, fn = apiName] = apiName.split(".");
    const suffixRules: Array<[RegExp, string]> = [
        [/^(add|append|insert|union|concat)$/i, "执行添加/合并操作并返回结果。"],
        [/^(remove|del|delete|discard|pop|clear)$/i, "执行删除/清空操作并返回结果。"],
        [/^(greater|less|greater_equal|less_equal|equal|not_equal|exist|ptr_exist|isdisjoint|issubset|issuperset)$/i, "执行比较或关系判断并返回布尔结果。"],
        [/^(get|ptr_get|at|index|rindex|find|rfind)$/i, "读取并返回目标值或位置。"],
        [/^(set|ptr_set)$/i, "写入目标值并返回处理结果。"],
        [/^(length|count)$/i, "返回目标对象的长度。"],
        [/^(format|isoformat|ctime|asctime)$/i, "将目标值格式化为字符串。"],
        [/^(encode|decode|b16encode|b16decode|b32encode|b32decode|b64encode|b64decode|hexlify|a2b_hex|b2a_hex|a2b_base64|b2a_base64)$/i, "执行编码/解码转换并返回结果。"],
        [/^(max|min|sum)$/i, "执行聚合计算并返回结果。"],
        [/^(new|make|copy|deepcopy|cast)$/i, "创建或转换对象并返回结果。"],
        [/^(shuffle|sample|choice|randint|randrange|random|uniform|gauss|normalvariate)$/i, "执行随机计算并返回结果。"]
    ];

    for (const [rule, desc] of suffixRules) {
        if (rule.test(fn)) {
            return desc;
        }
    }

    if (moduleName === "datetime_date" || moduleName === "datetime_time" || moduleName === "datetime_datetime") {
        if (/^(year|month|day|hour|minute|second|microsecond|weekday|isoweekday|toordinal)$/i.test(fn)) {
            return "返回日期时间对象的对应字段值。";
        }
    }

    return undefined;
}

function inferDescriptionFromApiName(apiName: string): string {
    const specific = getSpecificApiDescription(apiName);
    if (specific) {
        return specific;
    }

    const [moduleName, funcName] = apiName.split(".");
    const fn = funcName ?? apiName;

    if (["new", "make"].includes(fn)) {
        return `创建 ${moduleName} 模块中的新对象。`;
    }
    if (fn === "cast") {
        return `将输入值转换为 ${moduleName} 模块期望的数据类型。`;
    }
    if (fn === "format") {
        return `将值格式化为可读字符串。`;
    }
    if (fn === "length") {
        return `返回目标对象的长度。`;
    }
    if (["max", "min", "sum"].includes(fn)) {
        return `执行 ${humanizeName(fn)} 计算并返回结果。`;
    }
    if (fn.startsWith("is") || fn.startsWith("has") || fn.startsWith("can")) {
        return `执行条件判断，返回布尔值结果。`;
    }
    if (fn.startsWith("get") || fn.startsWith("ptr_get")) {
        return `读取并返回目标值。`;
    }
    if (fn.startsWith("set") || fn.startsWith("ptr_set")) {
        return `写入目标值并返回处理结果。`;
    }
    if (fn.includes("equal") || fn.includes("less") || fn.includes("greater")) {
        return `执行比较运算并返回布尔值结果。`;
    }
    if (fn.includes("add") || fn.includes("append") || fn.includes("insert")) {
        return `执行添加操作并返回处理结果。`;
    }
    if (fn.includes("remove") || fn.includes("del") || fn.includes("pop") || fn.includes("discard")) {
        return `执行移除操作并返回处理结果。`;
    }

    return `调用 ${apiName} 执行对应操作。`;
}

function inferDescriptionFromRhs(apiName: string, rhs?: string): string {
    if (!rhs) {
        return inferDescriptionFromApiName(apiName);
    }

    const apiNameDescription = inferDescriptionFromApiName(apiName);
    const hasSpecificDescription = apiNameDescription !== `调用 ${apiName} 执行对应操作。`;

    const lambdaBodyMatch = rhs.match(/^lambda\s+[^:]*:\s*(.+)$/);
    if (lambdaBodyMatch) {
        const body = lambdaBodyMatch[1].trim();

        const binaryMatch = body.match(/^([A-Za-z_][A-Za-z0-9_]*)\s*(\+|\-|\*|\/|\/\/|%|\*\*|<<|>>|==|!=|<=|>=|<|>|&|\||\^)\s*([A-Za-z_][A-Za-z0-9_]*)$/);
        if (binaryMatch) {
            const opMap: Record<string, string> = {
                "+": "加法",
                "-": "减法",
                "*": "乘法",
                "/": "除法",
                "//": "整除",
                "%": "取模",
                "**": "幂运算",
                "<<": "左移",
                ">>": "右移",
                "==": "相等比较",
                "!=": "不等比较",
                "<=": "小于等于比较",
                ">=": "大于等于比较",
                "<": "小于比较",
                ">": "大于比较",
                "&": "按位与",
                "|": "按位或",
                "^": "按位异或"
            };
            return `对 ${binaryMatch[1]} 和 ${binaryMatch[3]} 执行${opMap[binaryMatch[2]] || "运算"}并返回结果。`;
        }

        const unaryBitNotMatch = body.match(/^~\s*([A-Za-z_][A-Za-z0-9_]*)$/);
        if (unaryBitNotMatch) {
            return `对 ${unaryBitNotMatch[1]} 执行按位取反并返回结果。`;
        }

        const callMatch = body.match(/^([A-Za-z_][A-Za-z0-9_.]*)\((.*)\)$/);
        if (callMatch) {
            if (hasSpecificDescription) {
                return apiNameDescription;
            }
            return `调用 ${callMatch[1]} 并返回结果。`;
        }

        const attrMatch = body.match(/^([A-Za-z_][A-Za-z0-9_.()]+)\.([A-Za-z_][A-Za-z0-9_]*)$/);
        if (attrMatch) {
            return `返回 ${attrMatch[1]} 的 ${attrMatch[2]} 属性值。`;
        }

        if (/^[A-Za-z_][A-Za-z0-9_.]*$/.test(body)) {
            return `返回 ${body}。`;
        }

        return `执行表达式 ${body} 并返回结果。`;
    }

    const selfMatch = rhs.match(/^self\.([A-Za-z_][A-Za-z0-9_]*)$/);
    if (selfMatch) {
        return `调用内部方法 ${selfMatch[1]} 处理并返回结果。`;
    }

    if (rhs.includes(" and ") || rhs.includes(" or ")) {
        return "执行逻辑组合运算并返回布尔值结果。";
    }

    if (rhs.includes("==") || rhs.includes("!=") || rhs.includes(">") || rhs.includes("<")) {
        return "执行比较运算并返回布尔值结果。";
    }

    return apiNameDescription;
}

function extractMethodSignatures(fileText: string): Map<string, MethodInfo> {
    const result = new Map<string, MethodInfo>();
    const regex = /^\s*def\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(([^)]*)\)\s*:/gm;

    for (const match of fileText.matchAll(regex)) {
        const methodName = match[1];
        const rawParams = match[2];
        const params = normalizeParamList(rawParams);
        const defLine = readLineAt(fileText, match.index ?? 0);
        const typeInfo = parseTypeComment(defLine);
        const typedParams = typeInfo
            ? params.map((param, idx) => attachTypeToParam(param, typeInfo.paramTypes[idx]))
            : params;

        let description: string | undefined;
        let docTypeInfo: DocstringTypeInfo | undefined;
        const bodyStart = match.index! + match[0].length;
        const bodySlice = fileText.slice(bodyStart, Math.min(fileText.length, bodyStart + 1000));
        const docMatch = bodySlice.match(/^\s*(?:"""([\s\S]*?)"""|'''([\s\S]*?)''')/m);
        if (docMatch) {
            const rawDoc = (docMatch[1] ?? docMatch[2] ?? "").trim();
            docTypeInfo = parseDocstringTypes(rawDoc);
            const cleaned = cleanDocText(rawDoc);
            description = cleaned.length > 0 ? cleaned : undefined;
        }

        const mergedParams = typedParams.map((param) => {
            if (param.includes(":")) {
                return param;
            }
            const baseName = getParamBaseName(param);
            return attachTypeToParam(param, docTypeInfo?.paramTypes.get(baseName));
        });

        const returnType = typeInfo?.returnType ?? docTypeInfo?.returnType;

        result.set(methodName, {
            params: mergedParams,
            description,
            returnType
        });
    }

    return result;
}

function tryExtractLambdaParams(expression: string): string[] | undefined {
    const lambdaMatch = expression.match(/^\s*lambda\s*([^:]*):/);
    if (!lambdaMatch) {
        return undefined;
    }
    return normalizeParamList(lambdaMatch[1]);
}

function isWrappedBySingleParentheses(expression: string): boolean {
    const trimmed = expression.trim();
    if (!trimmed.startsWith("(") || !trimmed.endsWith(")")) {
        return false;
    }

    let depth = 0;
    let inString = false;
    let escaped = false;

    for (let i = 0; i < trimmed.length; i++) {
        const ch = trimmed[i];

        if (inString) {
            if (escaped) {
                escaped = false;
                continue;
            }
            if (ch === "\\") {
                escaped = true;
                continue;
            }
            if (ch === "'") {
                inString = false;
            }
            continue;
        }

        if (ch === "'") {
            inString = true;
            continue;
        }

        if (ch === "(") {
            depth += 1;
            continue;
        }

        if (ch === ")") {
            depth -= 1;
            if (depth === 0 && i < trimmed.length - 1) {
                return false;
            }
        }
    }

    return depth === 0;
}

function normalizeMappingExpression(rhs: string): string {
    let expression = rhs.trim();
    while (isWrappedBySingleParentheses(expression)) {
        expression = expression.slice(1, -1).trim();
    }
    return expression;
}

function extractFuncMappings(
    fileText: string,
    methods: Map<string, MethodInfo>
): Map<string, MappingInfo> {
    const result = new Map<string, MappingInfo>();
    const headerRegex = /^\s*funcs\["([A-Za-z_][A-Za-z0-9_]*\.[A-Za-z_][A-Za-z0-9_]*)"\]\s*=\s*/gm;
    const entries: Array<{ apiName: string; start: number; rhsStart: number }> = [];
    for (const match of fileText.matchAll(headerRegex)) {
        const full = match[0] ?? "";
        const start = match.index ?? 0;
        entries.push({
            apiName: match[1],
            start,
            rhsStart: start + full.length
        });
    }

    for (let i = 0; i < entries.length; i++) {
        const current = entries[i];
        const next = entries[i + 1];
        const rhsEnd = next ? next.start : fileText.length;
        const rhsRaw = fileText.slice(current.rhsStart, rhsEnd);
        const beforeBuildLoop = rhsRaw.split(/\n(?=\s*for\s+key,\s*value\s+in\s+funcs\.items\(\)\s*:)/)[0] ?? rhsRaw;
        const rhs = normalizeMappingExpression(beforeBuildLoop);
        const apiName = current.apiName;
        if (!rhs) {
            continue;
        }

        const lambdaParams = tryExtractLambdaParams(rhs);
        if (lambdaParams) {
            result.set(apiName, {
                params: lambdaParams,
                rhs,
                description: inferDescriptionFromRhs(apiName, rhs)
            });
            continue;
        }

        const selfMethod = rhs.match(/^self\.([A-Za-z_][A-Za-z0-9_]*)$/);
        if (selfMethod) {
            const methodName = selfMethod[1];
            const info = methods.get(methodName);
            if (info) {
                result.set(apiName, {
                    params: info.params,
                    rhs,
                    description: info.description,
                    returnType: info.returnType
                });
            }
        }
    }

    return result;
}

async function buildWorkspaceFunctionSignatures(): Promise<Map<string, FunctionSignature>> {
    const signatures = new Map<string, FunctionSignature>();
    const staticFiles = await vscode.workspace.findFiles("static/lib_*.py", "**/node_modules/**");
    const dynamicFiles = await vscode.workspace.findFiles("dynamic/lib_*.py", "**/node_modules/**");
    const featureFiles = await vscode.workspace.findFiles("feature/*.py", "**/node_modules/**");
    const files = [...staticFiles, ...dynamicFiles, ...featureFiles];

    for (const file of files) {
        try {
            const data = await vscode.workspace.fs.readFile(file);
            const text = Buffer.from(data).toString("utf8");
            const methods = extractMethodSignatures(text);
            const mapping = extractFuncMappings(text, methods);
            const sourceFile = file.fsPath.split(/[/\\]/).pop() ?? "static/lib_*.py";

            for (const [name, info] of mapping.entries()) {
                signatures.set(
                    name,
                    createSignature(
                        name,
                        info.params,
                        "workspace",
                        sourceFile,
                        info.description,
                        info.returnType
                    )
                );
            }
        } catch {
            // Ignore parse/read failures for individual files.
        }
    }

    return signatures;
}

function listEmbeddedLibFiles(extensionPath: string): string[] {
    const candidates = [
        path.join(extensionPath, "embedded-libs", "static"),
        path.join(extensionPath, "embedded-libs", "dynamic"),
        path.join(extensionPath, "embedded-libs", "feature")
    ];

    const files: string[] = [];
    for (const dir of candidates) {
        if (!fs.existsSync(dir)) {
            continue;
        }
        for (const entry of fs.readdirSync(dir)) {
            if (/^lib_.*\.py$/i.test(entry)) {
                files.push(path.join(dir, entry));
            }
        }
    }

    return files;
}

async function buildWorkspaceFunctionSignaturesWithEmbedded(extensionPath: string): Promise<Map<string, FunctionSignature>> {
    const signatures = new Map<string, FunctionSignature>();
    const workspaceSignatures = await buildWorkspaceFunctionSignatures();
    for (const [name, info] of workspaceSignatures.entries()) {
        signatures.set(name, info);
    }

    const embeddedFiles = listEmbeddedLibFiles(extensionPath);
    for (const filePath of embeddedFiles) {
        if (!fs.existsSync(filePath)) {
            continue;
        }
        try {
            const text = fs.readFileSync(filePath, "utf8");
            const methods = extractMethodSignatures(text);
            const mapping = extractFuncMappings(text, methods);
            const sourceFile = path.basename(filePath);

            for (const [name, info] of mapping.entries()) {
                if (signatures.has(name)) {
                    continue;
                }
                signatures.set(
                    name,
                    createSignature(
                        name,
                        info.params,
                        "builtin",
                        sourceFile,
                        info.description,
                        info.returnType
                    )
                );
            }
        } catch {
            // Ignore parse/read failures for individual files.
        }
    }

    return signatures;
}

function countCommas(text: string): number {
    let level = 0;
    let braceLevel = 0;
    let bracketLevel = 0;
    let inString = false;
    let escaped = false;
    let commas = 0;

    for (const ch of text) {
        if (inString) {
            if (escaped) {
                escaped = false;
                continue;
            }
            if (ch === "\\") {
                escaped = true;
                continue;
            }
            if (ch === "'") {
                inString = false;
            }
            continue;
        }

        if (ch === "'") {
            inString = true;
            continue;
        }
        if (ch === "(") {
            level += 1;
            continue;
        }
        if (ch === ")") {
            level = Math.max(0, level - 1);
            continue;
        }
        if (ch === "{") {
            braceLevel += 1;
            continue;
        }
        if (ch === "}") {
            braceLevel = Math.max(0, braceLevel - 1);
            continue;
        }
        if (ch === "[") {
            bracketLevel += 1;
            continue;
        }
        if (ch === "]") {
            bracketLevel = Math.max(0, bracketLevel - 1);
            continue;
        }
        if (ch === "," && level === 0 && braceLevel === 0 && bracketLevel === 0) {
            commas += 1;
        }
    }

    return commas;
}

function getFunctionCallContext(document: vscode.TextDocument, position: vscode.Position): {
    name: string;
    argumentPrefix: string;
} | undefined {
    const upToCursor = document.getText(new vscode.Range(new vscode.Position(0, 0), position));
    const funcStart = findEnclosingFuncStart(upToCursor);
    if (funcStart < 0) {
        return undefined;
    }

    const segment = upToCursor.slice(funcStart + "{func,".length);

    let inString = false;
    let escaped = false;
    let parenDepth = 0;

    const callStack: Array<{ name: string; depth: number; argumentStart: number }> = [];

    for (let i = 0; i < segment.length; i++) {
        const ch = segment[i];

        if (inString) {
            if (escaped) {
                escaped = false;
                continue;
            }
            if (ch === "\\") {
                escaped = true;
                continue;
            }
            if (ch === "'") {
                inString = false;
            }
            continue;
        }

        if (ch === "'") {
            inString = true;
            continue;
        }

        if (ch === "(") {
            const beforeParen = segment.slice(0, i);
            const nameMatch = beforeParen.match(/([A-Za-z_][A-Za-z0-9_.]*)\s*$/);

            parenDepth += 1;
            if (nameMatch) {
                callStack.push({
                    name: nameMatch[1],
                    depth: parenDepth,
                    argumentStart: i + 1
                });
            }
            continue;
        }

        if (ch === ")") {
            if (callStack.length > 0 && callStack[callStack.length - 1].depth === parenDepth) {
                callStack.pop();
            }
            parenDepth = Math.max(0, parenDepth - 1);
        }
    }

    const current = callStack[callStack.length - 1];
    if (!current) {
        return undefined;
    }

    return {
        name: current.name,
        argumentPrefix: segment.slice(current.argumentStart)
    };
}

function findEnclosingFuncStart(text: string): number {
    let inString = false;
    let escaped = false;
    let braceDepth = 0;
    const funcStack: Array<{ start: number; depth: number }> = [];

    for (let i = 0; i < text.length; i++) {
        const ch = text[i];

        if (inString) {
            if (escaped) {
                escaped = false;
                continue;
            }
            if (ch === "\\") {
                escaped = true;
                continue;
            }
            if (ch === "'") {
                inString = false;
            }
            continue;
        }

        if (ch === "'") {
            inString = true;
            continue;
        }

        if (ch === "{") {
            braceDepth += 1;
            if (text.startsWith("{func,", i)) {
                funcStack.push({ start: i, depth: braceDepth });
            }
            continue;
        }

        if (ch === "}") {
            braceDepth = Math.max(0, braceDepth - 1);
            while (funcStack.length > 0 && funcStack[funcStack.length - 1].depth > braceDepth) {
                funcStack.pop();
            }
        }
    }

    const current = funcStack[funcStack.length - 1];
    return current ? current.start : -1;
}

function extractCurrentTopLevelArgument(argumentPrefix: string): string {
    let level = 0;
    let braceLevel = 0;
    let bracketLevel = 0;
    let inString = false;
    let escaped = false;
    let lastCommaIndex = -1;

    for (let i = 0; i < argumentPrefix.length; i++) {
        const ch = argumentPrefix[i];

        if (inString) {
            if (escaped) {
                escaped = false;
                continue;
            }
            if (ch === "\\") {
                escaped = true;
                continue;
            }
            if (ch === "'") {
                inString = false;
            }
            continue;
        }

        if (ch === "'") {
            inString = true;
            continue;
        }
        if (ch === "(") {
            level += 1;
            continue;
        }
        if (ch === ")") {
            level = Math.max(0, level - 1);
            continue;
        }
        if (ch === "{") {
            braceLevel += 1;
            continue;
        }
        if (ch === "}") {
            braceLevel = Math.max(0, braceLevel - 1);
            continue;
        }
        if (ch === "[") {
            bracketLevel += 1;
            continue;
        }
        if (ch === "]") {
            bracketLevel = Math.max(0, bracketLevel - 1);
            continue;
        }

        if (ch === "," && level === 0 && braceLevel === 0 && bracketLevel === 0) {
            lastCommaIndex = i;
        }
    }

    return argumentPrefix.slice(lastCommaIndex + 1);
}

function parameterInsertName(param: string): string {
    const match = param.match(/[A-Za-z_][A-Za-z0-9_]*/);
    return match ? match[0] : param.trim();
}

function buildFunctionArgumentCompletions(
    context: { name: string; argumentPrefix: string },
    position: vscode.Position
): vscode.CompletionItem[] {
    const signature = FUNCTION_SIGNATURES.get(context.name);
    if (!signature || signature.parameters.length === 0) {
        return [];
    }

    const activeParamIndex = Math.min(
        countCommas(context.argumentPrefix),
        Math.max(0, signature.parameters.length - 1)
    );

    const currentArgText = extractCurrentTopLevelArgument(context.argumentPrefix);
    const typedMatch = currentArgText.match(/([A-Za-z_][A-Za-z0-9_]*)$/);
    const typed = typedMatch?.[1] ?? "";
    const replaceRange = typed.length > 0
        ? new vscode.Range(
            new vscode.Position(position.line, position.character - typed.length),
            position
        )
        : undefined;

    const items = signature.parameters.map((param, index) => {
        const insertName = parameterInsertName(param);
        const item = new vscode.CompletionItem(insertName, vscode.CompletionItemKind.Variable);
        item.insertText = insertName;
        item.detail = index === activeParamIndex
            ? `当前参数建议: ${param}`
            : `函数参数: ${param}`;
        item.documentation = new vscode.MarkdownString(`函数: ${signature.label}`);
        item.sortText = index === activeParamIndex
            ? `0_expected_${index.toString().padStart(2, "0")}`
            : `1_param_${index.toString().padStart(2, "0")}`;
        if (replaceRange) {
            item.range = replaceRange;
            item.filterText = `${typed} ${insertName} ${param}`;
        }
        return item;
    });

    return items;
}

function buildFunctionLiteralCompletions(
    context: { argumentPrefix: string },
    position: vscode.Position
): vscode.CompletionItem[] {
    const currentArgText = extractCurrentTopLevelArgument(context.argumentPrefix);
    const typedMatch = currentArgText.match(/([A-Za-z_]*)$/);
    const typed = typedMatch?.[1] ?? "";
    const replaceRange = new vscode.Range(
        new vscode.Position(position.line, position.character - typed.length),
        position
    );

    const literals = ["True", "False"];
    return literals
        .filter((name) => name.startsWith(typed))
        .map((name) => {
            const item = new vscode.CompletionItem(name, vscode.CompletionItemKind.Keyword);
            item.insertText = name;
            item.sortText = `050_literal_${name}`;
            item.range = replaceRange;
            item.filterText = name;
            return item;
        });
}

function buildFunctionTypeCompletions(
    context: { argumentPrefix: string },
    position: vscode.Position
): vscode.CompletionItem[] {
    const currentArgText = extractCurrentTopLevelArgument(context.argumentPrefix);
    const typedMatch = currentArgText.match(/([A-Za-z_]*)$/);
    const typed = typedMatch?.[1] ?? "";
    const replaceRange = new vscode.Range(
        new vscode.Position(position.line, position.character - typed.length),
        position
    );

    const types = ["int", "bool", "float", "str"];
    return types
        .filter((name) => name.startsWith(typed))
        .map((name) => {
            const item = new vscode.CompletionItem(name, vscode.CompletionItemKind.Keyword);
            item.insertText = name;
            item.sortText = `060_type_${name}`;
            item.range = replaceRange;
            item.filterText = name;
            return item;
        });
}

function buildFunctionArgumentVariableCompletions(
    document: vscode.TextDocument,
    context: { argumentPrefix: string },
    position: vscode.Position
): vscode.CompletionItem[] {
    const currentArgText = extractCurrentTopLevelArgument(context.argumentPrefix);
    const typedMatch = currentArgText.match(/([A-Za-z_][A-Za-z0-9_]*)$/);
    const typed = typedMatch?.[1] ?? "";
    const replaceRange = typed.length > 0
        ? new vscode.Range(
            new vscode.Position(position.line, position.character - typed.length),
            position
        )
        : undefined;

    return extractVariableNames(document)
        .filter((name) => typed.length === 0 || name.startsWith(typed))
        .map((name) => {
            const item = new vscode.CompletionItem(name, vscode.CompletionItemKind.Variable);
            item.insertText = name;
            item.detail = "Variable";
            item.sortText = `150_arg_var_${name}`;
            if (replaceRange) {
                item.range = replaceRange;
                item.filterText = name;
            }
            return item;
        });
}

function isInsideFuncExternal(document: vscode.TextDocument, position: vscode.Position): boolean {
    const upToCursor = document.getText(new vscode.Range(new vscode.Position(0, 0), position));
    return findEnclosingFuncStart(upToCursor) >= 0;
}

function getCurrentFuncParenDepth(document: vscode.TextDocument, position: vscode.Position): number | undefined {
    const upToCursor = document.getText(new vscode.Range(new vscode.Position(0, 0), position));
    const funcStart = findEnclosingFuncStart(upToCursor);
    if (funcStart < 0) {
        return undefined;
    }

    const segment = upToCursor.slice(funcStart + "{func,".length);
    let depth = 0;
    let inString = false;
    let escaped = false;

    for (const ch of segment) {
        if (inString) {
            if (escaped) {
                escaped = false;
                continue;
            }
            if (ch === "\\") {
                escaped = true;
                continue;
            }
            if (ch === "'") {
                inString = false;
            }
            continue;
        }

        if (ch === "'") {
            inString = true;
            continue;
        }
        if (ch === "(") {
            depth += 1;
            continue;
        }
        if (ch === ")") {
            depth = Math.max(0, depth - 1);
        }
    }

    return depth;
}

function buildFunctionDetailHover(name: string, signature: FunctionSignature): vscode.MarkdownString {
    const md = new vscode.MarkdownString();
    md.appendMarkdown(`### ${name}\n\n`);
    md.appendMarkdown("**签名**\n\n");
    md.appendCodeblock(signature.label, "plaintext");

    if (signature.parameters.length > 0) {
        md.appendMarkdown("\n**参数**\n\n");
        for (const param of signature.parameters) {
            md.appendMarkdown(`- ${param}\n`);
        }
    }

    if (signature.returnType) {
        md.appendMarkdown("\n**返回值**\n\n");
        md.appendMarkdown(`- ${signature.returnType}\n`);
    }

    if (signature.description) {
        md.appendMarkdown("\n**说明**\n\n");
        md.appendMarkdown(`${signature.description}\n`);
    }

    return md;
}

function buildFunctionFallbackHover(name: string): vscode.MarkdownString {
    const md = new vscode.MarkdownString();
    md.appendMarkdown(`### ${name}\n\n`);
    md.appendMarkdown("**说明**\n\n");
    md.appendMarkdown(`- ${inferDescriptionFromApiName(name)}\n`);
    return md;
}

function shouldShowFunctionHover(word: string): boolean {
    return FUNCTION_SIGNATURES.has(word);
}

function keywordItem(word: string): vscode.CompletionItem {
    const item = new vscode.CompletionItem(word, vscode.CompletionItemKind.Keyword);
    item.insertText = word;
    return item;
}

function statementItem(word: string): vscode.CompletionItem {
    const item = new vscode.CompletionItem(word, vscode.CompletionItemKind.Function);
    item.insertText = word;
    item.detail = `${word.charAt(0).toUpperCase()}${word.slice(1)} external statement`;
    return item;
}

function buildBraceKeywordOnlyCompletions(
    linePrefix: string,
    position: vscode.Position
): vscode.CompletionItem[] {
    const typedMatch = linePrefix.match(/([A-Za-z_]*)$/);
    const typed = typedMatch?.[1] ?? "";
    const replaceRange = new vscode.Range(
        new vscode.Position(position.line, position.character - typed.length),
        position
    );

    return EXTERNAL_STATEMENTS
        .filter((name) => name.startsWith(typed))
        .map((name) => {
            const item = statementItem(name);
            item.range = replaceRange;
            item.sortText = `0_${name}`;
            return item;
        });
}

function apiItem(name: string): vscode.CompletionItem {
    const item = new vscode.CompletionItem(name, vscode.CompletionItemKind.Function);
    item.insertText = name;
    const signature = FUNCTION_SIGNATURES.get(name);
    item.detail = signature ? signature.label : "Static library API";
    if (signature) {
        item.documentation = new vscode.MarkdownString(`函数签名: ${signature.label}`);
    }
    return item;
}

function apiModuleItem(
    fullName: string,
    moduleName: string,
    replaceRange: vscode.Range
): vscode.CompletionItem {
    const suffix = fullName.startsWith(`${moduleName}.`) ? fullName.slice(moduleName.length + 1) : fullName;
    const item = new vscode.CompletionItem(fullName, vscode.CompletionItemKind.Function);
    item.insertText = fullName;
    item.range = replaceRange;
    const signature = FUNCTION_SIGNATURES.get(fullName);
    item.detail = signature ? signature.label : fullName;
    item.filterText = `${fullName} ${suffix}`;
    item.sortText = `0_${fullName}`;
    if (signature) {
        item.documentation = new vscode.MarkdownString(`函数签名: ${signature.label}`);
    }
    return item;
}

function buildFuncApiCompletions(
    linePrefix: string,
    position: vscode.Position
): vscode.CompletionItem[] {
    const match = linePrefix.match(/\{func,(\s*)([A-Za-z_][A-Za-z0-9_.]*)?(\s*\}?)$/);
    if (!match) {
        return [];
    }

    const spacesAfterComma = match[1] ?? "";
    const partial = match[2] ?? "";
    const trailing = match[3] ?? "";
    const leadingSpace = spacesAfterComma.length > 0 ? "" : " ";

    const replaceRange = partial.length > 0
        ? new vscode.Range(
            new vscode.Position(position.line, position.character - trailing.length - partial.length),
            position
        )
        : undefined;

    const items: vscode.CompletionItem[] = [];
    for (const api of DISCOVERED_APIS) {
        if (partial.length > 0 && !api.startsWith(partial)) {
            continue;
        }

        const item = new vscode.CompletionItem(api, vscode.CompletionItemKind.Function);
        item.insertText = leadingSpace + api;
        const isExactMatch = partial.length > 0 && api === partial;
        if (replaceRange) {
            item.range = replaceRange;
            item.filterText = api;
        }

        const signature = FUNCTION_SIGNATURES.get(api);
        item.detail = signature ? signature.label : "Static library API";
        item.sortText = isExactMatch ? `0000_exact_${api}` : `1000_${api}`;
        item.preselect = isExactMatch;
        if (signature) {
            item.documentation = new vscode.MarkdownString(`函数签名: ${signature.label}`);
        }

        items.push(item);
    }

    return items;
}

type ExternalKind = "command" | "score" | "selector" | "ref" | "func";

interface ExternalArgContext {
    kind: ExternalKind;
    argIndex: number;
    currentArgText: string;
    currentArgStart: number;
}

function findLastTopLevelCommaIndex(text: string): number {
    let level = 0;
    let braceLevel = 0;
    let bracketLevel = 0;
    let inString = false;
    let escaped = false;
    let lastIndex = -1;

    for (let i = 0; i < text.length; i++) {
        const ch = text[i];
        if (inString) {
            if (escaped) {
                escaped = false;
                continue;
            }
            if (ch === "\\") {
                escaped = true;
                continue;
            }
            if (ch === "'") {
                inString = false;
            }
            continue;
        }

        if (ch === "'") {
            inString = true;
            continue;
        }
        if (ch === "(") {
            level += 1;
            continue;
        }
        if (ch === ")") {
            level = Math.max(0, level - 1);
            continue;
        }
        if (ch === "{") {
            braceLevel += 1;
            continue;
        }
        if (ch === "}") {
            braceLevel = Math.max(0, braceLevel - 1);
            continue;
        }
        if (ch === "[") {
            bracketLevel += 1;
            continue;
        }
        if (ch === "]") {
            bracketLevel = Math.max(0, bracketLevel - 1);
            continue;
        }
        if (ch === "," && level === 0 && braceLevel === 0 && bracketLevel === 0) {
            lastIndex = i;
        }
    }

    return lastIndex;
}

function findEnclosingExternalStart(linePrefix: string):
    | { kind: ExternalKind; headerEnd: number; depth: number }
    | undefined {
    let inString = false;
    let escaped = false;
    let braceDepth = 0;
    const stack: Array<{ kind: ExternalKind; headerEnd: number; depth: number }> = [];

    for (let i = 0; i < linePrefix.length; i++) {
        const ch = linePrefix[i];

        if (inString) {
            if (escaped) {
                escaped = false;
                continue;
            }
            if (ch === "\\") {
                escaped = true;
                continue;
            }
            if (ch === "'") {
                inString = false;
            }
            continue;
        }

        if (ch === "'") {
            inString = true;
            continue;
        }

        if (ch === "{") {
            braceDepth += 1;

            let j = i + 1;
            while (j < linePrefix.length && /\s/.test(linePrefix[j])) {
                j += 1;
            }

            let k = j;
            while (k < linePrefix.length && /[A-Za-z]/.test(linePrefix[k])) {
                k += 1;
            }

            if (k > j) {
                const word = linePrefix.slice(j, k);
                if ((["command", "score", "selector", "ref", "func"] as const).includes(word as ExternalKind)) {
                    stack.push({
                        kind: word as ExternalKind,
                        headerEnd: k,
                        depth: braceDepth
                    });
                }
            }
            continue;
        }

        if (ch === "}") {
            braceDepth = Math.max(0, braceDepth - 1);
            while (stack.length > 0 && stack[stack.length - 1].depth > braceDepth) {
                stack.pop();
            }
        }
    }

    return stack[stack.length - 1];
}

function hasUnclosedBraceContext(linePrefix: string): boolean {
    let inString = false;
    let escaped = false;
    let depth = 0;

    for (let i = 0; i < linePrefix.length; i++) {
        const ch = linePrefix[i];

        if (inString) {
            if (escaped) {
                escaped = false;
                continue;
            }
            if (ch === "\\") {
                escaped = true;
                continue;
            }
            if (ch === "'") {
                inString = false;
            }
            continue;
        }

        if (ch === "'") {
            inString = true;
            continue;
        }

        if (ch === "{") {
            depth += 1;
            continue;
        }

        if (ch === "}") {
            depth = Math.max(0, depth - 1);
        }
    }

    return depth > 0;
}

function getExternalArgContext(linePrefix: string): ExternalArgContext | undefined {
    const enclosing = findEnclosingExternalStart(linePrefix);
    if (!enclosing) {
        return undefined;
    }

    const tail = linePrefix.slice(enclosing.headerEnd);
    const commaCount = countCommas(tail);
    const lastCommaIndex = findLastTopLevelCommaIndex(tail);
    const currentArgRaw = tail.slice(lastCommaIndex + 1);
    const leadingSpaces = (currentArgRaw.match(/^\s*/) ?? [""])[0].length;
    const currentArgText = currentArgRaw.slice(leadingSpaces);
    const currentArgStart = enclosing.headerEnd + lastCommaIndex + 1 + leadingSpaces;

    return {
        kind: enclosing.kind,
        argIndex: commaCount,
        currentArgText,
        currentArgStart
    };
}

function externalArgItem(
    label: string,
    snippet: string,
    detail: string,
    replaceRange?: vscode.Range
): vscode.CompletionItem {
    const item = new vscode.CompletionItem(label, vscode.CompletionItemKind.Field);
    item.insertText = new vscode.SnippetString(snippet);
    item.detail = detail;
    item.sortText = "0_external_arg";
    if (replaceRange) {
        item.range = replaceRange;
    }
    return item;
}

function nestedExternalItem(
    label: string,
    snippet: string,
    detail: string,
    replaceRange?: vscode.Range
): vscode.CompletionItem {
    const item = new vscode.CompletionItem(label, vscode.CompletionItemKind.Function);
    item.insertText = new vscode.SnippetString(snippet);
    item.detail = detail;
    item.sortText = "0_nested_external";
    if (replaceRange) {
        item.range = replaceRange;
    }
    return item;
}

function booleanLiteralItemsForRange(
    leadingSpace: string,
    replaceRange: vscode.Range
): vscode.CompletionItem[] {
    return ["True", "False"].map((literal) => {
        const item = new vscode.CompletionItem(literal, vscode.CompletionItemKind.Keyword);
        item.insertText = leadingSpace + literal;
        item.range = replaceRange;
        item.sortText = `2_bool_${literal}`;
        return item;
    });
}

function typeKeywordItemsForRange(
    leadingSpace: string,
    replaceRange: vscode.Range
): vscode.CompletionItem[] {
    return ["int", "bool", "float", "str"].map((name) => {
        const item = new vscode.CompletionItem(name, vscode.CompletionItemKind.Keyword);
        item.insertText = leadingSpace + name;
        item.range = replaceRange;
        item.sortText = `2_type_${name}`;
        return item;
    });
}

function buildBracedExternalKeywordItems(
    _document: vscode.TextDocument,
    currentArgText: string,
    position: vscode.Position,
    allowedKinds: ExternalKind[]
): vscode.CompletionItem[] {
    const lastOpenBrace = currentArgText.lastIndexOf("{");
    if (lastOpenBrace < 0) {
        return [];
    }

    const suffix = currentArgText.slice(lastOpenBrace);
    const bracedKeywordMatch = suffix.match(/^\{\s*([A-Za-z_]*)\s*\}?$/);
    if (!bracedKeywordMatch) {
        return [];
    }

    const partial = bracedKeywordMatch[1] ?? "";
    const partialMatch = suffix.match(/[A-Za-z_]*$/);
    const partialLength = partialMatch?.[0]?.length ?? 0;
    const replaceRange = new vscode.Range(
        new vscode.Position(position.line, position.character - partialLength),
        position
    );

    return allowedKinds
        .filter((kind) => kind.startsWith(partial))
        .map((kind) => {
            const item = new vscode.CompletionItem(kind, vscode.CompletionItemKind.Keyword);
            item.insertText = kind;
            item.range = replaceRange;
            item.detail = `${kind.charAt(0).toUpperCase()}${kind.slice(1)} external statement`;
            item.sortText = `0_nested_keyword_${kind}`;
            item.preselect = true;
            return item;
        });
}

function externalArgValueItem(
    label: string,
    detail: string,
    replaceRange?: vscode.Range
): vscode.CompletionItem {
    const item = new vscode.CompletionItem(label, vscode.CompletionItemKind.Keyword);
    item.insertText = label;
    item.detail = detail;
    item.sortText = `0_${label}`;
    if (replaceRange) {
        item.range = replaceRange;
    }
    return item;
}

function getIfConditionContext(linePrefix: string):
    | { keyword: "if" | "elif"; conditionPrefix: string }
    | undefined {
    const match = linePrefix.match(/^\s*(if|elif)\b([\s\S]*)$/);
    if (!match) {
        return undefined;
    }

    const keyword = match[1] as "if" | "elif";
    const tail = match[2] ?? "";
    if (tail.includes(":")) {
        return undefined;
    }

    return {
        keyword,
        conditionPrefix: tail
    };
}

function conditionKeywordItem(word: string): vscode.CompletionItem {
    const item = new vscode.CompletionItem(word, vscode.CompletionItemKind.Keyword);
    item.insertText = word;
    item.sortText = `0_${word}`;
    item.detail = "Condition keyword";
    return item;
}

function conditionOperatorItem(op: string, detail: string): vscode.CompletionItem {
    const item = new vscode.CompletionItem(op, vscode.CompletionItemKind.Operator);
    item.insertText = op;
    item.sortText = `1_${op}`;
    item.detail = detail;
    return item;
}

function buildIfConditionCompletions(
    document: vscode.TextDocument,
    conditionPrefix: string
): vscode.CompletionItem[] {
    const items: vscode.CompletionItem[] = [];

    items.push(...extractVariableNames(document).map(variableItem));
    items.push(
        conditionKeywordItem("True"),
        conditionKeywordItem("False"),
        conditionKeywordItem("and"),
        conditionKeywordItem("or"),
        conditionKeywordItem("not"),
        conditionKeywordItem("in")
    );

    items.push(
        conditionOperatorItem("==", "Equal"),
        conditionOperatorItem("!=", "Not equal"),
        conditionOperatorItem(">", "Greater than"),
        conditionOperatorItem("<", "Less than"),
        conditionOperatorItem(">=", "Greater or equal"),
        conditionOperatorItem("<=", "Less or equal")
    );

    const trimmedPrefix = conditionPrefix.trimStart();
    if (trimmedPrefix.startsWith("cond")) {
        items.push(
            snippetItem("cond: ==", "${1:left} == ${2:right}", "condition template", "cond eq template"),
            snippetItem("cond: !=", "${1:left} != ${2:right}", "condition template", "cond neq template"),
            snippetItem("cond: and", "${1:left} and ${2:right}", "condition template", "cond and template"),
            snippetItem("cond: or", "${1:left} or ${2:right}", "condition template", "cond or template"),
            snippetItem("cond: not", "not ${1:condition}", "condition template", "cond not template"),
            snippetItem("cond: in", "${1:item} in ${2:container}", "condition template", "cond in template"),
            snippetItem("cond: {func}", "{func, ${1:math.sqrt(4)}}", "function expression in condition", "cond func template")
        );
    }

    return items;
}

function extractVariableNames(document: vscode.TextDocument): string[] {
    const reserved = new Set([
        "if", "elif", "else", "fi", "for", "continue", "break", "rof", "return",
        "and", "or", "not", "in", "True", "False", "int", "bool", "float", "str",
        "ref", "selector", "score", "command", "func"
    ]);

    const names = new Set<string>();
    const assignRegex = /\b([A-Za-z_][A-Za-z0-9_]*)\b(?=\s*=)/g;
    const forHeaderRegex = /^\s*for\s+([A-Za-z_][A-Za-z0-9_]*)\s*,\s*([^:]+?)\s*:\s*$/;
    let inBlockComment = false;

    for (let line = 0; line < document.lineCount; line++) {
        const raw = document.lineAt(line).text;
        const commentAware = stripCommentsFromLine(raw, inBlockComment);
        inBlockComment = commentAware.inBlockComment;
        const text = commentAware.code;
        for (const match of text.matchAll(assignRegex)) {
            const name = match[1];
            if (!reserved.has(name)) {
                names.add(name);
            }
        }

        const forHeaderMatch = text.match(forHeaderRegex);
        if (forHeaderMatch) {
            const indexName = forHeaderMatch[1];
            if (!reserved.has(indexName)) {
                names.add(indexName);
            }

            const countExpr = forHeaderMatch[2].trim();
            if (/^[A-Za-z_][A-Za-z0-9_]*$/.test(countExpr) && !reserved.has(countExpr)) {
                names.add(countExpr);
            }
        }
    }

    return [...names].sort();
}

function variableItem(name: string): vscode.CompletionItem {
    const item = new vscode.CompletionItem(name, vscode.CompletionItemKind.Variable);
    item.insertText = name;
    item.detail = "Variable";
    item.sortText = `1_${name}`;
    return item;
}

function getExternalArgumentCompletions(
    document: vscode.TextDocument,
    context: ExternalArgContext,
    linePrefix: string,
    position: vscode.Position
): vscode.CompletionItem[] {
    const hasTrailingWhitespace = /\s$/.test(linePrefix);
    const leadingSpace = hasTrailingWhitespace ? "" : " ";
    const currentArgRange = new vscode.Range(
        new vscode.Position(position.line, context.currentArgStart),
        position
    );
    const refTypePartialMatch = context.currentArgText.match(/([A-Za-z_]*)$/);
    const refTypePartial = refTypePartialMatch?.[1] ?? "";

    const names = extractVariableNames(document);
    const variableItemsForRange = (replaceRange?: vscode.Range): vscode.CompletionItem[] => {
        return names.map((name) => {
            const item = externalArgValueItem(name, "Variable", replaceRange);
            item.insertText = leadingSpace + name;
            item.sortText = `1_${name}`;
            return item;
        });
    };

    if (context.kind === "command" && context.argIndex === 1) {
        const bracedKeywordItems = buildBracedExternalKeywordItems(
            document,
            context.currentArgText,
            position,
            ["selector", "score", "command", "ref", "func"]
        );
        return [
            ...bracedKeywordItems,
            ...booleanLiteralItemsForRange(leadingSpace, currentArgRange),
            ...typeKeywordItemsForRange(leadingSpace, currentArgRange),
            externalArgItem(
                "commandLine",
                leadingSpace + "'${1:say Hello, World!}'",
                "Command statement argument",
                currentArgRange
            ),
            ...variableItemsForRange(currentArgRange)
        ];
    }

    if (context.kind === "selector" && context.argIndex === 1) {
        const bracedKeywordItems = buildBracedExternalKeywordItems(
            document,
            context.currentArgText,
            position,
            ["selector", "score", "command", "ref", "func"]
        );
        return [
            ...bracedKeywordItems,
            ...booleanLiteralItemsForRange(leadingSpace, currentArgRange),
            ...typeKeywordItemsForRange(leadingSpace, currentArgRange),
            externalArgItem(
                "target",
                leadingSpace + "'${1:@s}'",
                "Selector statement argument",
                currentArgRange
            ),
            ...variableItemsForRange(currentArgRange)
        ];
    }

    if (context.kind === "score") {
        if (context.argIndex === 1) {
            const bracedKeywordItems = buildBracedExternalKeywordItems(
                document,
                context.currentArgText,
                position,
                ["selector", "score", "command", "ref", "func"]
            );

            return [
                ...bracedKeywordItems,
                ...booleanLiteralItemsForRange(leadingSpace, currentArgRange),
                ...typeKeywordItemsForRange(leadingSpace, currentArgRange),
                externalArgItem(
                    "player",
                    leadingSpace + "'${1:@s}'",
                    "Score statement argument",
                    currentArgRange
                ),
                ...variableItemsForRange(currentArgRange)
            ];
        }
        if (context.argIndex === 2) {
            const bracedKeywordItems = buildBracedExternalKeywordItems(
                document,
                context.currentArgText,
                position,
                ["selector", "score", "command", "ref", "func"]
            );
            return [
                ...bracedKeywordItems,
                ...booleanLiteralItemsForRange(leadingSpace, currentArgRange),
                ...typeKeywordItemsForRange(leadingSpace, currentArgRange),
                externalArgItem(
                    "scoreboard",
                    leadingSpace + "'${1:coin}'",
                    "Score statement argument",
                    currentArgRange
                ),
                ...variableItemsForRange(currentArgRange)
            ];
        }
    }

    if (context.kind === "ref") {
        if (context.argIndex === 1) {
            const allTypes = ["int", "bool", "float", "str"];
            const filtered = refTypePartial.length > 0
                ? allTypes.filter((name) => name.startsWith(refTypePartial))
                : allTypes;
            return filtered.map((name) => {
                const item = externalArgValueItem(name, "Ref statement argument", currentArgRange);
                item.insertText = leadingSpace + name;
                return item;
            });
        }
        if (context.argIndex === 2) {
            const bracedKeywordItems = buildBracedExternalKeywordItems(
                document,
                context.currentArgText,
                position,
                ["selector", "score", "command", "ref", "func"]
            );
            return [
                ...bracedKeywordItems,
                ...booleanLiteralItemsForRange(leadingSpace, currentArgRange),
                ...typeKeywordItemsForRange(leadingSpace, currentArgRange),
                externalArgItem("index", leadingSpace + "${1:0}", "Ref statement argument"),
                ...variableItemsForRange(currentArgRange)
            ];
        }
    }

    if (context.kind === "func") {
        const bracedKeywordItems = buildBracedExternalKeywordItems(
            document,
            context.currentArgText,
            position,
            ["selector", "score", "command", "ref", "func"]
        );
        const functionCallContext = getFunctionCallContext(document, position);
        const functionArgVariableItems = functionCallContext
            ? buildFunctionArgumentVariableCompletions(document, functionCallContext, position)
            : [];
        const functionLiteralItems = functionCallContext
            ? buildFunctionLiteralCompletions(functionCallContext, position)
            : [];
        const functionTypeItems = functionCallContext
            ? buildFunctionTypeCompletions(functionCallContext, position)
            : [];
        const normalizedFuncArgText = context.currentArgText.replace(/[\s\}\]\)]+$/g, "");
        const normalizedPartialMatch = normalizedFuncArgText.match(/([A-Za-z_][A-Za-z0-9_.]*)$/);
        const normalizedPartial = normalizedPartialMatch?.[1] ?? "";
        const partialOffsetInArg = normalizedPartial.length > 0
            ? context.currentArgText.lastIndexOf(normalizedPartial)
            : -1;
        const funcApiReplaceStart = normalizedPartial.length > 0 && partialOffsetInArg >= 0
            ? context.currentArgStart + partialOffsetInArg
            : context.currentArgStart;
        const funcApiReplaceRange = new vscode.Range(
            new vscode.Position(position.line, funcApiReplaceStart),
            position
        );

        const funcApiItems = functionCallContext
            ? []
            : DISCOVERED_APIS
                .filter((api) => normalizedPartial.length === 0 || api.startsWith(normalizedPartial))
                .map((api) => {
                    const item = new vscode.CompletionItem(api, vscode.CompletionItemKind.Function);
                    item.insertText = api;
                    item.detail = FUNCTION_SIGNATURES.get(api)?.label ?? "Function API";
                    const isExactMatch = normalizedPartial.length > 0 && api === normalizedPartial;
                    item.sortText = isExactMatch ? `0000_exact_${api}` : `1000_api_${api}`;
                    item.preselect = isExactMatch;
                    item.range = funcApiReplaceRange;
                    if (normalizedPartial.length > 0) {
                        item.filterText = api;
                    }
                    return item;
                });
        return [
            ...funcApiItems,
            ...functionArgVariableItems,
            ...functionLiteralItems,
            ...functionTypeItems,
            ...bracedKeywordItems,
            ...variableItemsForRange(currentArgRange)
        ];
    }

    return [];
}

function snippetItem(
    label: string,
    snippet: string,
    detail: string,
    filterText?: string
): vscode.CompletionItem {
    const item = new vscode.CompletionItem(label, vscode.CompletionItemKind.Snippet);
    item.insertText = new vscode.SnippetString(snippet);
    item.detail = detail;
    item.documentation = new vscode.MarkdownString("Template snippet");
    if (filterText) {
        item.filterText = filterText;
    }
    return item;
}

type BlockType = "if" | "for";

interface BlockState {
    type: BlockType;
    line: number;
    hasElse: boolean;
}

const HOVER_DOCS = new Map<string, string>([
    ["if", "条件语句起始。语法: `if 条件: `"],
    ["elif", "条件分支。语法: `elif 条件: `，且必须位于 `if ...fi` 中。"],
    ["else", "条件兜底分支。语法: `else: `，且必须位于 `if ...fi` 中。"],
    ["fi", "结束 `if` 代码块。"],
    ["for", "循环语句起始。语法: `for 变量, 次数: `"],
    ["rof", "结束 `for` 代码块。"],
    ["return", "返回表达式结果。语法: `return 表达式`。"],
    ["selector", "外部语句关键字。语法: `{ selector, <target: str >} `"],
    ["score", "外部语句关键字。语法: `{ score, <player: str >, <scoreboard: str >} `"],
    ["command", "外部语句关键字。语法: `{ command, <commandLine: str >} `"],
    ["ref", "外部语句关键字。语法: `{ ref, <dataType: type >, <index: int >} `"],
    ["func", "外部语句关键字。语法: `{ func, 表达式 } `"],
    ["and", "逻辑与运算。"],
    ["or", "逻辑或运算。"],
    ["not", "逻辑取反运算。"],
    ["in", "成员检查运算。"],
    ["int", "强制类型转换为整数。语法: `int(...)`"],
    ["bool", "强制类型转换为布尔值。语法: `bool(...)`"],
    ["float", "强制类型转换为浮点数。语法: `float(...)`"],
    ["str", "强制类型转换为字符串。语法: `str(...)`"],
    ["True", "布尔真值。"],
    ["False", "布尔假值。"]
]);

const REF_TYPE_ASSERTION_WORDS = new Set(["int", "bool", "float", "str"]);
const REF_TYPE_ASSERTION_TIP = "在 `ref` 语句中，这里用于类型断言（声明引用目标类型），不是运行时强制类型转换。";

function isRefTypeAssertionPosition(
    document: vscode.TextDocument,
    wordRange: vscode.Range
): boolean {
    const lineText = document.lineAt(wordRange.start.line).text;
    const before = lineText.slice(0, wordRange.start.character);
    const after = lineText.slice(wordRange.end.character);

    const isRefFirstArg = /\{\s*ref\b[^}]*,\s*$/.test(before);
    const firstArgTerminator = /^\s*(,|\})/.test(after);
    return isRefFirstArg && firstArgTerminator;
}

function stripCommentsFromLine(
    line: string,
    inBlockComment: boolean
): { code: string; inBlockComment: boolean } {
    let i = 0;
    let inString = false;
    let escaped = false;
    let code = "";

    if (inBlockComment) {
        const end = line.indexOf("*/");
        if (end < 0) {
            return { code: "", inBlockComment: true };
        }
        i = end + 2;
        inBlockComment = false;
    }

    while (i < line.length) {
        const ch = line[i];

        if (inString) {
            code += ch;
            if (escaped) {
                escaped = false;
            } else if (ch === "\\") {
                escaped = true;
            } else if (ch === "'") {
                inString = false;
            }
            i += 1;
            continue;
        }

        if (ch === "'") {
            inString = true;
            code += ch;
            i += 1;
            continue;
        }

        if (line.startsWith("//", i)) {
            break;
        }

        if (line.startsWith("/*", i)) {
            const end = line.indexOf("*/", i + 2);
            if (end < 0) {
                return { code, inBlockComment: true };
            }
            i = end + 2;
            continue;
        }

        code += ch;
        i += 1;
    }

    return { code, inBlockComment: false };
}

function firstToken(line: string): string | undefined {
    const match = line.trimStart().match(/^([A-Za-z_][A-Za-z0-9_]*)\b/);
    return match?.[1];
}

function endsWithColon(line: string): boolean {
    return line.trimEnd().endsWith(":");
}

function makeLineRange(document: vscode.TextDocument, line: number): vscode.Range {
    return document.lineAt(line).range;
}

function splitTopLevelArguments(text: string): string[] {
    const parts: string[] = [];
    let start = 0;
    let paren = 0;
    let brace = 0;
    let bracket = 0;
    let inString = false;
    let escaped = false;

    for (let i = 0; i < text.length; i++) {
        const ch = text[i];

        if (inString) {
            if (escaped) {
                escaped = false;
                continue;
            }
            if (ch === "\\") {
                escaped = true;
                continue;
            }
            if (ch === "'") {
                inString = false;
            }
            continue;
        }

        if (ch === "'") {
            inString = true;
            continue;
        }
        if (ch === "(") {
            paren += 1;
            continue;
        }
        if (ch === ")") {
            paren = Math.max(0, paren - 1);
            continue;
        }
        if (ch === "{") {
            brace += 1;
            continue;
        }
        if (ch === "}") {
            brace = Math.max(0, brace - 1);
            continue;
        }
        if (ch === "[") {
            bracket += 1;
            continue;
        }
        if (ch === "]") {
            bracket = Math.max(0, bracket - 1);
            continue;
        }

        if (ch === "," && paren === 0 && brace === 0 && bracket === 0) {
            parts.push(text.slice(start, i).trim());
            start = i + 1;
        }
    }

    parts.push(text.slice(start).trim());
    return parts;
}

function findMatchingParenAtEnd(text: string, openIndex: number): boolean {
    let inString = false;
    let escaped = false;
    let depth = 0;

    for (let i = openIndex; i < text.length; i++) {
        const ch = text[i];

        if (inString) {
            if (escaped) {
                escaped = false;
                continue;
            }
            if (ch === "\\") {
                escaped = true;
                continue;
            }
            if (ch === "'") {
                inString = false;
            }
            continue;
        }

        if (ch === "'") {
            inString = true;
            continue;
        }

        if (ch === "(") {
            depth += 1;
            continue;
        }

        if (ch === ")") {
            depth -= 1;
            if (depth === 0) {
                return i === text.length - 1;
            }
            continue;
        }
    }

    return false;
}

function normalizeFunctionCallExpression(expr: string): string | undefined {
    const trimmed = expr.trim();
    const openIndex = trimmed.indexOf("(");
    if (openIndex <= 0 || !trimmed.endsWith(")")) {
        return undefined;
    }

    const name = trimmed.slice(0, openIndex).trim();
    if (!/^[A-Za-z_][A-Za-z0-9_.]*$/.test(name)) {
        return undefined;
    }

    if (!findMatchingParenAtEnd(trimmed, openIndex)) {
        return undefined;
    }

    const inner = trimmed.slice(openIndex + 1, -1);
    const args = splitTopLevelArguments(inner).filter((arg) => arg.length > 0);
    if (args.length === 0) {
        return `${name}()`;
    }

    const normalizedArgs = args.map((arg) => normalizeExpression(arg));
    return `${name}(${normalizedArgs.join(", ")})`;
}

function normalizeOperatorSpacing(text: string): string {
    let result = text;
    result = result.replace(/\s*(==|!=|>=|<=|>|<)\s*/g, " $1 ");
    result = result.replace(/\s*\b(and|or|in)\b\s*/g, " $1 ");
    result = result.replace(/\s*\bnot\b\s*/g, " not ");
    result = result.replace(/[ \t]{2,}/g, " ");
    return result.trim();
}

function normalizeExpression(expr: string): string {
    const trimmed = expr.trim();
    if (trimmed.length === 0) {
        return trimmed;
    }

    const external = normalizeExternalStatement(trimmed);
    if (external) {
        return external;
    }

    const funcCall = normalizeFunctionCallExpression(trimmed);
    if (funcCall) {
        return funcCall;
    }

    return normalizeOperatorSpacing(trimmed);
}

function normalizeExternalStatement(code: string): string | undefined {
    const trimmed = code.trim();
    const match = trimmed.match(/^\{\s*(selector|score|command|ref|func)\s*(?:,\s*([\s\S]*))?\}\s*$/);
    if (!match) {
        return undefined;
    }

    const kind = match[1];
    const argText = match[2] ?? "";
    const args = splitTopLevelArguments(argText)
        .map((arg) => normalizeExpression(arg))
        .filter((arg) => arg.length > 0);
    if (args.length === 0) {
        return `{${kind}}`;
    }

    return `{${kind}, ${args.join(", ")}}`;
}

function normalizeCodeLine(code: string): string {
    const trimmed = code.trim();
    if (trimmed.length === 0) {
        return trimmed;
    }

    if (/^else\s*:\s*$/.test(trimmed)) {
        return "else:";
    }

    const keywordColonMatch = trimmed.match(/^(if|elif|for)\s+([\s\S]*?)\s*:\s*$/);
    if (keywordColonMatch) {
        const keyword = keywordColonMatch[1];
        const body = keywordColonMatch[2].trim();
        if (keyword === "for") {
            const forParts = splitTopLevelArguments(body);
            const normalizedForParts = forParts.map((part) => normalizeExpression(part));
            return `${keyword} ${normalizedForParts.join(", ")}:`;
        }
        return `${keyword} ${normalizeExpression(body)}:`;
    }

    const assignMatch = trimmed.match(/^([A-Za-z_][A-Za-z0-9_]*)\s*=\s*([\s\S]+)$/);
    if (assignMatch) {
        return `${assignMatch[1]} = ${normalizeExpression(assignMatch[2])}`;
    }

    const returnMatch = trimmed.match(/^return\b([\s\S]*)$/);
    if (returnMatch) {
        const expr = returnMatch[1].trim();
        if (expr.length === 0) {
            return "return";
        }
        return `return ${normalizeExpression(expr)}`;
    }

    const external = normalizeExternalStatement(trimmed);
    if (external) {
        return external;
    }

    return normalizeExpression(trimmed);
}

interface ForHeaderIdentifiers {
    indexName: string;
    indexRange: vscode.Range;
    countName: string;
    countRange: vscode.Range;
}

function getForHeaderSignatureContext(
    document: vscode.TextDocument,
    position: vscode.Position
): { activeParameter: 0 | 1 } | undefined {
    const linePrefix = document.lineAt(position.line).text.slice(0, position.character);
    if (/^\s*for\s+$/.test(linePrefix)) {
        return { activeParameter: 0 };
    }

    if (/^\s*for\s+[A-Za-z_][A-Za-z0-9_]*\s*$/.test(linePrefix)) {
        return { activeParameter: 0 };
    }

    const countMatch = linePrefix.match(/^\s*for\s+[A-Za-z_][A-Za-z0-9_]*\s*,\s*([A-Za-z_][A-Za-z0-9_]*)?\s*$/);
    if (countMatch) {
        return { activeParameter: 1 };
    }

    return undefined;
}

function getIfElifSignatureContext(
    document: vscode.TextDocument,
    position: vscode.Position
): { keyword: "if" | "elif" } | undefined {
    const linePrefix = document.lineAt(position.line).text.slice(0, position.character);
    const match = linePrefix.match(/^\s*(if|elif)\s+([^:]*)$/);
    if (!match) {
        return undefined;
    }

    const keyword = match[1] as "if" | "elif";
    return { keyword };
}

function getForHeaderIdentifiers(document: vscode.TextDocument, line: number): ForHeaderIdentifiers | undefined {
    const text = document.lineAt(line).text;
    const match = text.match(/^\s*for\s+([A-Za-z_][A-Za-z0-9_]*)\s*,\s*([A-Za-z_][A-Za-z0-9_]*)\s*:\s*$/);
    if (!match) {
        return undefined;
    }

    const indexName = match[1];
    const countName = match[2];
    const indexStart = text.indexOf(indexName);
    const countStart = text.indexOf(countName, indexStart + indexName.length);

    if (indexStart < 0 || countStart < 0) {
        return undefined;
    }

    return {
        indexName,
        indexRange: new vscode.Range(
            new vscode.Position(line, indexStart),
            new vscode.Position(line, indexStart + indexName.length)
        ),
        countName,
        countRange: new vscode.Range(
            new vscode.Position(line, countStart),
            new vscode.Position(line, countStart + countName.length)
        )
    };
}

function pushSyntaxError(
    result: vscode.Diagnostic[],
    document: vscode.TextDocument,
    line: number,
    message: string
): void {
    result.push(
        new vscode.Diagnostic(
            makeLineRange(document, line),
            message,
            vscode.DiagnosticSeverity.Error
        )
    );
}

function validateControlHeaders(
    text: string,
    token: string,
    result: vscode.Diagnostic[],
    document: vscode.TextDocument,
    line: number
): void {
    if ((token === "if" || token === "elif") && endsWithColon(text)) {
        const match = text.trim().match(/^(if|elif)\s+([\s\S]*?)\s*:\s*$/);
        if (!match || match[2].trim().length === 0) {
            pushSyntaxError(result, document, line, `\`${token}\` 条件不能为空。`);
        }
    }

    if (token === "for" && endsWithColon(text)) {
        const match = text.trim().match(/^for\s+([\s\S]*?)\s*:\s*$/);
        if (!match) {
            return;
        }

        const parts = splitTopLevelArguments(match[1]);
        if (parts.length !== 2) {
            pushSyntaxError(result, document, line, "`for` 语句语法应为 `for 变量, 次数:`。");
            return;
        }

        const indexName = parts[0].trim();
        const countExpr = parts[1].trim();
        if (!/^[A-Za-z_][A-Za-z0-9_]*$/.test(indexName)) {
            pushSyntaxError(result, document, line, "`for` 第一个参数必须是合法变量名。`for 变量, 次数:`");
        }
        if (countExpr.length === 0) {
            pushSyntaxError(result, document, line, "`for` 第二个参数（次数）不能为空。`for 变量, 次数:`");
        }
    }

    if (token === "else" && endsWithColon(text)) {
        if (!/^\s*else\s*:\s*$/.test(text)) {
            pushSyntaxError(result, document, line, "`else` 语句不应包含条件或额外表达式。语法: `else:`");
        }
    }
}

function validateExternalStatement(
    text: string,
    result: vscode.Diagnostic[],
    document: vscode.TextDocument,
    line: number
): void {
    const trimmed = text.trim();
    if (!trimmed.startsWith("{")) {
        return;
    }

    if (!trimmed.endsWith("}")) {
        pushSyntaxError(result, document, line, "外部语句缺少右花括号 `}`。");
        return;
    }

    const match = trimmed.match(/^\{\s*([A-Za-z_][A-Za-z0-9_]*)\s*(?:,\s*([\s\S]*))?\}\s*$/);
    if (!match) {
        pushSyntaxError(result, document, line, "外部语句语法无效。示例: `{score, '@s', 'coin'}`。");
        return;
    }

    const kind = match[1];
    const argText = match[2] ?? "";
    const args = argText.length > 0
        ? splitTopLevelArguments(argText).filter((arg) => arg.trim().length > 0)
        : [];

    const allowed = new Set(["selector", "score", "command", "ref", "func"]);
    if (!allowed.has(kind)) {
        pushSyntaxError(result, document, line, `未知外部语句 \`${kind}\`。`);
        return;
    }

    const expectedArgs = new Map<string, number>([
        ["selector", 1],
        ["command", 1],
        ["score", 2],
        ["ref", 2],
        ["func", 1]
    ]);

    const expected = expectedArgs.get(kind) ?? 0;
    if (args.length !== expected) {
        pushSyntaxError(result, document, line, `\`${kind}\` 语句参数数量应为 ${expected}，当前为 ${args.length}。`);
        return;
    }

    if (kind === "ref") {
        const refType = args[0].trim();
        if (/^[A-Za-z_][A-Za-z0-9_]*$/.test(refType) && !["int", "bool", "float", "str"].includes(refType)) {
            pushSyntaxError(result, document, line, "`ref` 第一个参数应为 `int/bool/float/str`。");
        }
    }
}

function validateDocument(
    document: vscode.TextDocument,
    diagnostics: vscode.DiagnosticCollection
): void {
    if (document.languageId !== "form-python-ast") {
        return;
    }

    const result: vscode.Diagnostic[] = [];
    const stack: BlockState[] = [];
    let inBlockComment = false;

    for (let line = 0; line < document.lineCount; line++) {
        const raw = document.lineAt(line).text;
        const commentAware = stripCommentsFromLine(raw, inBlockComment);
        inBlockComment = commentAware.inBlockComment;
        const text = commentAware.code;

        if (text.trim().length === 0) {
            continue;
        }

        const token = firstToken(text);
        if (!token) {
            continue;
        }

        validateControlHeaders(text, token, result, document, line);
        validateExternalStatement(text, result, document, line);

        if ((token === "if" || token === "elif" || token === "else" || token === "for") && !endsWithColon(text)) {
            pushSyntaxError(result, document, line, `\`${token}\` 语句应以冒号结尾。`);
        }

        if (token === "if") {
            stack.push({ type: "if", line, hasElse: false });
            continue;
        }

        if (token === "for") {
            stack.push({ type: "for", line, hasElse: false });
            continue;
        }

        if (token === "elif") {
            const top = stack[stack.length - 1];
            if (!top || top.type !== "if") {
                result.push(
                    new vscode.Diagnostic(
                        makeLineRange(document, line),
                        "`elif` 必须出现在 `if ... fi` 代码块中。",
                        vscode.DiagnosticSeverity.Error
                    )
                );
            } else if (top.hasElse) {
                result.push(
                    new vscode.Diagnostic(
                        makeLineRange(document, line),
                        "`elif` 不能出现在 `else` 之后。",
                        vscode.DiagnosticSeverity.Error
                    )
                );
            }
            continue;
        }

        if (token === "else") {
            const top = stack[stack.length - 1];
            if (!top || top.type !== "if") {
                result.push(
                    new vscode.Diagnostic(
                        makeLineRange(document, line),
                        "`else` 必须出现在 `if ... fi` 代码块中。",
                        vscode.DiagnosticSeverity.Error
                    )
                );
            } else if (top.hasElse) {
                result.push(
                    new vscode.Diagnostic(
                        makeLineRange(document, line),
                        "同一个 `if` 代码块中只能出现一个 `else`。",
                        vscode.DiagnosticSeverity.Error
                    )
                );
            } else {
                top.hasElse = true;
            }
            continue;
        }

        if (token === "fi") {
            const top = stack[stack.length - 1];
            if (!top || top.type !== "if") {
                result.push(
                    new vscode.Diagnostic(
                        makeLineRange(document, line),
                        "`fi` 缺少对应的 `if`。",
                        vscode.DiagnosticSeverity.Error
                    )
                );
            } else {
                stack.pop();
            }
            continue;
        }

        if (token === "rof") {
            const top = stack[stack.length - 1];
            if (!top || top.type !== "for") {
                result.push(
                    new vscode.Diagnostic(
                        makeLineRange(document, line),
                        "`rof` 缺少对应的 `for`。",
                        vscode.DiagnosticSeverity.Error
                    )
                );
            } else {
                stack.pop();
            }
            continue;
        }
    }

    for (const block of stack) {
        const closeWord = block.type === "if" ? "fi" : "rof";
        result.push(
            new vscode.Diagnostic(
                makeLineRange(document, block.line),
                `该代码块缺少结束关键字 \`${closeWord}\`。`,
                vscode.DiagnosticSeverity.Error
            )
        );
    }

    diagnostics.set(document.uri, result);
}

function buildIndent(level: number, options: vscode.FormattingOptions): string {
    const _ = options;
    return " ".repeat(level * 2);
}

function formatDocument(
    document: vscode.TextDocument,
    options: vscode.FormattingOptions
): vscode.TextEdit[] {
    let indentLevel = 0;
    const lines: string[] = [];
    let inBlockComment = false;

    for (let line = 0; line < document.lineCount; line++) {
        const raw = document.lineAt(line).text;
        const trimmed = raw.trim();
        const wasInBlockComment = inBlockComment;
        const hasInlineComment = /\/\//.test(raw);
        const hasBlockCommentMarker = raw.includes("/*") || raw.includes("*/");
        const commentAware = stripCommentsFromLine(raw, inBlockComment);
        inBlockComment = commentAware.inBlockComment;
        const codeOnly = commentAware.code;

        if (trimmed.length === 0) {
            lines.push("");
            continue;
        }

        // Keep block-comment text exactly as authored (including inner indentation).
        if (hasBlockCommentMarker || wasInBlockComment || inBlockComment) {
            lines.push(raw);
            continue;
        }

        const token = firstToken(codeOnly);
        const shouldDecreaseBefore = token === "fi" || token === "rof" || token === "elif" || token === "else";

        if (shouldDecreaseBefore) {
            indentLevel = Math.max(0, indentLevel - 1);
        }

        const shouldNormalizeCode =
            !hasInlineComment &&
            !hasBlockCommentMarker &&
            !wasInBlockComment &&
            !inBlockComment;
        const content = shouldNormalizeCode ? normalizeCodeLine(codeOnly) : trimmed;
        lines.push(`${buildIndent(indentLevel, options)}${content}`);

        const shouldIncreaseAfter =
            (token === "if" || token === "for" || token === "elif" || token === "else") && endsWithColon(codeOnly);

        if (shouldIncreaseAfter) {
            indentLevel += 1;
        }
    }

    const fullRange = new vscode.Range(
        document.positionAt(0),
        document.positionAt(document.getText().length)
    );

    return [vscode.TextEdit.replace(fullRange, lines.join("\n"))];
}

export function activate(context: vscode.ExtensionContext): void {
    const selector: vscode.DocumentSelector = { language: "form-python-ast" };
    const diagnostics = vscode.languages.createDiagnosticCollection("form-python-ast");

    void buildWorkspaceFunctionSignaturesWithEmbedded(context.extensionPath).then((map) => {
        FUNCTION_SIGNATURES.clear();
        for (const [name, signature] of map.entries()) {
            FUNCTION_SIGNATURES.set(name, signature);
        }
        DISCOVERED_APIS = [...map.keys()].sort();
    });

    const provider = vscode.languages.registerCompletionItemProvider(
        selector,
        {
            provideCompletionItems(
                document: vscode.TextDocument,
                position: vscode.Position
            ): vscode.ProviderResult<vscode.CompletionItem[]> {
                const linePrefix = document.lineAt(position).text.slice(0, position.character);
                const inExternal = hasUnclosedBraceContext(linePrefix);
                const externalArgContext = getExternalArgContext(linePrefix);
                const inFuncExternal = isInsideFuncExternal(document, position);
                const funcParenDepth = getCurrentFuncParenDepth(document, position);
                const funcApiItems = inFuncExternal && funcParenDepth === 0
                    ? buildFuncApiCompletions(linePrefix, position)
                    : [];

                if (inExternal) {
                    if (funcApiItems.length > 0) {
                        return funcApiItems;
                    }

                    if (externalArgContext) {
                        return getExternalArgumentCompletions(document, externalArgContext, linePrefix, position);
                    }

                    return buildBraceKeywordOnlyCompletions(linePrefix, position);
                }

                const ifConditionContext = getIfConditionContext(linePrefix);
                if (ifConditionContext) {
                    return buildIfConditionCompletions(document, ifConditionContext.conditionPrefix);
                }

                const items: vscode.CompletionItem[] = [];
                items.push(...KEYWORDS.map(keywordItem));
                items.push(...extractVariableNames(document).map(variableItem));
                return items;
            }
        },
        ".",
        "{",
        ",",
        " "
    );

    context.subscriptions.push(provider);

    const hoverProvider = vscode.languages.registerHoverProvider(selector, {
        provideHover(document, position) {
            const wordRange = document.getWordRangeAtPosition(position, /[A-Za-z_][A-Za-z0-9_.]*/);
            if (!wordRange) {
                return undefined;
            }

            const word = document.getText(wordRange);

            if (REF_TYPE_ASSERTION_WORDS.has(word) && isRefTypeAssertionPosition(document, wordRange)) {
                const md = new vscode.MarkdownString();
                md.appendMarkdown(`**${word}**\n\n${REF_TYPE_ASSERTION_TIP}`);
                return new vscode.Hover(md, wordRange);
            }

            if (isInsideFuncExternal(document, position)) {
                if (shouldShowFunctionHover(word)) {
                    const signature = FUNCTION_SIGNATURES.get(word);
                    if (!signature) {
                        return new vscode.Hover(buildFunctionFallbackHover(word), wordRange);
                    }
                    return new vscode.Hover(buildFunctionDetailHover(word, signature), wordRange);
                }

                if (DISCOVERED_APIS.includes(word)) {
                    return new vscode.Hover(buildFunctionFallbackHover(word), wordRange);
                }
            }

            const tip = HOVER_DOCS.get(word);
            if (!tip) {
                return undefined;
            }

            const md = new vscode.MarkdownString();
            md.appendMarkdown(`**${word}**\n\n${tip}`);
            return new vscode.Hover(md, wordRange);
        }
    });

    const formatter = vscode.languages.registerDocumentFormattingEditProvider(selector, {
        provideDocumentFormattingEdits(document, options) {
            return formatDocument(document, options);
        }
    });

    const signatureHelpProvider = vscode.languages.registerSignatureHelpProvider(
        selector,
        {
            provideSignatureHelp(document, position) {
                const forContext = getForHeaderSignatureContext(document, position);
                if (forContext) {
                    const help = new vscode.SignatureHelp();
                    const info = new vscode.SignatureInformation("for index: int, count: int:");
                    info.parameters = [
                        new vscode.ParameterInformation("index: int"),
                        new vscode.ParameterInformation("count: int")
                    ];
                    help.signatures = [info];
                    help.activeSignature = 0;
                    help.activeParameter = forContext.activeParameter;
                    return help;
                }

                const ifElifContext = getIfElifSignatureContext(document, position);
                if (ifElifContext) {
                    const help = new vscode.SignatureHelp();
                    const keyword = ifElifContext.keyword;
                    const info = new vscode.SignatureInformation(`${keyword} condition: bool:`);
                    info.parameters = [new vscode.ParameterInformation("condition: bool")];
                    help.signatures = [info];
                    help.activeSignature = 0;
                    help.activeParameter = 0;
                    return help;
                }

                const context = getFunctionCallContext(document, position);
                if (!context) {
                    return undefined;
                }

                const signature = FUNCTION_SIGNATURES.get(context.name);
                if (!signature) {
                    return undefined;
                }

                const help = new vscode.SignatureHelp();
                const info = new vscode.SignatureInformation(signature.label);
                info.parameters = signature.parameters.map((param) => new vscode.ParameterInformation(param));

                help.signatures = [info];
                help.activeSignature = 0;
                help.activeParameter = Math.min(
                    countCommas(context.argumentPrefix),
                    Math.max(0, signature.parameters.length - 1)
                );
                return help;
            }
        },
        "(",
        ",",
        " "
    );

    const updateDiagnostics = (doc: vscode.TextDocument) => validateDocument(doc, diagnostics);
    if (vscode.window.activeTextEditor?.document.languageId === "form-python-ast") {
        updateDiagnostics(vscode.window.activeTextEditor.document);
    }

    context.subscriptions.push(
        diagnostics,
        hoverProvider,
        formatter,
        signatureHelpProvider,
        vscode.workspace.onDidOpenTextDocument(updateDiagnostics),
        vscode.workspace.onDidChangeTextDocument((event) => updateDiagnostics(event.document)),
        vscode.workspace.onDidCloseTextDocument((doc) => diagnostics.delete(doc.uri))
    );
}

export function deactivate(): void {
    // no-op
}

