Pa Language
===========

<img src="https://raw.githubusercontent.com/stewartpark/palang/master/misc/logo.png" height="40" alt="" align="middle"/> Pa Language is a toy compiled language written in Python, C++11.

Currently, the only working implentation of Pa is Pypac, which is in the current git repository. The official Pa compiler will be reimplemented in Pa once the specification of the language is finished and polished up.

![Screencast](https://raw.githubusercontent.com/stewartpark/palang/master/misc/demo.gif)

### Work done so far

 - Initial implementation that is written in Python to bootstrap the language.
 - A few intrinsic funtions(print, input, len, range)
 - Binary level interface to import/export
 - Several libraries to make the language a bit more useful at this stage
    - tcp: TCP socket library
    - file: File I/O
 - import/export statements
 - Basic control flow statements: if, for, while, return(=)
 - Basic variable/function definition
 - Inline function definition(lambda)
 - Inline variable definition(lambda that gets executed right away)
 - Class/Instance (constructor, destructor, methods, properties, operator overloading)
 - -> operators(list -> func)

### Future work

 - Unimplemented operators (to different types)
 - Network/file I/O library that is based on libuv
 - the &, !, ? operators
 - Garbage collector

### Installation

Just type the below:

```
$ git clone https://github.com/stewartpark/palang
$ cd palang
$ pip install -r requirements.txt
$ ./build_libs.sh
```

### Examples

 - PAW (example web framework)
    - [app.pa](https://github.com/stewartpark/palang/blob/master/examples/paw/app.pa)
    - [paw.pa](https://github.com/stewartpark/palang/blob/master/examples/paw/paw.pa)
 - libsample (example library)
    - [libsample.pa](https://github.com/stewartpark/palang/blob/master/examples/libsample.pa)
    - [import_test.pa](https://github.com/stewartpark/palang/blob/master/examples/import_test.pa)
 - [tcp_http_test.pa](https://github.com/stewartpark/palang/blob/master/examples/tcp_http_test.pa)
 - [read_file.pa](https://github.com/stewartpark/palang/blob/master/examples/read_file.pa)
 - [string_test.pa](https://github.com/stewartpark/palang/blob/master/examples/string_test.pa)
 - [class_test.pa](https://github.com/stewartpark/palang/blob/master/examples/class_test.pa)
 - [map_test.pa](https://github.com/stewartpark/palang/blob/master/examples/map_test.pa)
 - [test.pa](https://github.com/stewartpark/palang/blob/master/examples/test.pa)
