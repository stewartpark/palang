class CppGenerator:
    HEADER = "/* Automatically compiled from Pa language */\n#include <palang.h>"
    ENTRYPOINT = "int main(int argc,char**argv,char**env){PA_ENTER(argc,argv,env);return PA_LEAVE(PA_INIT());}"
    def finalize(self, code, has_entrypoint=True):
        return "%s\nextern \"C\" pa_value_t* PA_INIT(){INTRINSICS();%s;};%s" % (CppGenerator.HEADER, code, CppGenerator.ENTRYPOINT if has_entrypoint else "")
    def cfunc_call(self, name, *args):
        return name + "(" + (",".join(args)) + ")"
    def func_call(self, name, *args, **kwargs):
        return self.cfunc_call("pa_function_call", name, self.literal_list(*args), self.literal_dict(*[self.literal_dict_kw(x,y) for x,y in kwargs]))
    def literal_nil(self):
        return self.cfunc_call("pa_new_nil")
    def literal_bool(self, v):
        return self.cfunc_call("pa_new_boolean", str(int(v)))
    def literal_int(self, v):
        return self.cfunc_call("pa_new_integer", str(v))
    def literal_real(self, v):
        return self.cfunc_call("pa_new_real", str(v))
    def literal_str(self, v):
        return self.cfunc_call("pa_new_string", "\"" + v + "\"")
    def literal_func(self, *args):
        return self.cfunc_call("pa_new_function", "[=](pa_value_t* args, pa_value_t* kwargs){" + ("".join(args)) + "}")
    def literal_list(self, *args):
        return self.cfunc_call("pa_new_list", *args)
    def literal_dict_kv(self, k, v):
        return self.cfunc_call("pa_new_dictionary_kv", k, v)
    def literal_dict(self, *args):
        return self.cfunc_call("pa_new_dictionary", *args)
    def literal_cstr(self, v):
        return "\"" + v + "\""
    def evaluate_multiline(self, *args):
        return "([=]() -> pa_value_t* {" + ("".join(args)) + "})()"
    def op(self, op, a, b=None, c=None):
        t_op = {
            'setitem': lambda: self.cfunc_call("pa_operator_setitem", a, b, c),
            'setattr': lambda: self.cfunc_call("pa_operator_setattr", a, b, c),
            'getitem': lambda: self.cfunc_call("pa_operator_getitem", a, b),
            'getattr': lambda: self.cfunc_call("pa_operator_getattr", a, b),
            '+': lambda: self.cfunc_call("pa_operator_add", a, b),
            '-': lambda: self.cfunc_call("pa_operator_subtract", a, b),
            '*': lambda: self.cfunc_call("pa_operator_multiply", a, b),
            '/': lambda: self.cfunc_call("pa_operator_divide", a, b),
            'mod': lambda: self.cfunc_call("pa_operator_modulo", a, b),
            'length': lambda: self.cfunc_call("pa_operator_length", a),
            '^': lambda: self.cfunc_call("pa_operator_power", a, b),
            '==': lambda: self.cfunc_call("pa_operator_eq", a, b),
            '!=': lambda: self.cfunc_call("pa_operator_neq", a, b),
            '>': lambda: self.cfunc_call("pa_operator_gt", a, b),
            '>=': lambda: self.cfunc_call("pa_operator_gte", a, b),
            '<': lambda: self.cfunc_call("pa_operator_lt", a, b),
            '<=': lambda: self.cfunc_call("pa_operator_lte", a, b),
            '->': lambda: self.cfunc_call("pa_operator_right", a, b),
            '<-': lambda: self.cfunc_call("pa_operator_left", a, b),
            'and': lambda: self.cfunc_call("pa_operator_and", a, b),
            'or': lambda: self.cfunc_call("pa_operator_or", a, b)
        }
        return t_op[op]()
    def cop(self, op, a, b=None, c=None):
        t_op = {
            '++': lambda: a + "++",
            '<': lambda: a + "<" + b
        }
        return t_op[op]()
    def var_name(self, v):
        return "_" + v
    def define_var(self, v, V=None):
        return "pa_value_t*  " + self.var_name(v)  + (("="+V) if V else "") + ";"
    def define_cvar(self, t, v, V=None):
        t_type = {
            'i64': 'int64_t'
        }
        return t_type[t] + " " + v + ("="+V if V else "")
    def raw_var(self, t, name):
        t_type = {
            'i64': 'i64'
        }
        return name + "->value." + t_type[t]
    def define_param(self, v, n, kw, df):
        return "pa_value_t* " + self.var_name(v) + " = " + self.cfunc_call("pa_get_argument", "args", "kwargs", str(n), self.literal_cstr(str(kw)), str(df)) + ";"
    def stat_assign(self, n, v):
        return n + "=" + v + ";"
    def stat_import(self, v):
        return self.cfunc_call("pa_import", "\"" + str(v) + "\"")
    def stat_ret(self, v):
        return "return " + v + ";"
    def stat_block(self, v):
        return "{" + v + "}"
    def stat_for(self, initial, condition, incremental, *args):
        return "for(" + initial + ";" + condition + ";" + incremental + "){" + ("".join(args)) + "}"
    def stat_while(self, condition, *args):
        return "while(" + (self.cfunc_call("pa_evaluate_into_boolean", condition)) + "){" + ("".join(args)) + "}" 
    def stat_if(self, condition, stats, else_stats=None):
        return "if(" + (self.cfunc_call("pa_evaluate_into_boolean", condition)) + "){" + stats + "}" + (("else{" + else_stats + "}") if else_stats else "")
    def stat_break(self):
        return "break"
    def stat_continue(self):
        return "continue"
    def finalize_line(self, v):
        return v + ";"
    


class Compiler:
    def __init__(self, ast, generator=CppGenerator(), exports=[], imports=[], intrinsics=["range", "print", "input", "len"], is_library=False):
        self.generator = generator
        self.root = ast
        self.exports = exports
        self.imports = imports
        self.intrinsics = intrinsics
        self.is_library = is_library
    def append(self, src):
        self.src += src
    def enter_func(self):
        ns = dict(self.scope[-1])
        for k in ns: 
            ns[k] = 'r' # Make variables outside the scope readable
        self.scope.append(ns)
        self.new_vars.append({})
        self.scope_prop.append('c') # The scope type is closure.
    def enter_loop(self):
        ns = dict(self.scope[-1]) # Copy as is.
        self.scope.append(ns)
        self.new_vars.append({})
        self.scope_prop.append('bl') # The scope type is a basic block + loop. (no closure)
    def leave_func(self):
        self.scope.pop()
        self.new_vars.pop()
        self.scope_prop.pop()
    def leave_loop(self):
        self.leave_func()
    def define(self, var_name, read_only=False, need_to_be_declared=True):
        self.scope[-1][var_name] = 'w' if not read_only else 'r' # Defined in the scope. writeable.
        if need_to_be_declared:
            self.new_vars[-1][var_name] = True
    def import_(self, lib_name, my_name, is_static=False):
        self.scope[-1][my_name] = 'xr' # External, read-only.
        self.imports.append([lib_name, my_name, is_static])
    def export_(self, var_name, my_name=None):
        self.scope[-1][var_name] = 'xw' # External, writeable. 
        if my_name:
            self.exports.append([var_name, my_name])
        else:
            self.exports.append([var_name, var_name])
    def get_reset_new_vars(self):
        r = self.new_vars[-1].keys()
        self.new_vars[-1] = {}
        return r
    def compile(self):
        _global = {}
        for k in self.intrinsics: _global[k] = 'xr'
        self.scope = [_global, dict(_global)]
        self.new_vars = [{}]
        self.scope_prop = ['c']
        src = self._program(self.root)

        src_def_export = ""
        for x in self.exports:
            src_def_export += self.generator.define_var(x[1])

        src_export = self.generator.literal_dict( 
            *map(lambda x: self.generator.literal_dict_kv(
                self.generator.literal_str(x[0]),
                self.generator.var_name(x[1])), self.exports)
        )
        return self.generator.finalize(
                (
                    src_def_export + 
                    src + 
                    self.generator.stat_ret(src_export)
                ),
                has_entrypoint=(not self.is_library)
        )
    # Rules
    def _program(self, ast):
        if ast[0] == 'program':
            src = ""
            for stat in ast[1]:
                src += self._stat(stat, topmost=True)
            return src
        else:
            raise Exception("Semantic error")
    def _stat(self, ast, topmost=False):
        if ast[0] == 'stat':
            stat_name = ast[1][0]
            stat_fn = {
                'stat_assign': self._stat_assign,
                'stat_expr': self._stat_expr,
                'stat_for': self._stat_for,
                'stat_while': self._stat_while,
                'stat_break': self._stat_break,
                'stat_continue': self._stat_continue,
                'stat_if': self._stat_if,
                'stat_ret': self._stat_ret,
                'stat_import': self._stat_import,
                'stat_export': self._stat_export
            }[stat_name]
            if stat_name in ['stat_export', 'stat_import'] and topmost == False:
                raise Exception("import/exports can be used only in the global scope.")
            return self.generator.finalize_line(stat_fn(ast[1]))
        else:
            raise Exception("Semantic error")
    def _stat_import(self, ast):
        if ast[0] == 'stat_import':
            src = ""
            for i in ast[1]:
                lib_name = i[0][1]
                if len(i) == 2:
                    name = i[1][1] 
                else:
                    name = lib_name.split('.')[-1]

                if name in self.scope[-1] and 'w' not in self.scope[-1][name]:
                    raise Exception("Assigning a library at a read-only variable.")
                if name not in self.scope[-1]:
                    src += self.generator.define_var(name) 
                src += self.generator.stat_assign(self.generator.var_name(name), self.generator.stat_import(lib_name))
                self.import_(lib_name, name)
            return src
        else:
            raise Exception("Semantic error")
    def _stat_export(self, ast):
        if ast[0] == 'stat_export':
            src = ""
            for i in ast[1]:
                my_name = i[0][1]
                if len(i) == 2:
                    name = i[1][1] 
                else:
                    name = my_name
                if my_name in self.scope[-1]:
                    raise Exception("Exporting a variable that is already defined in the scope.")
                self.export_(name, my_name)
            return src
        else:
            raise Exception("Semantic error")
    def _stat_assign(self, ast):
        if ast[0] == 'stat_assign':
            t = ast[1][0]
            if t[0] == 'def_var':
                self.enter_func()
                src = self.generator.evaluate_multiline(*[self._stat(x) for x in ast[1][1]])
                self.leave_func()
                
                src = self._expr_lvalue_assignment(t[1][1], src)
                def_vars = ""
                for x in self.get_reset_new_vars():
                    def_vars += self.generator.define_var(x) 
                src = def_vars + src
                return src
            elif t[0] == 'def_func':
                src = ""
                args = t[1][1]
                self._expr_lvalue_predefine(t[1][0][1])
                self.enter_func()
                for i, x in enumerate(args):
                    var_name = x[1][0][1]
                    if len(x[1]) == 1:
                        df = self.generator.literal_nil()
                    else:
                        df = self._expr(x[1][1])
                    src += self.generator.define_param(var_name, i, var_name, df)
                    self.define(var_name, need_to_be_declared=False)
                for s in ast[1][1]:
                    src += self._stat(s)
                self.leave_func()
                src = self._expr_lvalue_assignment(t[1][0][1], self.generator.literal_func(src))
                def_vars = ""
                for x in self.get_reset_new_vars():
                    def_vars += self.generator.define_var(x) 
                return def_vars + src
            else:
                raise Exception("Semantic error")
        else:
            raise Exception("Semantic error")
    def _stat_expr(self, ast):
        if ast[0] == 'stat_expr':
            if ast[1][0] == 'expr':
                return self._expr(ast[1])
            else:
                raise Exception("Semantic error")
        else:
            raise Exception("Semantic error")
    def _stat_for(self, ast):
        if ast[0] == 'stat_for':
            self.enter_loop() 
            ident = ast[1][0]
            val = ast[1][1]
            stats = ast[1][2]
            self.define(ident[1], read_only=True, need_to_be_declared=False) # make known. index var
            src = self.generator.stat_block(
                self.generator.define_var("_for_ref_", self._expr(val)) +
                self.generator.define_var("_for_ref_len_", self.generator.op("length", self.generator.var_name("_for_ref_"))) +
                self.generator.define_var(ident[1]) + 
                self.generator.stat_for(
                    self.generator.define_cvar("i64", "__for_index__", "0"),
                    self.generator.cop("<", "__for_index__", self.generator.raw_var("i64", self.generator.var_name("_for_ref_len_"))),
                    self.generator.cop("++", "__for_index__"),
                    self.generator.stat_assign(self.generator.var_name(ident[1]), self.generator.op("getitem", self.generator.var_name("_for_ref_"), self.generator.literal_int("__for_index__"))),
                    *map(self._stat, stats)
                )
            )
            self.leave_loop()
            return src
        else:
            raise Exception("Semantic error")
    def _stat_while(self, ast):
        if ast[0] == 'stat_while':
            self.enter_loop() 
            val = ast[1][0]
            stats = ast[1][1]
            src = self.generator.stat_while(self._expr(val), *map(self._stat, stats)) 
            self.leave_loop()
            return src
        else:
            raise Exception("Semantic error")
    def _stat_break(self, ast):
        if 'l' in self.scope_prop[-1]: # type should be l(loop)
            return self.generator.stat_break()
        else:
            raise Exception("Cannot use break outside a loop")
    def _stat_continue(self, ast):
        if 'l' in self.scope_prop[-1]: # type should be l(loop)
            return self.generator.stat_continue()
        else:
            raise Exception("Cannot use continue outside a loop")
    def _stat_if(self, ast):
        if ast[0] == 'stat_if':
            src = ""
            l = []
            meat = ast[1]
            for i, x in enumerate(meat):
                if i == 0:
                    l.append([self._expr(x[0]), "".join(map(self._stat, x[1]))])
                elif len(x) == 2:
                    l.append([self._expr(x[0]), "".join(map(self._stat, x[1]))])
                else:
                    l.append(["".join(map(self._stat, x[0]))])
            for x in range(len(l)-1,-1,-1):
                if len(l[x]) == 1:
                    src = l[x][0]
                else:
                    src = self.generator.stat_if(l[x][0], l[x][1], else_stats=src)
            return src
        else:
            raise Exception("Semantic error")
    def _stat_ret(self, ast):
        if ast[0] == 'stat_ret':
            return self.generator.stat_ret(self._expr(ast[1]));
    # Expressions
    def _expr_literal(self, ast):
        if ast[0] == 'expr_rvalue':
            return self._expr_rvalue(ast[1])
        elif ast[0] == 'BOOL':
            v = {'true': True, 'false': False, 'yes': True, 'no': False}[ast[1]]
            return self.generator.literal_bool(v) 
        elif ast[0] == 'NIL':
            return self.generator.literal_nil() 
        elif ast[0] == 'INTEGER':
            return self.generator.literal_int(str(ast[1]))
        elif ast[0] == 'REAL':
            return self.generator.literal_real(str(ast[1]))
        elif ast[0] == 'STRING':
            return self.generator.literal_str(ast[1])
        elif ast[0] == 'VAR':
            src = ""
            self.enter_func()
            for s in ast[1]:
                src += self._stat(s)
            self.leave_func()
            return self.generator.evaluate_multiline(src)
        elif ast[0] == 'FUNC':
            src = ""
            args = ast[1][0]
            self.enter_func()
            for i, x in enumerate(args):
                var_name = x[1][0][1]
                if len(x[1]) == 1:
                    df = self.generator.literal_nil() 
                else:
                    df = self._expr(x[1][1])
                src += self.generator.define_param(var_name, i, var_name, df)
                self.define(var_name, need_to_be_declared=False)
            for s in ast[1][1]:
                src += self._stat(s)
            self.leave_func()
            return self.generator.literal_func(src)
        elif ast[0] == 'LIST':
            return self.generator.literal_list(*map(self._expr, ast[1]))
        elif ast[0] == 'DICT':
            pass
        else:
            return self._expr_recur(ast)
    def _expr_recur(self, ast):
        if len(ast) == 0:
            return "0"
        elif len(ast) == 1:
            return self._expr_literal(ast[0])
        elif len(ast) == 2:
            if ast[0] == 'not':
                return self.generator.op("not", self._expr_literal(ast[1]))
            elif type(ast[1]) == str and ast[1] in '&!?':
                raise Exception("Not implemented")
            else:
                raise Exception("Semantic error")
        else:
            src = self._expr_literal(ast[0])
            i = 1
            while True:
                src = self.generator.op(ast[i], src, self._expr_literal(ast[i+1]))
                i += 2
                if len(ast) <= i:
                    break
            return src
    def _expr(self, ast):
        if ast[0] == 'expr':
            return self._expr_recur(ast[1])
        else:
            raise Exception("Semantic error")
    def _expr_lvalue(self, ast):
        var_name = ast[0][1] # IDENT
        if var_name in self.scope[-1]:
            if 'w' in self.scope[-1][var_name]:
                return self.generator.var_name(var_name)
            else:
                raise Exception("Variable is read-only in the scope: " + str(var_name))
        else:
            self.define(var_name)
            return self.generator.var_name(var_name)
    def _expr_lvalue_predefine(self, ast):
        if len(ast) == 1:
            self._expr_lvalue(ast) # just to see if the variable should be defined.
    def _expr_lvalue_assignment(self, ast, rvalue):
        src = ""
        i = 0
        while True:
            if len(ast) <= i+1:
                break # One element left!
            if ast[i][0] == 'IDENT':
                src += self._expr_rvalue([ast[i]])
            elif ast[i][0] == 'expr_lvalue_item':
                src = self.generator.op("getitem", src, self._expr(ast[i][1]))
            elif ast[i][0] == 'expr_lvalue_attr':
                src = self.generator.op("getattr", src, self.generator.literal_cstr(ast[i][1][1]))
            else:
                raise Exception("Semantic error")
            i += 1
        if ast[i][0] == 'IDENT':
            src = self.generator.stat_assign(self._expr_lvalue([ast[i]]), rvalue)
        elif ast[i][0] == 'expr_lvalue_item':
            src = self.generator.op("setitem", src, self._expr(ast[i][1]), rvalue)
        elif ast[i][0] == 'expr_lvalue_attr':
            src = self.generator.op("setattr", src, self.generator.literal_cstr(ast[i][1][1]), rvalue)
        return src
    def _expr_rvalue(self, ast):
        if len(ast) == 1:
            var_name = ast[0][1] # IDENT
            if var_name in self.scope[-1]:
                return self.generator.var_name(var_name)
            else:
                raise Exception("No such variable in the scope: " + var_name)
        else:
            src = ""
            i = 0
            while True:
                if ast[i][0] == 'IDENT':
                    src += self._expr_rvalue([ast[i]])
                elif ast[i][0] == 'expr_rvalue_item':
                    src = self.generator.op("getitem", src, self._expr(ast[i][1]))
                elif ast[i][0] == 'expr_rvalue_attr':
                    src = self.generator.op("getattr", src, self.generator.literal_cstr(ast[i][1][1]))
                elif ast[i][0] == 'expr_rvalue_call':
                    fargs = ast[i][1]
                    src = self.generator.func_call(src, 
                            *[self._expr(x) for x in filter(lambda x: x[0] == 'expr', fargs)], 
                            **{x[1][0][1]: self._expr(x[1][1]) for x in filter(lambda x: x[0] == 'expr_func_kwarg', fargs)}
                    )
                else:
                    raise Exception("Semantic error")
                i += 1
                if len(ast) <= i:
                    break
            return src
              

         

        

def compile(ast, compiler=Compiler, **kwargs):
    return compiler(ast, **kwargs).compile()
