

class CppCompiler:
    HEADER = "/* Automatically compiled from Pa language */\n#include <palang.h>"
    def __init__(self, ast, exports=[], imports=[], intrinsics=["nil", "range", "print"]):
        self.root = ast
        self.exports = exports
        self.imports = imports
        self.intrinsics = intrinsics
    def append(self, src):
        self.src += src
    def enter_func(self):
        ns = dict(self.scope[-1])
        self.scope.append(ns)
        self.new_vars.append({})
    def leave_func(self):
        self.scope.pop()
        self.new_vars.pop()
    def define(self, var_name):
        self.scope[-1][var_name] = True
        self.new_vars[-1][var_name] = True
    def get_reset_new_vars(self):
        r = self.new_vars[-1].keys()
        self.new_vars[-1] = {}
        return r
    def compile(self):
        _global = {}
        for k in self.imports: _global[k] = True
        for k in self.exports: _global[k] = True
        for k in self.intrinsics: _global[k] = True
        self.scope = [_global, dict(_global)]
        self.new_vars = [{}]
        src = self._program(self.root)
        members = ""
        members += "".join(map(lambda x: "extern pa_value " + x + ";", self.imports))
        members += "".join(map(lambda x: "pa_value " + x + ";", self.exports))
        return "%s\n%s;int main(int argc, char** argv, char **env){PA_ENTER();%s;PA_LEAVE();}\n" % (CppCompiler.HEADER, members, src)
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
            sss = ""
            if t[0] == 'def_var':
                ss = self._expr_lvalue(t[1][1], define=True)
                s = ""
                for x in self.get_reset_new_vars():
                    s += "pa_value " + x + ";"
                sss += s + ss + '='
                sss += "([&]()->pa_value{" 
                for x in ast[1][1]:
                    sss += self._stat(x)
                sss += "})()"
            elif t[0] == 'def_func':
                raise Exception("Not implemented") 
            else:
                raise Exception("Semantic error")
            return sss
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
            self.enter_func() 
            src = ""
            ident = ast[1][0]
            val = ast[1][1]
            stats = ast[1][2]
            self.scope[-1][ident[1]] = True # make known. index var
            src += "{"
            src += "pa_value __for_ref__=" + self._expr(val) + ";"
            src += "pa_value __for_ref_len__=OP_LEN(__for_ref__);"
            src += "pa_value " + ident[1] + ";"
            src += "for(int64_t __for_index__ = 0; __for_index__ < __for_ref_len__.value.i64; __for_index__++){"
            src += ident[1] + "=OP_ITEM(__for_ref__, TYPE_INT(__for_index__));"
            src += "".join(map(self._stat, stats))
            src += "}}"
            self.leave_func()
            return src
        else:
            raise Exception("Semantic error")
    # Error catch - break/continue when not in loop
    def _stat_break(self, ast):
        return "break"
    def _stat_continue(self, ast):
        return "continue"
    def _stat_if(self, ast):
        if ast[0] == 'stat_if':
            src = ""
            meat = ast[1]
            for i, x in enumerate(meat):
                if i == 0:
                    src += "if(CBOOL(" + self._expr(x[0]) + ")){" + ("".join(map(self._stat, x[1]))) + "}"
                elif len(x) == 2:
                    src += "else if(CBOOL(" + self._expr(x[0]) + ")){" + ("".join(map(self._stat, x[1]))) + "}"
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
        if ast[0] == 'expr_lvalue':
            return self._expr_lvalue(ast[1])
        elif ast[0] == 'expr_func_call':
            fc = ast[1]
            __args = filter(lambda x: x[0] == 'expr', fc[1]) 
            __kwargs = filter(lambda x: x[0] == 'expr_func_kwarg', fc[1]) 
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
            return "FUNC_CALL(" + self._expr_lvalue(fc[0][1]) + ",TYPE_LIST(" + s_args + "),TYPE_DICT(" + s_kwargs + "))"
        elif ast[0] == 'INTEGER':
            return "TYPE_INT(" + str(ast[1]) + ")"
        elif ast[0] == 'REAL':
            return "TYPE_REAL(" + str(ast[1]) + ")"
        elif ast[0] == 'STRING':
            return "TYPE_STRING(\"" + ast[1] + "\")"
        elif ast[0] == 'VAR':
            src = ""
            for s in ast[1]:
                src += self._stat(s)
            return "([&]->pa_value{" + src + "})()"
        elif ast[0] == 'FUNC':
            src = ""
            args = ast[1][0]
            self.enter_func()
            for i, x in enumerate(args):
                var_name = x[1][0][1]
                self.scope[-1][var_name] = True
                if len(x[1]) == 1:
                    df = "nil"
                else:
                    df = self._expr(x[1][1])
                src += "pa_value " + var_name + "=PARAM(args,kwargs," + str(i) + ",\"" + var_name + "\"," + df + ");"
            for s in ast[1][1]:
                src += self._stat(s)
            self.leave_func()
            return "TYPE_FUNC([&](pa_value args, pa_value kwargs)->pa_value {" + src + "})"
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
            src = ""
            i = 0
            while True:
                src += opf[ast[i+1]] + '(' + self._expr_literal(ast[i]) + ','
                i += 2
                if (len(ast)-i) == 1:
                    src += self._expr_literal(ast[i])
                    src += ')' * (i/2)
                    break
            return src
    def _expr(self, ast):
        if ast[0] == 'expr':
            return self._expr_recur(ast[1])
        else:
            raise Exception("Semantic error")
    def _expr_lvalue(self, ast, define=False):
        if len(ast) == 1:
            var_name = ast[0][1] # IDENT
            if var_name in self.scope[-1]:
                return var_name
            else:
                if define:
                    self.define(var_name)
                    return var_name
                else:
                    raise Exception("No such variable in the scope: " + var_name)
        else:
            src = ""
            i = 0
            while True:
                if ast[i][0] == 'IDENT':
                    src += self._expr_lvalue([ast[i]], define=define)
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
              

        

def compile(ast, compiler=CppCompiler):
    return compiler(ast).compile()