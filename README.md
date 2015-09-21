Pa Language
===========

Pa Language is a toy compiled language written in Python, C++11.

```
$ git clone https://github.com/stewartpark/palang
$ cd palang
$ pip install -r requirements.txt
$ cat examples/test.pa
# Sample code
s = 0
for x in range(1,10000), s = s + x

if s > 100, print("Bigger than 100\n")

if s < 1000 { 
    print("Smaller than 1000\n")
} else {
    print("Bigger than 1000\n")
}

print(s, "\n");

# Map function
two = range(1,9) -> func(x) = 2*x

for x in two {
    print(x, " ")
}
print("\n")
$ python pypac -o test examples/test.pa 
$ ./test
Bigger than 100
Bigger than 1000
50005000
2 4 6 8 10 12 14 16 18 
```
