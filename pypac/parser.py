from pyparsing import *

ParserElement.enablePackrat()

# Grammatical components
LPAREN, RPAREN, LBRACK, RBRACK, LBRACE, RBRACE, COLON =\
map(Suppress,"()[]{}:")
COMMA, DOT, OP_ASSIGN = map(Suppress, ",.=")
NEWLINE = Suppress(";")

COMMENT = Literal('#') + restOfLine

# Literals
#FIXME Ident shouldn't be matched if it's a reserved keyword
IDENT = Regex(r'[a-zA-Z_][a-zA-Z0-9_]*')\
        .setParseAction(lambda t: ["IDENT", t[0]])
PACKAGE_NAME = Combine(Regex(r'[a-zA-Z_][a-zA-Z0-9_]*') + ZeroOrMore(Literal(".") + Regex(r'[a-zA-Z_][a-zA-Z0-9_]*'))).setParseAction(lambda t: ["PACKAGE_NAME", t[0]])
NIL     = Literal("nil").setParseAction(lambda t: ["NIL", t[0]])
INTEGER = Combine(Optional(oneOf("+ -")) + Word(nums))\
    .setName("integer")\
    .setParseAction(lambda t: ["INTEGER", int(t[0])])
REAL    = Combine(Optional(oneOf("+ -")) + Word(nums) + "." +
               Optional(Word(nums)) +
               Optional(oneOf("e E")+Optional(oneOf("+ -")) +Word(nums)))\
    .setName("real")\
    .setParseAction(lambda t: ["REAL", float(t[0])])
STRING  = QuotedString('"', multiline=False)\
        .setName("string")\
        .setParseAction(lambda t: ["STRING", t[0]])
BOOL    = (Literal("true") | Literal("false") | Literal('yes') | Literal('no')).setParseAction(lambda t: ["BOOL", t[0]])
LIST    = Forward()
DICT    = Forward()
FUNC    = Forward()
VAR     = Forward()

# General rules
expr = Forward()
stat = Forward()
stat_ret = Forward()
stat_one_line = Group(stat_ret).setParseAction(lambda t: ['stat', t[0]])


# L-value expression
expr_lvalue_item = Group(LBRACK + expr + RBRACK)\
        .setParseAction(lambda t: ["expr_lvalue_item", t[0]])
expr_lvalue_attr = Group(DOT + IDENT)\
        .setParseAction(lambda t: ["expr_lvalue_attr", t[0]])
expr_lvalue = Group(Group(IDENT) + ZeroOrMore(Group(expr_lvalue_item|expr_lvalue_attr)))\
        .setParseAction(lambda t: ["expr_lvalue", t[0]])

expr_rvalue_item = Group(LBRACK + expr + RBRACK)\
        .setParseAction(lambda t: ["expr_rvalue_item", t[0]])
expr_rvalue_attr = Group(DOT + IDENT)\
        .setParseAction(lambda t: ["expr_rvalue_attr", t[0]])

expr_func_kwarg = Group(Group(IDENT) + OP_ASSIGN + Group(expr)).setParseAction(lambda t: ['expr_func_kwarg', t[0]])
expr_rvalue_call = (LPAREN + Group(Optional(delimitedList(Group(expr_func_kwarg|expr)))) + RPAREN)\
        .setParseAction(lambda t: ["expr_rvalue_call", t[0]])

expr_rvalue = Group(Group(IDENT) + ZeroOrMore(Group(expr_rvalue_item|expr_rvalue_attr|expr_rvalue_call)))\
        .setParseAction(lambda t: ["expr_rvalue", t[0]])

def_var = Group(expr_lvalue)\
        .setParseAction(lambda t: ["def_var", t[0]])

def_stat_block = (Group(stat_one_line))|(LBRACE + ZeroOrMore(Group(stat)) + RBRACE)
def_func_arg = Group(Group(IDENT) + Optional(OP_ASSIGN + Group(expr))).setParseAction(lambda t: ['def_func_arg', t[0]])
def_func_args = LPAREN + Optional(delimitedList(Group(def_func_arg))) + RPAREN
def_func = Group(Group(expr_lvalue) + Group(def_func_args))\
        .setParseAction(lambda t: ["def_func", t[0]])

expr_literal = Group(BOOL | NIL | REAL | INTEGER | STRING | LIST | DICT | FUNC | VAR | expr_rvalue)


LIST << Group(LBRACK + Optional(delimitedList(Group(expr))) + RBRACK)\
        .setParseAction(lambda t: ["LIST", t[0]])

DICT << Group(LBRACE + Optional(delimitedList(Group(expr_literal) + COLON + Group(expr))) + RBRACE)\
        .setParseAction(lambda t: ["DICT", t[0]])

FUNC << Group(Suppress("func") + Group(def_func_args) + Group(def_stat_block)).setParseAction(lambda t: ["FUNC", t[0]])

VAR << Group(Suppress("var") + def_stat_block).setParseAction(lambda t: ["VAR", t[0]])

# Expression
expr << Group(operatorPrecedence(expr_literal, [
        (oneOf("new"), 1, opAssoc.RIGHT),
        (oneOf("* / mod"), 2, opAssoc.LEFT),
        (oneOf("+ -"), 2, opAssoc.LEFT),
        (oneOf("== != > >= < <="), 2, opAssoc.LEFT),
        (oneOf("-> <-"), 2, opAssoc.LEFT),
        (oneOf("not"), 1, opAssoc.RIGHT),
        (oneOf("and"), 2, opAssoc.LEFT),
        (oneOf("or"), 2, opAssoc.LEFT),
        (oneOf("& ? !"), 1, opAssoc.LEFT),
])).setParseAction(lambda t: ["expr", t[0]])

# Statements
stat_class_constructor = Group(Suppress("constructor") + Group(def_func_args) + Group(def_stat_block)).setParseAction(lambda t: ["stat_class_constructor", t[0]])
stat_class_deconstructor = Group(Suppress("deconstructor") + Group(def_func_args) + Group(def_stat_block)).setParseAction(lambda t: ["stat_class_deconstructor", t[0]])
stat_class_method = Group(Suppress("method") + Group(IDENT) + Group(def_func_args) + Group(def_stat_block)).setParseAction(lambda t: ["stat_class_method", t[0]])
stat_class_operator = Group(Suppress("operator") + Group(oneOf("* / mod + - == != > >= < <= -> <- not and or & ? ! getattr setattr getitem setitem")) + Group(def_func_args) + Group(def_stat_block)).setParseAction(lambda t: ["stat_class_operator", t[0]])
stat_class_property = Group(Suppress("property") + Group(IDENT) + Group(def_stat_block)).setParseAction(lambda t: ["stat_class_property", t[0]])
stat_def_class = Group(Suppress("class") + Group(IDENT) + LBRACE + Group(ZeroOrMore(Group(stat_class_method|stat_class_operator|stat_class_property|stat_class_constructor|stat_class_deconstructor))) + RBRACE).setParseAction(lambda t: ["stat_def_class", t[0]])

expr_stat_block = ((COMMA + Group(stat))|(LBRACE + ZeroOrMore(Group(stat)) + RBRACE))
stat_if = Group(Suppress("if") + Group(Group(expr) + Group(expr_stat_block)) + ZeroOrMore(Group(Suppress("elif") + Group(expr) + Group(expr_stat_block))) + Optional(Group(Suppress("else") + Group(expr_stat_block)))).setParseAction(lambda t: ["stat_if", t[0]])
stat_for = Group(Suppress("for") + Group(IDENT) + Suppress("in") + Group(expr) + Group(expr_stat_block)).setParseAction(lambda t: ["stat_for", t[0]])
stat_while = Group(Suppress("while") + Group(expr) + Group(expr_stat_block)).setParseAction(lambda t: ["stat_while", t[0]])
stat_assign = Group(Group(def_func|def_var) + Group(def_stat_block)).setParseAction(lambda t: ["stat_assign", t[0]])
stat_ret << Group(OP_ASSIGN + expr).setParseAction(lambda t: ["stat_ret", t[0]])
stat_expr = Group(expr).setParseAction(lambda t: ["stat_expr", t[0]])
stat_break = Group(Suppress("break")).setParseAction(lambda t: ["stat_break"])
stat_continue = Group(Suppress("continue")).setParseAction(lambda t: ["stat_continue"])
stat_import = Group(Suppress("import") + Group(Group(PACKAGE_NAME) + Optional(Group(Suppress("as") + IDENT)))).setParseAction(lambda t: ["stat_import", t[0]])
stat_export = Group(Suppress("export") + Group(Group(IDENT) + Optional(Group(Suppress("as") + IDENT)))).setParseAction(lambda t: ["stat_export", t[0]])
stat << Group((stat_def_class | stat_import | stat_export | stat_if | stat_for | stat_while | stat_break | stat_continue | stat_assign | stat_ret | stat_expr) + Optional(NEWLINE)).setParseAction(lambda t: ["stat", t[0]])

# Program
program = ZeroOrMore(Group(stat)).setParseAction(lambda t: ["program", t])
program.ignore(COMMENT)
 
def parse(source):
  return program.parseString(source, parseAll=True)
