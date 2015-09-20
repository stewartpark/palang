from pyparsing import *

ParserElement.enablePackrat()

# Grammatical components
LPAREN, RPAREN, LBRACK, RBRACK, LBRACE, RBRACE, COLON =\
map(Suppress,"()[]{}:")
COMMA, DOT, OP_ASSIGN = map(Suppress, ",.=")
NEWLINE = Suppress(";")

# Literals
#FIXME Ident shouldn't be matched if it's a reserved keyword
IDENT = Word(alphas)\
        .setParseAction(lambda t: ["IDENT", t[0]])
INTEGER = Combine(Optional(oneOf("+ -")) + Word(nums))\
    .setName("integer")\
    .setParseAction(lambda t: ["INTEGER", int(t[0])])
REAL    = Combine(Optional(oneOf("+ -")) + Word(nums) + "." +
               Optional(Word(nums)) +
               Optional(oneOf("e E")+Optional(oneOf("+ -")) +Word(nums)))\
    .setName("real")\
    .setParseAction(lambda t: ["REAL", float(t[0])])
STRING  = QuotedString('"', multiline=True)\
        .setName("string")\
        .setParseAction(lambda t: ["STRING", t[0]])
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

def_var = Group(expr_lvalue)\
        .setParseAction(lambda t: ["def_var", t[0]])

def_stat_block = (Group(stat_one_line))|(LBRACE + ZeroOrMore(Group(stat)) + RBRACE)
def_func_arg = Group(Group(IDENT) + Optional(OP_ASSIGN + Group(expr))).setParseAction(lambda t: ['def_func_arg', t[0]])
def_func_args = LPAREN + Optional(delimitedList(Group(def_func_arg))) + RPAREN
def_func = Group(expr_lvalue + def_func_args)\
        .setParseAction(lambda t: ["def_func", t[0]])

expr_func_kwarg = Group(Group(IDENT) + OP_ASSIGN + Group(expr)).setParseAction(lambda t: ['expr_func_kwarg', t[0]])
expr_func_call = Group(Group(expr_lvalue) + LPAREN + Group(Optional(delimitedList(Group(expr_func_kwarg|expr)))) + RPAREN)\
        .setParseAction(lambda t: ["expr_func_call", t[0]])

expr_literal = Group(REAL | INTEGER | STRING | LIST | DICT | FUNC | VAR | expr_func_call | expr_lvalue)


LIST << Group(LBRACK + Optional(delimitedList(Group(expr))) + RBRACK)\
        .setParseAction(lambda t: ["LIST", t[0]])

DICT << Group(LBRACE + Optional(delimitedList(expr_literal + COLON + expr)) + RBRACE)\
        .setParseAction(lambda t: ["DICT", t[0]])

FUNC << Group(Suppress("func") + Group(def_func_args) + Group(def_stat_block)).setParseAction(lambda t: ["FUNC", t[0]])

VAR << Group(Suppress("var") + def_stat_block).setParseAction(lambda t: ["VAR", t[0]])

# Expression
expr << Group(operatorPrecedence(expr_literal, [
        (oneOf("* / mod"), 2, opAssoc.LEFT),
        (oneOf("+ -"), 2, opAssoc.LEFT),
        (oneOf("== != > >= < <= -> <-"), 2, opAssoc.LEFT),
        (oneOf("not"), 1, opAssoc.RIGHT),
        (oneOf("and"), 2, opAssoc.LEFT),
        (oneOf("or"), 2, opAssoc.LEFT),
        (oneOf("& ? !"), 1, opAssoc.LEFT)
])).setParseAction(lambda t: ["expr", t[0]])

# Statements
expr_stat_block = ((COMMA + Group(stat))|(LBRACE + ZeroOrMore(Group(stat)) + RBRACE))
stat_if = Group(Suppress("if") + Group(Group(expr) + Group(expr_stat_block)) + ZeroOrMore(Group(Suppress("elif") + Group(expr) + Group(expr_stat_block))) + Optional(Group(Suppress("else") + Group(expr_stat_block)))).setParseAction(lambda t: ["stat_if", t[0]])
stat_for = Group(Suppress("for") + Group(IDENT) + Suppress("in") + Group(expr) + Group(expr_stat_block)).setParseAction(lambda t: ["stat_for", t[0]])
stat_assign = Group(Group(def_func|def_var) + Group(def_stat_block)).setParseAction(lambda t: ["stat_assign", t[0]])
stat_ret << Group(OP_ASSIGN + expr).setParseAction(lambda t: ["stat_ret", t[0]])
stat_expr = Group(expr).setParseAction(lambda t: ["stat_expr", t[0]])
stat_break = Group(Suppress("break")).setParseAction(lambda t: ["stat_break"])
stat_continue = Group(Suppress("continue")).setParseAction(lambda t: ["stat_continue"])
stat << Group((stat_if | stat_for | stat_break | stat_continue | stat_assign | stat_ret | stat_expr) + Optional(NEWLINE)).setParseAction(lambda t: ["stat", t[0]])

# Program
program = ZeroOrMore(Group(stat)).setParseAction(lambda t: ["program", t])
 
def parse(source):
  return program.parseString(source, parseAll=True)
