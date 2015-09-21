

class CppCompiler:
    HEADER = "/* Automatically compiled from Pa language */\n#include <palang.h>"
    ENTRYPOINT = "int main(int argc,char**argv,char**env){PA_ENTER(argc,argv,env);return PA_LEAVE(PA_INIT());}"
    def __init__(self, ast, exports=[], imports=[], intrinsics=["nil", "range", "print", "input"], is_library=False):
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
    def define(self, var_name):
        self.scope[-1][var_name] = 'w' # Defined in the scope. writeable.
        self.new_vars[-1][var_name] = True
    def get_reset_new_vars(self):
        r = self.new_vars[-1].keys()
        self.new_vars[-1] = {}
        return r
    def compile(self):
        _global = {}
        for k in self.imports: _global[k] = 'r'
        for k in self.exports: _global[k] = 'w'
        for k in self.intrinsics: _global[k] = 'r'
        self.scope = [_global, dict(_global)]
        self.new_vars = [{}]
        self.scope_prop = ['c']
        src = self._program(self.root)
        members = ""
        members += "".join(map(lambda x: "extern pa_value* " + x + ";", self.imports))
        members += "".join(map(lambda x: "pa_value* " + x + ";", self.exports))
        return "%s\n%s;pa_value*PA_INIT(){pa_value* __ret__=nil;%s;return __ret__;};%s" % (CppCompiler.HEADER, members, src, CppCompiler.ENTRYPOINT if not self.is_library else "")
    # Rules
    def _program(self, ast):
        if ast[0] == 'program':
            src = ""
            for stat in ast[1]:
                src += self._stat(stat)
            return src
        else:
            raise Exception("Semantic error")
    def _stat(self, ast):
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
                'stat_ret': self._stat_ret
            }[stat_name]
            return stat_fn(ast[1]) + ';'
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
                    def_vars += "pa_value *" + x + ";"
                src += def_vars + lv + '='
                src += "([=]()->pa_value*{" #FUNC 
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
                    def_vars += "pa_value *" + x + ";"
                args = t[1][1]
                self.enter_func()
                for i, x in enumerate(args):
                    var_name = x[1][0][1]
                    self.scope[-1][var_name] = 'w'
                    if len(x[1]) == 1:
                        df = "nil"
                    else:
                        df = self._expr(x[1][1])
                    src += "pa_value*" + var_name + "=PARAM(args,kwargs," + str(i) + ",\"" + var_name + "\"," + df + ");"
                for s in ast[1][1]:
                    src += self._stat(s)
                self.leave_func()
                return def_vars + lv + "=TYPE_FUNC([=](pa_value *args, pa_value *kwargs)->pa_value* {" + src + "})" #FUNC
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
            self.scope[-1][ident[1]] = 'r' # make known. index var
            src += "{"
            src += "pa_value *__for_ref__=" + self._expr(val) + ";"
            src += "pa_value *__for_ref_len__=OP_LEN(__for_ref__);"
            src += "pa_value *" + ident[1] + ";"
            src += "for(int64_t __for_index__ = 0; __for_index__ < __for_ref_len__->value.i64; __for_index__++){"
            src += ident[1] + "=OP_ITEM(__for_ref__, TYPE_INT(__for_index__));"
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
            src += "while(LEXPR(" + self._expr(val) + ")){"
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
                    src += "if(LEXPR(" + self._expr(x[0]) + ")){" + ("".join(map(self._stat, x[1]))) + "}"
                elif len(x) == 2:
                    src += "else if(LEXPR(" + self._expr(x[0]) + ")){" + ("".join(map(self._stat, x[1]))) + "}"
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
        elif ast[0] == 'INTEGER':
            return "TYPE_INT(" + str(ast[1]) + ")"
        elif ast[0] == 'REAL':
            return "TYPE_REAL(" + str(ast[1]) + ")"
        elif ast[0] == 'STRING':
            return "TYPE_STRING(\"" + ast[1] + "\")"
        elif ast[0] == 'VAR':
            src = ""
            self.enter_func()
            for s in ast[1]:
                src += self._stat(s)
            self.leave_func()
            return "([=]()->pa_value*{" + src + "})()" #FUNC
        elif ast[0] == 'FUNC':
            src = ""
            args = ast[1][0]
            self.enter_func()
            for i, x in enumerate(args):
                var_name = x[1][0][1]
                self.scope[-1][var_name] = 'w'
                if len(x[1]) == 1:
                    df = "nil"
                else:
                    df = self._expr(x[1][1])
                src += "pa_value*" + var_name + "=PARAM(args,kwargs," + str(i) + ",\"" + var_name + "\"," + df + ");"
            for s in ast[1][1]:
                src += self._stat(s)
            self.leave_func()
            return "TYPE_FUNC([=](pa_value *args, pa_value *kwargs)->pa_value* {" + src + "})" #FUNC
        elif ast[0] == 'LIST':
            return "TYPE_LIST(" + ",".join(map(self._expr, ast[1])) + ")"
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
                return "OP_NOT(" + self._expr_literal(ast[1]) + ")"
            elif type(ast[1]) == str and ast[1] in '&!?':
                raise Exception("Not implemented")
            else:
                raise Exception("Semantic error")
        else:
            opf = {
                '+': 'OP_ADD',
                '-': 'OP_SUB',
                '*': 'OP_MUL',
                '/': 'OP_DIV',
                'mod': 'OP_MOD',
                '^': 'OP_POW',
                '==': 'OP_EQ',
                '!=': 'OP_NEQ',
                '>': 'OP_GT',
                '>=': 'OP_GTE',
                '<': 'OP_LT',
                '<=': 'OP_LTE',
                '->': 'OP_RIGHT',
                '<-': 'OP_LEFT',
                'and': 'OP_AND',
                'or': 'OP_OR'
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
                if self.scope[-1][var_name] == 'w':
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
                    src = "OP_ITEM(" + src + "," + self._expr(ast[i][1]) + ")"
                elif ast[i][0] == 'expr_lvalue_attr':
                    src = "OP_ATTR(" + src + "," + self._expr(ast[i][1]) + ")"
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
                    src = "OP_ITEM(" + src + "," + self._expr(ast[i][1]) + ")"
                elif ast[i][0] == 'expr_rvalue_attr':
                    src = "OP_ATTR(" + src + "," + self._expr(ast[i][1]) + ")"
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
                        s_kwargs += "TYPE_DICT_KV(TYPE_STRING(\"" + x[1][0][1] + "\")," + self._expr(x[1][1]) + "),"
                    s_kwargs = s_kwargs[:-1]
                    src ="FUNC_CALL(" + src + ",TYPE_LIST(" + s_args + "),TYPE_DICT(" + s_kwargs + "))"
                else:
                    raise Exception("Semantic error")
                i += 1
                if len(ast) <= i:
                    break
            return src
              

         

        

def compile(ast, compiler=CppCompiler, **kwargs):
    return compiler(ast, **kwargs).compile()
