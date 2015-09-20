#ifndef __PALANG_H
#define __PALANG_H

#if __cplusplus < 201103L
    #error Needs at least a C++11 compliant compiler
#endif

#include <stdint.h>
#include <stdbool.h>
#include <list>
#include <map>
#include <string>
#include <functional>

#define PV2STR(x) (static_cast<string*>(x.value.ptr))
#define PV2LIST(x) (static_cast<list<pa_value>*>(x.value.ptr))
#define PV2MAP(x) (static_cast<map<string,pa_value>*>(x.value.ptr))

using namespace std;

enum pa_type {
    pa_nil,
    pa_bool,
    pa_integer,
    pa_float,
    pa_string, 
    pa_list,
    pa_dict,
    pa_func,
    pa_class,
    pa_object
}; 

struct pa_value {
    union {
        int8_t i8;
        int16_t i16;
        int32_t i32;
        int64_t i64;
        uint8_t u8;
        uint16_t u16;
        uint32_t u32;
        uint64_t u64;
        bool b;
        float f32;
        double f64;
        void* ptr; 
        function<pa_value(pa_value,pa_value)>* func;
    } value;
    enum pa_type type;
};

list<pa_value*> pool;
pa_value nil; // Just to represent nil

// Types

inline pa_value& TYPE_NIL() {
    return nil;
}

inline bool CBOOL(pa_value a) {
    switch(a.type) {
        case pa_integer:
                return a.value.b;
        case pa_bool:
                return a.value.b;
        default:
            goto type_mismatch; 
    }
type_mismatch:
    printf("Runtime Error: Type mismatch(logical).\n");
    exit(1);
}


inline pa_value& TYPE_BOOL(bool v) {
    pa_value *r = new pa_value;
    r->value.b = v;
    r->type = pa_bool;
    pool.push_back(r);
    return *r;
}

inline pa_value& TYPE_INT(int64_t v) {
    pa_value *r = new pa_value;
    r->value.i64 = v;
    r->type = pa_integer;
    pool.push_back(r);
    return *r;
}

#define TYPE_LIST(...) _TYPE_LIST(list<pa_value>{ __VA_ARGS__ })
inline pa_value& _TYPE_LIST(list<pa_value> li) {
    pa_value *r = new pa_value;
    list<pa_value>* l = new list<pa_value>;
    *l = li;
    r->value.ptr = (void*)l;
    r->type = pa_list;
    pool.push_back(r);
    return *r;
}

inline string HASH(pa_value o) {
    switch(o.type){
        case pa_string:
            return *PV2STR(o);
            break;
        default:
            printf("Runtime Error: Non-hashable.\n");
            exit(1);
    }
}

#define TYPE_DICT_KV(k, v) {HASH(k), v}
#define TYPE_DICT(...) _TYPE_DICT(map<string,pa_value>{ __VA_ARGS__ })
inline pa_value& _TYPE_DICT(map<string,pa_value> dict) {
    pa_value *r = new pa_value;
    map<string,pa_value>* d = new map<string,pa_value>;
    *d = dict;
    r->value.ptr = (void*)d;
    r->type = pa_dict;
    pool.push_back(r);
    return *r;
}

inline pa_value& TYPE_STRING(string str) {
    pa_value *r = new pa_value;
    string* s = new string;
    *s = str;
    r->value.ptr = (void*)s;
    r->type = pa_string;
    pool.push_back(r);
    return *r;
}

inline pa_value& TYPE_FUNC(function<pa_value(pa_value,pa_value)> f) {
    pa_value *r = new pa_value;
    function<pa_value(pa_value,pa_value)>* ff = new function<pa_value(pa_value,pa_value)>;
    *ff = f;
    r->value.func = ff;
    r->type = pa_func;
    pool.push_back(r);
    return *r;

}

// Function invoke

inline pa_value FUNC_CALL(pa_value func, pa_value args, pa_value kwargs) {

    if(func.type != pa_func) {
        printf("Runtime Error: calling a non-function value.\n");
        exit(1);
    } 

    return (*(func.value.func))(args, kwargs);
}

pa_value PARAM(pa_value &args, pa_value &kwargs, const size_t nth, const string name, pa_value &def) {
    list<pa_value> &_args = *PV2LIST(args);
    map<string,pa_value> &_kwargs = *PV2MAP(kwargs);
    
    if(_kwargs.count(name)) {
        return _kwargs[name];
    } else if(_args.size()-1 >= nth) {
        list<pa_value>::iterator it = _args.begin();
        advance(it, nth);
        return *it;
    } else {
        if(&def == &nil) {
            printf("Runtime Error: %s is required.\n", name.c_str());
            exit(1);
        } else {
            return def;
        }
    }
}

// Operators

inline pa_value OP_ITEM(pa_value a, pa_value b) {
    list<pa_value>* l;
    list<pa_value>::iterator it;
    string* s;

    switch(a.type) {
        case pa_string:
            switch(b.type) {
                case pa_integer:
                    s = PV2STR(a);      
                    if(s->length() <= b.value.i64) {
                        printf("Runtime Error: String index out of range.\n");
                        exit(1);
                    }
                    return TYPE_STRING(string { s->at(b.value.i64) });
                default:
                    goto type_mismatch;
            }
        case pa_list:
            l = PV2LIST(a);
            switch(b.type) {
                case pa_integer:
                    if(l->size() <= b.value.i64) {
                        printf("Runtime Error: List index out of range.\n");
                        exit(1);
                    }

                    it = l->begin();
                    advance(it, b.value.i64);
                    return *it;
                default:
                   goto type_mismatch;
            }
        default:
            goto type_mismatch;
    }
type_mismatch:
    printf("Runtime Error: Type mismatch([]).\n");
    exit(1);
}

inline pa_value OP_ADD(pa_value a, pa_value b) {
    pa_value n;
    list<pa_value> *l1, *l2;
    list<pa_value>::iterator it;
    switch(a.type) {
        case pa_integer:
            switch(b.type) {
                case pa_integer:
                    return TYPE_INT(a.value.i64 + b.value.i64);
                default:
                    goto type_mismatch;
            }
        case pa_string:
            switch(b.type) {
                case pa_string:
                    return TYPE_STRING(*PV2STR(a) + *PV2STR(b));
                default:
                   goto type_mismatch;
            }
        case pa_list:
            switch(b.type) {
                case pa_list:
                    n = TYPE_LIST();
                    l2 = PV2LIST(n);
                    l1 = PV2LIST(a);
                    for(it = l1->begin(); it != l1->end(); ++it) {
                        l2->push_back(*it);
                    }
                    l1 = PV2LIST(b);
                    for(it = l1->begin(); it != l1->end(); ++it) {
                        l2->push_back(*it);
                    }
                    return n;
                default:
                   goto type_mismatch;
            }
        default:
            goto type_mismatch; 
    }
type_mismatch:
    printf("Runtime Error: Type mismatch(+).\n");
    exit(1);
}

inline pa_value OP_SUB(pa_value a, pa_value b) {
    switch(a.type) {
        case pa_integer:
            switch(b.type) {
                case pa_integer:
                    return TYPE_INT(a.value.i64 - b.value.i64);
                default:
                    goto type_mismatch;
            }
        default:
            goto type_mismatch; 
    }
type_mismatch:
    printf("Runtime Error: Type mismatch(-).\n");
    exit(1);
}

inline pa_value OP_MUL(pa_value a, pa_value b) {
    switch(a.type) {
        case pa_integer:
            switch(b.type) {
                case pa_integer:
                    return TYPE_INT(a.value.i64 * b.value.i64);
                default:
                    goto type_mismatch;
            }
        default:
            goto type_mismatch; 
    }
type_mismatch:
    printf("Runtime Error: Type mismatch(*).\n");
    exit(1);
}

inline pa_value OP_DIV(pa_value a, pa_value b) {
    switch(a.type) {
        case pa_integer:
            switch(b.type) {
                case pa_integer:
                    return TYPE_INT(a.value.i64 / b.value.i64);
                default:
                    goto type_mismatch;
            }
        default:
            goto type_mismatch; 
    }
type_mismatch:
    printf("Runtime Error: Type mismatch(/).\n");
    exit(1);
}

inline pa_value OP_MOD(pa_value a, pa_value b) {
    switch(a.type) {
        case pa_integer:
            switch(b.type) {
                case pa_integer:
                    return TYPE_INT(a.value.i64 % b.value.i64);
                default:
                    goto type_mismatch;
            }
        default:
            goto type_mismatch; 
    }
type_mismatch:
    printf("Runtime Error: Type mismatch(mod).\n");
    exit(1);
}


inline pa_value OP_EQ(pa_value a, pa_value b) {
    switch(a.type) {
        case pa_integer:
            switch(b.type) {
                case pa_integer:
                    return TYPE_BOOL(a.value.i64 == b.value.i64);
                default:
                    goto type_mismatch;
            }
        default:
            goto type_mismatch; 
    }
type_mismatch:
    printf("Runtime Error: Type mismatch(==).\n");
    exit(1);
}

inline pa_value OP_OR(pa_value a, pa_value b) {
    switch(a.type) {
        case pa_bool:
            switch(b.type) {
                case pa_bool:
                    return TYPE_BOOL(a.value.b || b.value.b);
                default:
                    goto type_mismatch;
            }
        default:
            goto type_mismatch; 
    }
type_mismatch:
    printf("Runtime Error: Type mismatch(or).\n");
    exit(1);
}

inline pa_value OP_AND(pa_value a, pa_value b) {
    switch(a.type) {
        case pa_bool:
            switch(b.type) {
                case pa_bool:
                    return TYPE_BOOL(a.value.b && b.value.b);
                default:
                    goto type_mismatch;
            }
        default:
            goto type_mismatch; 
    }
type_mismatch:
    printf("Runtime Error: Type mismatch(or).\n");
    exit(1);
}

inline pa_value OP_LEN(pa_value a) {
    list<pa_value>* l;
    string* s;
    switch(a.type) {
        case pa_list:
            l = PV2LIST(a);
            return TYPE_INT(l->size());
        case pa_string:
            s = PV2STR(a);
            return TYPE_INT(s->length());
        default:
            goto type_mismatch; 
    }

type_mismatch:
    printf("Runtime Error: Type mismatch(len).\n");
    exit(1);
}

// Utilities

pa_value print; 
pa_value range;

inline void PA_ENTER() {
    nil = TYPE_NIL();
    range = TYPE_FUNC([](pa_value args, pa_value kwargs) -> pa_value {
        pa_value start = PARAM(args, kwargs, 0, "start", nil);
        pa_value end = PARAM(args, kwargs, 1, "end", nil);
        pa_value step = PARAM(args, kwargs, 2, "step", TYPE_INT(1));
        
        pa_value l = TYPE_LIST();
        if(start.type == pa_integer && end.type == pa_integer && step.type == pa_integer) { 
            for(int64_t i = start.value.i64; i <= end.value.i64; i+=step.value.i64) {
                PV2LIST(l)->push_back(TYPE_INT(i));
            }
            return l;
        } else {
            printf("Runtime Error: Type mismatch(range).\n");
            exit(1);
        }
    });
    print = TYPE_FUNC([](pa_value args, pa_value kwargs) -> pa_value {
        pa_value msg = PARAM(args, kwargs, 0, "msg", nil);
        switch(msg.type) {
            case pa_nil:
                printf("nil");
                break;
            case pa_integer:
                printf("%lld", (long long int)msg.value.i64);
                break;
            case pa_float:
                printf("%lf", (double)msg.value.f64);
                break;
            case pa_string:
                printf("%s", PV2STR(msg)->c_str());
                break;
            default:
                printf("Runtime Error: print() cannot print the value. %d\n", msg.type);
                exit(1);
                break;
        }
        return nil;
    });
}

inline void PA_LEAVE() {

}


#endif
