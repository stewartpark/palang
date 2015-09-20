import parser
import compiler
import pprint
import sys

def go(source):
    pp = pprint.PrettyPrinter(indent=2, width=1)
    ast = parser.parse(source)
    print "/*"
    pp.pprint(eval(str(ast)))
    print "*/"
    c = compiler.compile(ast)
    print c

if len(sys.argv) == 1:
    while True:
        source = ""
        while True:
            line = raw_input()
            if len(line):
                source += line + '\n'
            else:
                break
        go(source)
else:
    source = open(sys.argv[1]).read()
    go(source)

