const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const extensionRoot = path.resolve(__dirname, "..");
const compiledExtension = fs.readFileSync(path.join(extensionRoot, "out/extension.js"), "utf8");

class MarkdownString {
    value = "";

    appendMarkdown(text) {
        this.value += text;
        return this;
    }

    appendCodeblock(text, language) {
        this.value += `\n\`\`\`${language}\n${text}\n\`\`\`\n`;
        return this;
    }
}

function loadExtension(workspaceSource) {
    const vscode = {
        MarkdownString,
        workspace: {
            findFiles: async (pattern) => workspaceSource && pattern === "static/lib_*.py"
                ? [{ fsPath: "static/lib_test.py" }]
                : [],
            fs: { readFile: async () => Buffer.from(workspaceSource) }
        }
    };
    // Run the compiled extension with only the VS Code API replaced, without a running editor.
    const context = vm.createContext({
        exports: {},
        Buffer,
        require: (name) => name === "vscode" ? vscode : require(name)
    });
    vm.runInContext(compiledExtension, context, { filename: "extension.js" });
    return context;
}

function readHover(extension, signatures, name) {
    const signature = signatures.get(name);
    assert.ok(signature, `Missing signature for ${name}`);
    return extension.buildFunctionDetailHover(name, signature).value;
}

test("embedded reflect functions with registration comments retain their documentation and types", async () => {
    const extension = loadExtension();
    const signatures = await extension.buildWorkspaceFunctionSignaturesWithEmbedded(extensionRoot);
    const expected = [
        ["vars", "ptr: int", "int", "vars 是已被弃用的特性"],
        ["dir", "ptr: int", "int", "dir 是已被弃用的特性"],
        ["hasattr", "ptr: int, attr: str", "bool", "hasattr 检查对象是否拥有 attr 指示的属性"],
        ["getattr", "ptr: int, attr: str", "int", "getattr 是已被弃用的特性"],
        ["setattr", "obj_ptr: int, obj_attr: str, value_ptr: int", "bool", "setattr 是已被弃用的特性"],
        ["delattr", "ptr: int, attr: str", "bool", "delattr 是已被弃用的特性"],
        ["call", "func_ptr: int, arg_ptrs: Any", "int | str", "call 是已被弃用的特性"]
    ];
    for (const [method, params, returnType, description] of expected) {
        const name = `reflect.${method}`;
        const signature = signatures.get(name);
        const hover = readHover(extension, signatures, name);
        assert.equal(signature.label, `${name}(${params})`);
        assert.equal(signature.returnType, returnType);
        assert.ok(hover.includes(description), `Missing description for ${name}`);
        assert.ok(hover.includes("**说明**"));
    }
});

test("long embedded docstrings produce summaries and return types", async () => {
    const extension = loadExtension();
    const signatures = await extension.buildWorkspaceFunctionSignaturesWithEmbedded(extensionRoot);
    const expected = [
        ["json.dumps", "Serialize ``obj`` to a JSON formatted ``str``.", "str"],
        ["time.strftime", "strftime converts a time tuple to a string according to a format specification.", "str"],
        ["object.ref_type", "ref_type 返回 ptr 指向对象的类型", "int"]
    ];
    for (const [name, description, returnType] of expected) {
        assert.ok(readHover(extension, signatures, name).includes(description), name);
        assert.equal(signatures.get(name).returnType, returnType, name);
    }
    assert.equal(signatures.get("json.dumps").parameters[0], "ptr");
});

test("workspace documentation overrides embedded documentation and skips leading comments", async () => {
    const extension = loadExtension(`
class CustomReflect:
    def call(self, value):  # type: (str) -> bool
        # A comment before the docstring.

        '''Call the workspace implementation.'''
        return True

    def build_func(self):
        funcs["reflect.call"] = self.call  # Workspace override
`);
    const signatures = await extension.buildWorkspaceFunctionSignaturesWithEmbedded(extensionRoot);
    assert.equal(signatures.get("reflect.call").source, "workspace");
    assert.equal(signatures.get("reflect.call").label, "reflect.call(value: str)");
    assert.ok(readHover(extension, signatures, "reflect.call").includes("Call the workspace implementation."));
});

test("undocumented methods do not borrow a later method's docstring", async () => {
    const extension = loadExtension(`
class Example:
    def undocumented(self, value):  # type: (int) -> int
        return value

    def documented(self, value):  # type: (str) -> str
        """Describe only this method."""
        return value

    def build_func(self):
        funcs["example.undocumented"] = self.undocumented
        funcs["example.documented"] = self.documented
`);
    const signatures = await extension.buildWorkspaceFunctionSignaturesWithEmbedded(extensionRoot);
    assert.equal(signatures.get("example.undocumented").description, undefined);
    assert.ok(!readHover(extension, signatures, "example.undocumented").includes("**说明**"));
    assert.ok(readHover(extension, signatures, "example.documented").includes("Describe only this method."));
});

test("plain registrations, aliases and lambda string defaults still produce signatures", async () => {
    const extension = loadExtension(`
class Example:
    def method(self, value):  # type: (int) -> int
        """Describe the method."""
        return value

    def build_func(self):
        funcs["example.plain"] = self.method
        funcs["example.lambda"] = lambda value="text": value + "#"
        funcs["example.alias"], funcs["example.alias2"] = (
            self.method,
            self.method,
        )

        for key, value in funcs.items():
            origin[key] = value
`);
    const signatures = await extension.buildWorkspaceFunctionSignaturesWithEmbedded(extensionRoot);
    for (const name of ["example.plain", "example.alias", "example.alias2"]) {
        assert.equal(signatures.get(name).label, `${name}(value: int)`);
        assert.ok(readHover(extension, signatures, name).includes("Describe the method."));
    }
    assert.equal(signatures.get("example.lambda").label, 'example.lambda(value="text")');
});
