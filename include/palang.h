#ifndef __PALANG_H
#define __PALANG_H

#if __cplusplus < 201103L
    #error Needs at least a C++11 compliant compiler
#endif

#include <stdint.h>
#include <stdbool.h>
#include <cstdlib>
#include <list>
#include <map>
#include <string>
#include <functional>
#include <dlfcn.h>

#define PV2STR(x) (static_cast<string*>((x)->value.ptr))
#define PV2LIST(x) (static_cast<list<pa_value*>*>((x)->value.ptr))
#define PV2MAP(x) (static_cast<map<string,pa_value*>*>((x)->value.ptr))
#define inline

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

struct pa_value;
class pa_object_data;
class pa_class_data;

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
        //list<pa_value*>* list;
        //map<string,pa_value*>* dict;
        function<pa_value*(pa_value*,pa_value*)>* func;
        pa_class_data* cls;
        pa_object_data* obj;
    } value;
    enum pa_type type;
};

class pa_class_data {
    private:
        map<string, pa_value*> members;
        map<string, pa_value*> operators;
    public:
        void set_member(string name, pa_value* value) { this->members[name] = value; }
        pa_value* get_member(string name) { return this->members[name]; }
        void set_operator(string name, pa_value* value) { this->operators[name] = value; }
        pa_value* get_operator(string name) { return this->operators[name]; }
};

class pa_object_data {
    private:
        pa_class_data* _class;
        map<string, pa_value*> members;
    public:
        pa_object_data() {}
        pa_object_data(pa_class_data* _class) { this->_class = _class; }
        pa_class_data* get_class() { return this->_class; }
        void set_member(string name, pa_value* value) { this->members[name] = value; }
        pa_value* get_member(string name) { 
            if(this->members[name]){
                return this->members[name]; 
            } else if(this->_class && this->_class->get_member(name)) {
                return this->_class->get_member(name);
            } else {
                return NULL;
            }
        }
};

list<pa_value*> pool;

// Types

inline pa_value* TYPE_NIL() {
    static pa_value *r = NULL;
    if(!r) { 
        r = new pa_value;
        r->type = pa_nil;
        pool.push_back(r);
    }
    return r;
}

// Convert any value into a logical value
inline bool LEXPR(pa_value* a) {
    switch(a->type) {
        case pa_integer:
                return a->value.b;
        case pa_bool:
                return a->value.b;
        default:
            goto type_mismatch; 
    }
type_mismatch:
    printf("Runtime Error: Type mismatch(logical).\n");
    exit(1);
}


inline pa_value* TYPE_BOOL(bool v) {
    pa_value *r = new pa_value;
    r->value.b = v;
    r->type = pa_bool;
    pool.push_back(r);
    return r;
}

inline pa_value* TYPE_INT(int64_t v) {
    pa_value *r = new pa_value;
    r->value.i64 = v;
    r->type = pa_integer;
    pool.push_back(r);
    return r;
}

#define TYPE_LIST(...) _TYPE_LIST(list<pa_value*>{ __VA_ARGS__ })
inline pa_value* _TYPE_LIST(list<pa_value*> li) {
    pa_value *r = new pa_value;
    list<pa_value*>* l = new list<pa_value*>;
    *l = li;
    r->value.ptr = (void*)l;
    r->type = pa_list;
    pool.push_back(r);
    return r;
}

inline string HASH(pa_value* o) {
    switch(o->type){
        case pa_string:
            return *PV2STR(o);
            break;
        default:
            printf("Runtime Error: Non-hashable.\n");
            exit(1);
    }
}

#define TYPE_DICT_KV(k, v) {HASH(k), v}
#define TYPE_DICT(...) _TYPE_DICT(map<string,pa_value*>{ __VA_ARGS__ })
inline pa_value* _TYPE_DICT(map<string,pa_value*> dict) {
    pa_value *r = new pa_value;
    map<string,pa_value*>* d = new map<string,pa_value*>;
    *d = dict;
    r->value.ptr = (void*)d;
    r->type = pa_dict;
    pool.push_back(r);
    return r;
}

inline pa_value* TYPE_STRING(string str) {
    pa_value *r = new pa_value;
    string* s = new string;
    *s = str;
    r->value.ptr = (void*)s;
    r->type = pa_string;
    pool.push_back(r);
    return r;
}

inline pa_value* TYPE_FUNC(function<pa_value*(pa_value*,pa_value*)> f) {
    pa_value *r = new pa_value;
    function<pa_value*(pa_value*,pa_value*)>* ff = new function<pa_value*(pa_value*,pa_value*)>;
    *ff = f;
    r->value.func = ff;
    r->type = pa_func;
    pool.push_back(r);
    return r;

}

inline pa_value* TYPE_CLASS() {
    pa_value *r = new pa_value;
    r->value.cls = new pa_class_data;
    r->type = pa_class;
    pool.push_back(r);
    return r;
}

inline pa_value* TYPE_OBJECT() {
    pa_value *r = new pa_value;
    r->value.obj = new pa_object_data;
    r->type = pa_object;
    pool.push_back(r);
    return r;
}
inline pa_value* TYPE_OBJECT(pa_class_data* _class) {
    pa_value *r = new pa_value;
    r->value.obj = new pa_object_data(_class);
    r->type = pa_object;
    pool.push_back(r);
    return r;
}

// Function invoke

inline pa_value* FUNC_CALL(pa_value* func, pa_value* args, pa_value* kwargs) {
    
    if(func->type != pa_func) {
        printf("func_type: %d\n", func->type);
        printf("Runtime Error: calling a non-function value.\n");
        exit(1);
    } 

    return (*(func->value.func))(args, kwargs);
}

pa_value* PARAM(pa_value *args, pa_value *kwargs, const size_t nth, const string name, pa_value *def) {
    list<pa_value*> &_args = *PV2LIST(args);
    map<string,pa_value*> &_kwargs = *PV2MAP(kwargs);
    
    if(_kwargs.count(name)) {
        return _kwargs[name];
    } else if(_args.size()-1 >= nth) {
        list<pa_value*>::iterator it = _args.begin();
        advance(it, nth);
        return *it;
    } else {
        if(def->type == pa_nil) {
            printf("Runtime Error: %s is required.\n", name.c_str());
            exit(1);
        } else {
            return def;
        }
    }
}

// Operators

inline pa_value* OP_GETITEM(pa_value* a, pa_value* b) {
    list<pa_value*>* l;
    list<pa_value*>::iterator it;
    map<string,pa_value*>* m;
    string* s;

    switch(a->type) {
        case pa_string:
            switch(b->type) {
                case pa_integer:
                    s = PV2STR(a);      
                    if(s->length() <= b->value.i64) {
                        printf("Runtime Error: String index out of range.\n");
                        exit(1);
                    }
                    return TYPE_STRING(string { s->at(b->value.i64) });
                default:
                    goto type_mismatch;
            }
        case pa_list:
            l = PV2LIST(a);
            switch(b->type) {
                case pa_integer:
                    if(l->size() <= b->value.i64) {
                        printf("Runtime Error: List index out of range.\n");
                        exit(1);
                    }

                    it = l->begin();
                    advance(it, b->value.i64);
                    return *it;
                default:
                   goto type_mismatch;
            }
        case pa_dict:
            m = PV2MAP(a);
            return (*m)[HASH(b)];
        default:
            goto type_mismatch;
    }
type_mismatch:
    printf("Runtime Error: Type mismatch([]).\n");
    exit(1);
}

inline pa_value* OP_GETATTR(pa_value* a, string b) {
    pa_value* ret;
    switch(a->type) {
        case pa_object:
            ret = a->value.obj->get_member(b);
            if(!ret) {
                ret = a->value.obj->get_class()->get_operator("getattr");
                if(ret) {
                    ret = FUNC_CALL(ret, TYPE_LIST(a, TYPE_STRING(b)), TYPE_DICT());
                } else {
                    printf("Runtime Error: no such attribute/method.\n");
                    exit(1); 
                }
            }
            return ret;
        default:
            goto type_mismatch;
    }
type_mismatch:
    printf("Runtime Error: Type mismatch(.).\n");
    exit(1);
}

inline pa_value* OP_ADD(pa_value* a, pa_value* b) {
    pa_value* n;
    list<pa_value*> *l1, *l2;
    list<pa_value*>::iterator it;
    switch(a->type) {
        case pa_integer:
            switch(b->type) {
                case pa_integer:
                    return TYPE_INT(a->value.i64 + b->value.i64);
                default:
                    goto type_mismatch;
            }
        case pa_string:
            switch(b->type) {
                case pa_string:
                    return TYPE_STRING(*PV2STR(a) + *PV2STR(b));
                default:
                   goto type_mismatch;
            }
        case pa_list:
            switch(b->type) {
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

inline pa_value* OP_SUB(pa_value *a, pa_value *b) {
    switch(a->type) {
        case pa_integer:
            switch(b->type) {
                case pa_integer:
                    return TYPE_INT(a->value.i64 - b->value.i64);
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

inline pa_value* OP_MUL(pa_value* a, pa_value* b) {
    switch(a->type) {
        case pa_integer:
            switch(b->type) {
                case pa_integer:
                    return TYPE_INT(a->value.i64 * b->value.i64);
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

inline pa_value* OP_DIV(pa_value* a, pa_value* b) {
    switch(a->type) {
        case pa_integer:
            switch(b->type) {
                case pa_integer:
                    return TYPE_INT(a->value.i64 / b->value.i64);
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

inline pa_value* OP_MOD(pa_value* a, pa_value* b) {
    switch(a->type) {
        case pa_integer:
            switch(b->type) {
                case pa_integer:
                    return TYPE_INT(a->value.i64 % b->value.i64);
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


inline pa_value* OP_EQ(pa_value* a, pa_value* b) {
    switch(a->type) {
        case pa_integer:
            switch(b->type) {
                case pa_integer:
                    return TYPE_BOOL(a->value.i64 == b->value.i64);
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

inline pa_value* OP_NEQ(pa_value* a, pa_value* b) {
    switch(a->type) {
        case pa_integer:
            switch(b->type) {
                case pa_integer:
                    return TYPE_BOOL(a->value.i64 != b->value.i64);
                default:
                    goto type_mismatch;
            }
        default:
            goto type_mismatch; 
    }
type_mismatch:
    printf("Runtime Error: Type mismatch(!=).\n");
    exit(1);
}

inline pa_value* OP_GT(pa_value* a, pa_value* b) {
    switch(a->type) {
        case pa_integer:
            switch(b->type) {
                case pa_integer:
                    return TYPE_BOOL(a->value.i64 > b->value.i64);
                default:
                    goto type_mismatch;
            }
        default:
            goto type_mismatch; 
    }
type_mismatch:
    printf("Runtime Error: Type mismatch(>).\n");
    exit(1);
}

inline pa_value* OP_GTE(pa_value* a, pa_value* b) {
    switch(a->type) {
        case pa_integer:
            switch(b->type) {
                case pa_integer:
                    return TYPE_BOOL(a->value.i64 >= b->value.i64);
                default:
                    goto type_mismatch;
            }
        default:
            goto type_mismatch; 
    }
type_mismatch:
    printf("Runtime Error: Type mismatch(>=).\n");
    exit(1);
}

inline pa_value* OP_LT(pa_value* a, pa_value* b) {
    switch(a->type) {
        case pa_integer:
            switch(b->type) {
                case pa_integer:
                    return TYPE_BOOL(a->value.i64 < b->value.i64);
                default:
                    goto type_mismatch;
            }
        default:
            goto type_mismatch; 
    }
type_mismatch:
    printf("Runtime Error: Type mismatch(<).\n");
    exit(1);
}

inline pa_value* OP_LTE(pa_value* a, pa_value* b) {
    switch(a->type) {
        case pa_integer:
            switch(b->type) {
                case pa_integer:
                    return TYPE_BOOL(a->value.i64 <= b->value.i64);
                default:
                    goto type_mismatch;
            }
        default:
            goto type_mismatch; 
    }
type_mismatch:
    printf("Runtime Error: Type mismatch(<=).\n");
    exit(1);
}

inline pa_value* OP_RIGHT(pa_value* a, pa_value* b) {
    // Flow operator (right).
    pa_value* n;
    list<pa_value*> *l1, *l2;
    list<pa_value*>::iterator it;
    switch(a->type) {
        case pa_list:
            switch(b->type) {
                case pa_func:
                    // map(list->list) with a func
                    n = TYPE_LIST();
                    l1 = PV2LIST(a);
                    l2 = PV2LIST(n);
                    for(it = l1->begin(); it != l1->end(); ++it){
                        l2->push_back(FUNC_CALL(b, TYPE_LIST(*it), TYPE_DICT()));
                    }
                    return n;
                default:
                    goto type_mismatch;
            }
        default:
            goto type_mismatch; 
    }
type_mismatch:
    printf("Runtime Error: Type mismatch(->).\n");
    exit(1);
}


inline pa_value* OP_OR(pa_value* a, pa_value* b) {
    switch(a->type) {
        case pa_bool:
            switch(b->type) {
                case pa_bool:
                    return TYPE_BOOL(a->value.b || b->value.b);
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

inline pa_value* OP_AND(pa_value* a, pa_value* b) {
    switch(a->type) {
        case pa_bool:
            switch(b->type) {
                case pa_bool:
                    return TYPE_BOOL(a->value.b && b->value.b);
                default:
                    goto type_mismatch;
            }
        default:
            goto type_mismatch; 
    }
type_mismatch:
    printf("Runtime Error: Type mismatch(and).\n");
    exit(1);
}

inline pa_value* OP_LEN(pa_value* a) {
    list<pa_value*>* l;
    string* s;
    switch(a->type) {
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

inline pa_value* PA_IMPORT(string name) {

    //TODO 
    string file_name = "./" + name + ".so";

    void* handle = dlopen(file_name.c_str(), RTLD_NOW | RTLD_GLOBAL);

    if(handle) {
        pa_value*(*mod_init)() = (pa_value*(*)()) dlsym(handle, "PA_INIT");

        pa_value* mod = mod_init();

        pa_value* mod_class = TYPE_CLASS();
        mod_class->value.cls->set_operator("getattr", TYPE_FUNC([=](pa_value* args, pa_value* kwargs) -> pa_value* {
            pa_value *_this = PARAM(args, kwargs, 0, "", TYPE_NIL());
            pa_value *attr_name = PARAM(args, kwargs, 1, "", TYPE_NIL());
            pa_value* attr = OP_GETITEM(mod, attr_name); 
            if(attr){ 
                return attr; 
            } else {
                printf("Runtime Error: no such name in the module: %s.%s\n", name.c_str(), PV2STR(attr_name)->c_str());
                exit(1);
            }
        }));

        return TYPE_OBJECT(mod_class->value.cls);
    } else {
        printf("Runtime Error: no such library. %s\n", name.c_str());
        printf("%s\n", dlerror());
        exit(1);
    }
}

inline void PA_ENTER(int argc, char** argv, char** env) {
    //TODO 
}

inline int PA_LEAVE(pa_value *ret) {
    //TODO Return value
    return 0;
}

// Intrinsics
#define INTRINSICS() \
pa_value *print; \
pa_value *range; \
pa_value *input; \
range = TYPE_FUNC([](pa_value* args, pa_value* kwargs) -> pa_value* { \
        pa_value *start = PARAM(args, kwargs, 0, "start", TYPE_NIL()); \
        pa_value *end = PARAM(args, kwargs, 1, "end", TYPE_NIL()); \
        pa_value *step = PARAM(args, kwargs, 2, "step", TYPE_INT(1)); \
        \
        pa_value *l = TYPE_LIST(); \
        if(start->type == pa_integer && end->type == pa_integer && step->type == pa_integer) {  \
            for(int64_t i = start->value.i64; i <= end->value.i64; i+=step->value.i64) { \
                pa_value *index = TYPE_INT(i); \
                PV2LIST(l)->push_back(index); \
            } \
            return l; \
        } else { \
            printf("Runtime Error: Type mismatch(range).\n"); \
            exit(1); \
        } \
    }); \
    print = TYPE_FUNC([](pa_value* args, pa_value* kwargs) -> pa_value* { \
        list<pa_value*> *_args = PV2LIST(args); \
        list<pa_value*>::iterator it; \
        for(it = _args->begin(); it != _args->end(); ++it) { \
            pa_value* msg = *it; \
            switch(msg->type) { \
                case pa_nil: \
                    printf("nil"); \
                    break; \
                case pa_integer: \
                    printf("%lld", (long long int)msg->value.i64); \
                    break; \
                case pa_float: \
                    printf("%lf", (double)msg->value.f64); \
                    break; \
                case pa_string: \
                    printf("%s", PV2STR(msg)->c_str()); \
                    break; \
                default: \
                    printf("Runtime Error: print() cannot print the value. (Type:%d)\n", msg->type); \
                    exit(1); \
                    break; \
            } \
        } \
        return TYPE_NIL(); \
    }); \
    input = TYPE_FUNC([](pa_value* args, pa_value* kwargs) -> pa_value* { \
        long long int N; \
        register int t = scanf("%lld", &N); \
        pa_value* n = TYPE_INT(N); \
        return n; \
    });


#endif
