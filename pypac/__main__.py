import sys, os, subprocess, pprint
from tempfile import NamedTemporaryFile
from optparse import OptionParser
import parser, compiler

CXX = os.environ.get("CXX", "c++")
CXXFLAGS = os.environ.get("CXXFLAGS", "-O3 -std=c++11")
PA_HOME = os.path.abspath(os.environ.get("PA_HOME", "."))

pp = pprint.PrettyPrinter(indent=2,width=80)

opt = OptionParser()
opt.add_option("-o", "--output", dest="output", default="a.out", help="output file", metavar="FILE")
opt.add_option("-v", "--verbose", dest="verbose", default=False, help="verbose mode", action="store_true")
opt.add_option("-c", "--cpp", dest="cpp", default=False, help="generate a C++ source code file instead of an executable.", action="store_true")
opt.add_option("-l", "--library", dest="library", default=False, help="build as a library.", action="store_true")

options, args = opt.parse_args()

if len(args) == 0:
    opt.print_help()
    exit(1)

source = "\n".join(map(lambda x: open(x).read(), args))

ast = parser.parse(source)

cxx = compiler.compile(ast, is_library=options.library)

if options.cpp:
    open(options.output, 'w').write(cxx)
else:
    f = NamedTemporaryFile(suffix='.cc', delete=False)
    f.write(cxx)
    f.close()
    CXXFLAGS += " -o " + options.output + " "
    CXXFLAGS += " -I " + PA_HOME + "/include/ "
    if options.library:
        CXXFLAGS += " -c -fPIC -shared -Wl,-soname," + options.output + " "
    cmdline = (CXX + " "  + CXXFLAGS + " " + f.name).split()
    if options.verbose: print " ".join(cmdline)
    p = subprocess.Popen(cmdline, stderr=subprocess.PIPE)
    ret = p.wait()
    err = p.stderr.read()
    os.unlink(f.name)
    if ret: print 'Internal Error!'
    if options.verbose and err: print err
