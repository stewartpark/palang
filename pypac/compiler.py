

class CppCompiler:
    HEADER = "/* Automatically compiled from Pa language */\n#include <palang.h>"
    ENTRYPOINT = "int main(int argc,char**argv,char**env){PA_ENTER(argc,argv,env);return PA_LEAVE(PA_INIT());}"
    def __init__(self, ast, exports=[], imports=[], intrinsics=["range", "print", "input", "len"], is_library=False):
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
            src_def_export += "pa_value_t*" + x[1] + ";"
        src_export = "pa_new_dictionary("
        src_export += ",".join(map(lambda x: "pa_new_dictionary_kv(pa_new_string(\"" + x[0] + "\")," + x[1] + ")", self.exports))  
        src_export += ")"
        return "%s\nextern \"C\" pa_value_t*PA_INIT(){INTRINSICS();%s;%s;return %s;};%s" % (CppCompiler.HEADER, src_def_export, src, src_export, CppCompiler.ENTRYPOINT if not self.is_library else "")
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
            return stat_fn(ast[1]) + ';'
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
                    src += "pa_value_t*" + name + ";"
                src += name + "=pa_import(\"" + lib_name + "\");"
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
                self.export_(name, my_name)
            return src
        else:
            raise Exception("Semantic error")
    def _stat_assign(self, ast):
        if ast[0] == 'stat_assign':
            t = ast[1][0]
            if t[0] == 'def_var':
                src = ""
                lv = self._expr_lvalue(t[1][1])
                def_vars = ""
                for x in self.get_reset_new_vars():
                    def_vars += "pa_value_t *" + x + ";"
                src += def_vars + lv + '='
                src += "([=]()->pa_value_t*{" #FUNC 
                self.enter_func()
                for x in ast[1][1]:
                    src += self._stat(x)
                self.leave_func()
                src += "})()"
                return src
            elif t[0] == 'def_func':
                src = ""
                lv = self._expr_lvalue(t[1][0][1])
                def_vars = ""
                for x in self.get_reset_new_vars():
                    def_vars += "pa_value_t *" + x + ";"
                args = t[1][1]
                self.enter_func()
                for i, x in enumerate(args):
                    var_name = x[1][0][1]
                    if len(x[1]) == 1:
                        df = "pa_new_nil()"
                    else:
                        df = self._expr(x[1][1])
                    src += "pa_value_t*" + var_name + "=pa_get_argument(args,kwargs," + str(i) + ",\"" + var_name + "\"," + df + ");"
                    self.define(var_name, need_to_be_declared=False)
                for s in ast[1][1]:
                    src += self._stat(s)
                self.leave_func()
                return def_vars + lv + "=pa_new_function([=](pa_value_t *args, pa_value_t *kwargs)->pa_value_t* {" + src + "})" #FUNC
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
            src = ""
            ident = ast[1][0]
            val = ast[1][1]
            stats = ast[1][2]
            self.define(ident[1], read_only=True, need_to_be_declared=False) # make known. index var
            src += "{"
            src += "pa_value_t *__for_ref__=" + self._expr(val) + ";"
            src += "pa_value_t *__for_ref_len__=pa_operator_length(__for_ref__);"
            src += "pa_value_t *" + ident[1] + ";"
            src += "for(int64_t __for_index__ = 0; __for_index__ < __for_ref_len__->value.i64; __for_index__++){"
            src += ident[1] + "=pa_operator_getitem(__for_ref__, pa_new_integer(__for_index__));"
            src += "".join(map(self._stat, stats))
            src += "}}"
            self.leave_loop()
            return src
        else:
            raise Exception("Semantic error")
    def _stat_while(self, ast):
        if ast[0] == 'stat_while':
            self.enter_loop() 
            src = ""
            val = ast[1][0]
            stats = ast[1][1]
            src += "while(pa_evaluate_into_boolean(" + self._expr(val) + ")){"
            src += "".join(map(self._stat, stats))
            src += "}"
            self.leave_loop()
            return src
        else:
            raise Exception("Semantic error")
    def _stat_break(self, ast):
        if 'l' in self.scope_prop[-1]: # type should be l(loop)
            return "break"
        else:
            raise Exception("Cannot use break outside a loop")
    def _stat_continue(self, ast):
        if 'l' in self.scope_prop[-1]: # type should be l(loop)
            return "continue"
        else:
            raise Exception("Cannot use continue outside a loop")
    def _stat_if(self, ast):
        if ast[0] == 'stat_if':
            src = ""
            meat = ast[1]
            for i, x in enumerate(meat):
                if i == 0:
                    src += "if(pa_evaluate_into_boolean(" + self._expr(x[0]) + ")){" + ("".join(map(self._stat, x[1]))) + "}"
                elif len(x) == 2:
                    src += "else if(pa_evaluate_into_boolean(" + self._expr(x[0]) + ")){" + ("".join(map(self._stat, x[1]))) + "}"
                else:
                    src += "else{" + ("".join(map(self._stat, x[0]))) + "}"
            return src
        else:
            raise Exception("Semantic error")
    def _stat_ret(self, ast):
        if ast[0] == 'stat_ret':
            return "return " + self._expr(ast[1]);
    # Expressions
    def _expr_literal(self, ast):
        if ast[0] == 'expr_rvalue':
            return self._expr_rvalue(ast[1])
        elif ast[0] == 'BOOL':
            v = {'true': 'true', 'false': 'false', 'yes': 'true', 'no': 'false'}[ast[1]]
            return 'pa_new_boolean(' + v + ')'
        elif ast[0] == 'NIL':
            return 'pa_new_nil()'
        elif ast[0] == 'INTEGER':
            return "pa_new_integer(" + str(ast[1]) + ")"
        elif ast[0] == 'REAL':
            return "pa_new_real(" + str(ast[1]) + ")"
        elif ast[0] == 'STRING':
            return "pa_new_string(\"" + ast[1] + "\")"
        elif ast[0] == 'VAR':
            src = ""
            self.enter_func()
            for s in ast[1]:
                src += self._stat(s)
            self.leave_func()
            return "([=]()->pa_value_t*{" + src + "})()" #FUNC
        elif ast[0] == 'FUNC':
            src = ""
            args = ast[1][0]
            self.enter_func()
            for i, x in enumerate(args):
                var_name = x[1][0][1]
                if len(x[1]) == 1:
                    df = "pa_new_nil()"
                else:
                    df = self._expr(x[1][1])
                src += "pa_value_t*" + var_name + "=pa_get_argument(args,kwargs," + str(i) + ",\"" + var_name + "\"," + df + ");"
                self.define(var_name, need_to_be_declared=False)
            for s in ast[1][1]:
                src += self._stat(s)
            self.leave_func()
            return "pa_new_function([=](pa_value_t *args, pa_value_t *kwargs)->pa_value_t* {" + src + "})" #FUNC
        elif ast[0] == 'LIST':
            return "pa_new_list(" + ",".join(map(self._expr, ast[1])) + ")"
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
                return "pa_operator_not(" + self._expr_literal(ast[1]) + ")"
            elif type(ast[1]) == str and ast[1] in '&!?':
                raise Exception("Not implemented")
            else:
                raise Exception("Semantic error")
        else:
            opf = {
                '+': 'pa_operator_add',
                '-': 'pa_operator_subtract',
                '*': 'pa_operator_multiply',
                '/': 'pa_operator_divide',
                'mod': 'pa_operator_modulo',
                '^': 'pa_operator_power',
                '==': 'pa_operator_eq',
                '!=': 'pa_operator_neq',
                '>': 'pa_operator_gt',
                '>=': 'pa_operator_gte',
                '<': 'pa_operator_lt',
                '<=': 'pa_operator_lte',
                '->': 'pa_operator_right',
                '<-': 'pa_operator_left',
                'and': 'pa_operator_and',
                'or': 'pa_operator_or'
            }
            src = self._expr_literal(ast[0])
            i = 1
            while True:
                src = opf[ast[i]] + '(' + src + ',' + self._expr_literal(ast[i+1]) + ')'
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
        if len(ast) == 1:
            var_name = ast[0][1] # IDENT
            if var_name in self.scope[-1]:
                if 'w' in self.scope[-1][var_name]:
                    return var_name
                else:
                    raise Exception("Variable is read-only in the scope: " + str(var_name))
            else:
                self.define(var_name)
                return var_name
        else:
            src = ""
            i = 0
            while True:
                if ast[i][0] == 'IDENT':
                    src += self._expr_lvalue([ast[i]])
                elif ast[i][0] == 'expr_lvalue_item':
                    src = "pa_operator_setitem(" + src + "," + self._expr(ast[i][1]) + ")"
                elif ast[i][0] == 'expr_lvalue_attr':
                    src = "pa_operator_setattr(" + src + ",\"" + ast[i][1][1] + "\")"
                else:
                    raise Exception("Semantic error")
                i += 1
                if len(ast) <= i:
                    break
            return src
    def _expr_rvalue(self, ast):
        if len(ast) == 1:
            var_name = ast[0][1] # IDENT
            if var_name in self.scope[-1]:
                return var_name
            else:
                raise Exception("No such variable in the scope: " + var_name)
        else:
            src = ""
            i = 0
            while True:
                if ast[i][0] == 'IDENT':
                    src += self._expr_rvalue([ast[i]])
                elif ast[i][0] == 'expr_rvalue_item':
                    src = "pa_operator_getitem(" + src + "," + self._expr(ast[i][1]) + ")"
                elif ast[i][0] == 'expr_rvalue_attr':
                    src = "pa_operator_getattr(" + src + ",\"" + ast[i][1][1] + "\")"
                elif ast[i][0] == 'expr_rvalue_call':
                    fargs = ast[i][1]
                    __args = filter(lambda x: x[0] == 'expr', fargs) 
                    __kwargs = filter(lambda x: x[0] == 'expr_func_kwarg', fargs)
                    # args
                    s_args = ""
                    for x in __args:
                        s_args += self._expr(x) + ","
                    s_args = s_args[:-1]
                    # kwargs
                    s_kwargs = ""
                    for x in __kwargs:
                        s_kwargs += "pa_new_dictionary_kv(pa_new_string(\"" + x[1][0][1] + "\")," + self._expr(x[1][1]) + "),"
                    s_kwargs = s_kwargs[:-1]
                    src ="pa_function_call(" + src + ",pa_new_list(" + s_args + "),pa_new_dictionary(" + s_kwargs + "))"
                else:
                    raise Exception("Semantic error")
                i += 1
                if len(ast) <= i:
                    break
            return src
              

         

        

def compile(ast, compiler=CppCompiler, **kwargs):
    return compiler(ast, **kwargs).compile()
