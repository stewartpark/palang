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
#include <algorithm>
#include <stdio.h>
#include <dlfcn.h>
#include <unistd.h>
#include <gc/gc.h>
#include <gc/gc_cpp.h>
#include <gc/gc_allocator.h>

#define pa_string_t basic_string<char,char_traits<char>,gc_allocator<char>>
#define pa_list_t list<pa_value_t*>
#define pa_dict_t map<pa_string_t,pa_value_t*>
#define pa_func_t function<pa_value_t*(pa_list_t,pa_dict_t,pa_value_t*)>

#define PV2STR(x) (static_cast<pa_string_t*>((x)->value.ptr))
#define PV2LIST(x) (static_cast<pa_list_t*>((x)->value.ptr))
#define PV2MAP(x) (static_cast<pa_dict_t*>((x)->value.ptr))

using namespace std;

enum pa_type_t {
    pa_nil,
    pa_boolean,
    pa_integer,
    pa_float,
    pa_string, 
    pa_list,
    pa_dictionary,
    pa_function,
    pa_class,
    pa_object
}; 

class pa_value_t;
class pa_object_data;
class pa_class_data;

class pa_value_t : public gc {
    public:
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
            pa_func_t* func;
            pa_class_data* cls;
            pa_object_data* obj;
        } value;
        enum pa_type_t type;
};

class pa_class_data : public gc {
    private:
        pa_dict_t members;
        pa_dict_t operators;
    public:
        void set_member(pa_string_t name, pa_value_t* value) { this->members[name] = value; }
        pa_value_t* get_member(pa_string_t name) { return this->members[name]; }
        void set_operator(pa_string_t name, pa_value_t* value) { this->operators[name] = value; }
        pa_value_t* get_operator(pa_string_t name) { return this->operators[name]; }
};

class pa_object_data : public gc {
    private:
        pa_class_data* _class;
        pa_dict_t members;
    public:
        pa_object_data() {}
        pa_object_data(pa_class_data* _class) { this->_class = _class; }
        pa_class_data* get_class() { return this->_class; }
        pa_value_t* get_operator(pa_string_t name) { 
            if(this->_class) {
                return this->_class->get_operator(name);
            } else {
                return NULL;
            }
        }
        void set_member(pa_string_t name, pa_value_t* value) { this->members[name] = value; }
        pa_value_t* get_member(pa_string_t name) { 
            if(this->members[name]){
                return this->members[name]; 
            } else if(this->_class && this->_class->get_member(name)) {
                return this->_class->get_member(name);
            } else {
                return NULL;
            }
        }
};

// Types

inline pa_value_t* pa_new_nil() {
    static pa_value_t *r = NULL;
    if(!r) { 
        r = new pa_value_t;
        r->type = pa_nil;
    }
    return r;
}

// Convert any value into a logical value
inline bool pa_evaluate_into_boolean(pa_value_t* a) {
    switch(a->type) {
        case pa_integer:
                return a->value.b;
        case pa_boolean:
                return a->value.b;
        default:
            goto type_mismatch; 
    }
type_mismatch:
    printf("Runtime Error: Type mismatch(logical).\n");
    exit(1);
}


inline pa_value_t* pa_new_boolean(bool v) {
    pa_value_t *r = new pa_value_t;
    r->value.b = v;
    r->type = pa_boolean;
    return r;
}

inline pa_value_t* pa_new_integer(int64_t v) {
    pa_value_t *r = new pa_value_t;
    r->value.i64 = v;
    r->type = pa_integer;
    return r;
}

#define pa_new_list(...) _pa_new_list(pa_list_t{ __VA_ARGS__ })
inline pa_value_t* _pa_new_list(pa_list_t li) {
    pa_value_t *r = new pa_value_t;
    pa_list_t* l = new pa_list_t;
    *l = li;
    r->value.ptr = (void*)l;
    r->type = pa_list;
    return r;
}

inline pa_string_t pa_operator_hash(pa_value_t* o) {
    switch(o->type){
        case pa_string:
            return *PV2STR(o);
            break;
        default:
            printf("Runtime Error: Non-hashable.\n");
            exit(1);
    }
}

#define pa_new_dictionary_kv(k, v) {pa_operator_hash(k), v}
#define pa_new_dictionary(...) _pa_new_dictionary(pa_dict_t{ __VA_ARGS__ })
inline pa_value_t* _pa_new_dictionary(pa_dict_t dict) {
    pa_value_t *r = new pa_value_t;
    pa_dict_t* d = new pa_dict_t;
    *d = dict;
    r->value.ptr = (void*)d;
    r->type = pa_dictionary;
    return r;
}

inline pa_value_t* pa_new_string(pa_string_t str) {
    pa_value_t *r = new pa_value_t;
    r->value.ptr = (void*)new pa_string_t(str);
    r->type = pa_string;
    return r;
}

inline pa_value_t* pa_new_function(pa_func_t f) {
    pa_value_t *r = new pa_value_t;
    r->value.func = new pa_func_t(f);
    r->type = pa_function;
    return r;

}

inline pa_value_t* pa_new_class() {
    pa_value_t *r = new pa_value_t;
    r->value.cls = new pa_class_data;
    r->type = pa_class;
    return r;
}

inline pa_value_t* pa_new_object(pa_class_data* _class) {
    pa_value_t *r = new pa_value_t;
    r->value.obj = new pa_object_data(_class);
    r->type = pa_object;
    return r;
}

// Function invoke

inline pa_value_t* pa_function_call(pa_value_t* func, pa_list_t args, pa_dict_t kwargs, pa_value_t* _this) {
    
    if(func->type == pa_function) {
        return (*(func->value.func))(args, kwargs, _this);
    } else if(func->type == pa_class) {
        pa_value_t* new_obj = pa_new_object(func->value.cls);
        pa_value_t* ret = func->value.cls->get_operator("constructor");
        if(ret) {
            pa_function_call(ret, args, kwargs, new_obj); 
        }
        return new_obj;
    } else {
        printf("func_type: %d\n", func->type);
        printf("Runtime Error: calling a non-callable value.\n");
        exit(1);
    } 

}

pa_value_t* pa_get_argument(pa_list_t& args, pa_dict_t& kwargs, const size_t nth, const pa_string_t name, pa_value_t *def) {
    if(kwargs.count(name)) {
        return kwargs[name];
    } else if(args.size() >= nth+1) {
        pa_list_t::iterator it = args.begin();
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
inline pa_value_t* pa_operator_setitem(pa_value_t* a, pa_value_t* b, pa_value_t* c) {
    pa_list_t* l;
    pa_list_t::iterator it;
    pa_dict_t* m;
    pa_value_t* n;
    pa_string_t* s;

    switch(a->type) {
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
                    return *it = c;
                default:
                   goto type_mismatch;
            }
        case pa_dictionary:
            m = PV2MAP(a);
            return (*m)[pa_operator_hash(b)] = c;
        case pa_object:
            n = a->value.obj->get_operator("setitem");
            if(n) {
                return pa_function_call(n, pa_list_t{b, c}, pa_dict_t{}, a);
            } else {
                goto type_mismatch;
            }
        default:
            goto type_mismatch;
    }
type_mismatch:
    printf("Runtime Error: Type mismatch(setitem).\n");
    exit(1);
}

inline pa_value_t* pa_operator_getitem(pa_value_t* a, pa_value_t* b) {
    pa_list_t* l;
    pa_list_t::iterator it;
    pa_dict_t* m;
    pa_string_t* s;
    pa_value_t* n;

    switch(a->type) {
        case pa_string:
            switch(b->type) {
                case pa_integer:
                    s = PV2STR(a);      
                    if(s->length() <= b->value.i64) {
                        printf("Runtime Error: String index out of range.\n");
                        exit(1);
                    }
                    return pa_new_string(pa_string_t { s->at(b->value.i64) });
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
        case pa_dictionary:
            m = PV2MAP(a);
            return (*m)[pa_operator_hash(b)];
        case pa_object:
            n = a->value.obj->get_operator("getitem");
            if(n) {
                return pa_function_call(n, pa_list_t{b}, pa_dict_t{}, a);
            } else {
                goto type_mismatch;
            }
        default:
            goto type_mismatch;
    }
type_mismatch:
    printf("Runtime Error: Type mismatch(getitem).\n");
    exit(1);
}

inline pa_value_t* pa_operator_setattr(pa_value_t* a, pa_string_t b, pa_value_t* c) {
    pa_value_t* ret;
    switch(a->type) {
        case pa_object:
            ret = a->value.obj->get_member(b);
            if(!ret) {
                ret = a->value.obj->get_class()->get_operator("setattr");
                if(ret) {
                    ret = pa_function_call(ret, pa_list_t{a, pa_new_string(b), c}, pa_dict_t{}, a);
                    return ret;
                } 
            } 
            a->value.obj->set_member(b, c);
            return ret;
        default:
            goto type_mismatch;
    }
type_mismatch:
    printf("Runtime Error: Type mismatch(setattr).\n");
    exit(1);
}
inline pa_value_t* pa_operator_getattr(pa_value_t* a, pa_string_t b) {
    pa_value_t* ret;
    switch(a->type) {
        case pa_object:
            ret = a->value.obj->get_member(b);
            if(!ret) {
                ret = a->value.obj->get_class()->get_operator("getattr");
                if(ret) {
                    ret = pa_function_call(ret, pa_list_t{a, pa_new_string(b)}, pa_dict_t{}, a);
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
    printf("Runtime Error: Type mismatch(getattr).\n");
    exit(1);
}

inline pa_value_t* pa_operator_add(pa_value_t* a, pa_value_t* b) {
    pa_value_t* n;
    pa_list_t *l1, *l2;
    pa_list_t::iterator it;
    switch(a->type) {
        case pa_integer:
            switch(b->type) {
                case pa_integer:
                    return pa_new_integer(a->value.i64 + b->value.i64);
                default:
                    goto type_mismatch;
            }
        case pa_string:
            switch(b->type) {
                case pa_string:
                    return pa_new_string(*PV2STR(a) + *PV2STR(b));
                default:
                   goto type_mismatch;
            }
        case pa_list:
            switch(b->type) {
                case pa_list:
                    n = pa_new_list();
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
        case pa_object:
            n = a->value.obj->get_operator("+");
            if(n) {
                return pa_function_call(n, pa_list_t{b}, pa_dict_t{}, a);
            } else {
                goto type_mismatch;
            }
        default:
            goto type_mismatch; 
    }
type_mismatch:
    printf("Runtime Error: Type mismatch(+).\n");
    exit(1);
}

inline pa_value_t* pa_operator_subtract(pa_value_t *a, pa_value_t *b) {
    pa_value_t* n;
    switch(a->type) {
        case pa_integer:
            switch(b->type) {
                case pa_integer:
                    return pa_new_integer(a->value.i64 - b->value.i64);
                default:
                    goto type_mismatch;
            }
        case pa_object:
            n = a->value.obj->get_operator("-");
            if(n) {
                return pa_function_call(n, pa_list_t{b}, pa_dict_t{}, a);
            } else {
                goto type_mismatch;
            }
        default:
            goto type_mismatch; 
    }
type_mismatch:
    printf("Runtime Error: Type mismatch(-).\n");
    exit(1);
}

inline pa_value_t* pa_operator_multiply(pa_value_t* a, pa_value_t* b) {
    pa_value_t* n;
    switch(a->type) {
        case pa_integer:
            switch(b->type) {
                case pa_integer:
                    return pa_new_integer(a->value.i64 * b->value.i64);
                default:
                    goto type_mismatch;
            }
        case pa_object:
            n = a->value.obj->get_operator("*");
            if(n) {
                return pa_function_call(n, pa_list_t{b}, pa_dict_t{}, a);
            } else {
                goto type_mismatch;
            }
        default:
            goto type_mismatch; 
    }
type_mismatch:
    printf("Runtime Error: Type mismatch(*).\n");
    exit(1);
}

inline pa_value_t* pa_operator_divide(pa_value_t* a, pa_value_t* b) {
    pa_value_t* n;
    switch(a->type) {
        case pa_integer:
            switch(b->type) {
                case pa_integer:
                    return pa_new_integer(a->value.i64 / b->value.i64);
                default:
                    goto type_mismatch;
            }
        case pa_object:
            n = a->value.obj->get_operator("/");
            if(n) {
                return pa_function_call(n, pa_list_t{b}, pa_dict_t{}, a);
            } else {
                goto type_mismatch;
            }
        default:
            goto type_mismatch; 
    }
type_mismatch:
    printf("Runtime Error: Type mismatch(/).\n");
    exit(1);
}

inline pa_value_t* pa_operator_modulo(pa_value_t* a, pa_value_t* b) {
    pa_value_t* n;
    switch(a->type) {
        case pa_integer:
            switch(b->type) {
                case pa_integer:
                    return pa_new_integer(a->value.i64 % b->value.i64);
                default:
                    goto type_mismatch;
            }
        case pa_object:
            n = a->value.obj->get_operator("mod");
            if(n) {
                return pa_function_call(n, pa_list_t{b}, pa_dict_t{}, a);
            } else {
                goto type_mismatch;
            }
        default:
            goto type_mismatch; 
    }
type_mismatch:
    printf("Runtime Error: Type mismatch(mod).\n");
    exit(1);
}


inline pa_value_t* pa_operator_eq(pa_value_t* a, pa_value_t* b) {
    pa_value_t* n;
    switch(a->type) {
        case pa_integer:
            switch(b->type) {
                case pa_integer:
                    return pa_new_boolean(a->value.i64 == b->value.i64);
                default:
                    goto type_mismatch;
            }
        case pa_string:
            switch(b->type) {
                case pa_string:
                    return pa_new_boolean((*PV2STR(a)) == (*PV2STR(b)));
                default:
                    goto type_mismatch;
            }
        case pa_object:
            n = a->value.obj->get_operator("==");
            if(n) {
                return pa_function_call(n, pa_list_t{b}, pa_dict_t{}, a);
            } else {
                goto type_mismatch;
            }
        default:
            goto type_mismatch; 
    }
type_mismatch:
    printf("Runtime Error: Type mismatch(==).\n");
    exit(1);
}

inline pa_value_t* pa_operator_neq(pa_value_t* a, pa_value_t* b) {
    pa_value_t* n;
    switch(a->type) {
        case pa_integer:
            switch(b->type) {
                case pa_integer:
                    return pa_new_integer(a->value.i64 != b->value.i64);
                default:
                    goto type_mismatch;
            }
        case pa_string:
            switch(b->type) {
                case pa_string:
                    return pa_new_boolean((*PV2STR(a)) != (*PV2STR(b)));
                default:
                    goto type_mismatch;
            }
        case pa_object:
            n = a->value.obj->get_operator("!=");
            if(n) {
                return pa_function_call(n, pa_list_t{b}, pa_dict_t{}, a);
            } else {
                goto type_mismatch;
            }
        default:
            goto type_mismatch; 
    }
type_mismatch:
    printf("Runtime Error: Type mismatch(!=).\n");
    exit(1);
}

inline pa_value_t* pa_operator_gt(pa_value_t* a, pa_value_t* b) {
    pa_value_t* n;
    switch(a->type) {
        case pa_integer:
            switch(b->type) {
                case pa_integer:
                    return pa_new_boolean(a->value.i64 > b->value.i64);
                default:
                    goto type_mismatch;
            }
        case pa_object:
            n = a->value.obj->get_operator(">=");
            if(n) {
                return pa_function_call(n, pa_list_t{b}, pa_dict_t{}, a);
            } else {
                goto type_mismatch;
            }
        default:
            goto type_mismatch; 
    }
type_mismatch:
    printf("Runtime Error: Type mismatch(>).\n");
    exit(1);
}

inline pa_value_t* pa_operator_gte(pa_value_t* a, pa_value_t* b) {
    pa_value_t* n;
    switch(a->type) {
        case pa_integer:
            switch(b->type) {
                case pa_integer:
                    return pa_new_boolean(a->value.i64 >= b->value.i64);
                default:
                    goto type_mismatch;
            }
        case pa_object:
            n = a->value.obj->get_operator(">=");
            if(n) {
                return pa_function_call(n, pa_list_t{b}, pa_dict_t{}, a);
            } else {
                goto type_mismatch;
            }
        default:
            goto type_mismatch; 
    }
type_mismatch:
    printf("Runtime Error: Type mismatch(>=).\n");
    exit(1);
}

inline pa_value_t* pa_operator_lt(pa_value_t* a, pa_value_t* b) {
    pa_value_t* n;
    switch(a->type) {
        case pa_integer:
            switch(b->type) {
                case pa_integer:
                    return pa_new_boolean(a->value.i64 < b->value.i64);
                default:
                    goto type_mismatch;
            }
        case pa_object:
            n = a->value.obj->get_operator("<");
            if(n) {
                return pa_function_call(n, pa_list_t{b}, pa_dict_t{}, a);
            } else {
                goto type_mismatch;
            }
        default:
            goto type_mismatch; 
    }
type_mismatch:
    printf("Runtime Error: Type mismatch(<).\n");
    exit(1);
}

inline pa_value_t* pa_operator_lte(pa_value_t* a, pa_value_t* b) {
    pa_value_t* n;
    switch(a->type) {
        case pa_integer:
            switch(b->type) {
                case pa_integer:
                    return pa_new_boolean(a->value.i64 <= b->value.i64);
                default:
                    goto type_mismatch;
            }
        case pa_object:
            n = a->value.obj->get_operator("<=");
            if(n) {
                return pa_function_call(n, pa_list_t{b}, pa_dict_t{}, a);
            } else {
                goto type_mismatch;
            }
        default:
            goto type_mismatch; 
    }
type_mismatch:
    printf("Runtime Error: Type mismatch(<=).\n");
    exit(1);
}

inline pa_value_t* pa_operator_right(pa_value_t* a, pa_value_t* b) {
    // Flow operator (right).
    pa_value_t* n;
    pa_list_t *l1, *l2;
    pa_list_t::iterator it;
    switch(a->type) {
        case pa_list:
            switch(b->type) {
                case pa_function:
                    // map(list->list) with a func
                    n = pa_new_list();
                    l1 = PV2LIST(a);
                    l2 = PV2LIST(n);
                    for(it = l1->begin(); it != l1->end(); ++it){
                        l2->push_back(pa_function_call(b, pa_list_t{*it}, pa_dict_t{}, a));
                    }
                    return n;
                default:
                    goto type_mismatch;
            }
        case pa_object:
            n = a->value.obj->get_operator("->");
            if(n) {
                return pa_function_call(n, pa_list_t{b}, pa_dict_t{}, a);
            } else {
                goto type_mismatch;
            }
        default:
            goto type_mismatch; 
    }
type_mismatch:
    printf("Runtime Error: Type mismatch(->).\n");
    exit(1);
}


inline pa_value_t* pa_operator_or(pa_value_t* a, pa_value_t* b) {
    pa_value_t* n;
    switch(a->type) {
        case pa_boolean:
            switch(b->type) {
                case pa_boolean:
                    return pa_new_boolean(a->value.b || b->value.b);
                default:
                    goto type_mismatch;
            }
        case pa_object:
            n = a->value.obj->get_operator("or");
            if(n) {
                return pa_function_call(n, pa_list_t{b}, pa_dict_t{}, a);
            } else {
                goto type_mismatch;
            }
        default:
            goto type_mismatch; 
    }
type_mismatch:
    printf("Runtime Error: Type mismatch(or).\n");
    exit(1);
}

inline pa_value_t* pa_operator_and(pa_value_t* a, pa_value_t* b) {
    pa_value_t* n;
    switch(a->type) {
        case pa_boolean:
            switch(b->type) {
                case pa_boolean:
                    return pa_new_boolean(a->value.b && b->value.b);
                default:
                    goto type_mismatch;
            }
        case pa_object:
            n = a->value.obj->get_operator("and");
            if(n) {
                return pa_function_call(n, pa_list_t{b}, pa_dict_t{}, a);
            } else {
                goto type_mismatch;
            }
        default:
            goto type_mismatch; 
    }
type_mismatch:
    printf("Runtime Error: Type mismatch(and).\n");
    exit(1);
}

inline pa_value_t* pa_operator_length(pa_value_t* a) {
    pa_value_t* n;
    pa_list_t* l;
    pa_string_t* s;
    switch(a->type) {
        case pa_list:
            l = PV2LIST(a);
            return pa_new_integer(l->size());
        case pa_string:
            s = PV2STR(a);
            return pa_new_integer(s->length());
        case pa_object:
            n = a->value.obj->get_operator("length");
            if(n) {
                return pa_function_call(n, pa_list_t{}, pa_dict_t{}, a);
            } else {
                goto type_mismatch;
            }
        default:
            goto type_mismatch; 
    }

type_mismatch:
    printf("Runtime Error: Type mismatch(length).\n");
    exit(1);
}

// Utilities
inline pa_value_t* pa_import(pa_string_t name) {
    replace(name.begin(), name.end(), '.', '/');

    //TODO Make it functional on Windows, Mac as well.
    pa_string_t file_path;
    pa_string_t file_name = "/" + name + ".so";
    const char* pa_home = getenv("PA_HOME");
    pa_string_t paths_to_search[] = {
        ".",
        "./libs",
        pa_home ? pa_string_t(pa_home) + "/libs" : "/usr/local/palang/libs"
    };
    
    for(unsigned i = 0; i <= 2; i++) {
        file_path = paths_to_search[i] + file_name;
        if(access(file_path.c_str(), F_OK) != -1) {
            break;   
        }
    }

    void* handle = dlopen(file_path.c_str(), RTLD_NOW | RTLD_GLOBAL);

    if(handle) {
        pa_value_t*(*mod_init)() = (pa_value_t*(*)()) dlsym(handle, "PA_INIT");

        pa_value_t* mod = mod_init();

        pa_value_t* mod_class = pa_new_class();
        mod_class->value.cls->set_operator("getattr", pa_new_function([=](pa_list_t args, pa_dict_t kwargs, pa_value_t* _this) -> pa_value_t* {
            pa_value_t *__this = pa_get_argument(args, kwargs, 0, "", pa_new_nil());
            pa_value_t *attr_name = pa_get_argument(args, kwargs, 1, "", pa_new_nil());
            pa_value_t* attr = pa_operator_getitem(mod, attr_name); 
            if(attr){ 
                return attr; 
            } else {
                printf("Runtime Error: no such name in the module: %s.%s\n", name.c_str(), PV2STR(attr_name)->c_str());
                exit(1);
            }
        }));

        pa_value_t* obj = pa_new_object(mod_class->value.cls);
        return obj;
    } else {
        printf("Runtime Error: %s\n", dlerror());
        exit(1);
    }
}

inline void PA_ENTER(int argc, char** argv, char** env) {
    //TODO 
    GC_INIT(); GC_enable_incremental();
}

inline int PA_LEAVE(pa_value_t *ret) {
    //TODO Return value
    return 0;
}

// Intrinsics
#define INTRINSICS() \
    pa_value_t *_print; \
    pa_value_t *_range; \
    pa_value_t *_input; \
    pa_value_t *_len; \
    _range = pa_new_function([](pa_list_t args, pa_dict_t kwargs, pa_value_t* _this) -> pa_value_t* { \
        pa_value_t *start = pa_get_argument(args, kwargs, 0, "start", pa_new_nil()); \
        pa_value_t *end = pa_get_argument(args, kwargs, 1, "end", pa_new_nil()); \
        pa_value_t *step = pa_get_argument(args, kwargs, 2, "step", pa_new_integer(1)); \
        \
        pa_value_t *l = pa_new_list(); \
        if(start->type == pa_integer && end->type == pa_integer && step->type == pa_integer) {  \
            for(int64_t i = start->value.i64; i <= end->value.i64; i+=step->value.i64) { \
                pa_value_t *index = pa_new_integer(i); \
                PV2LIST(l)->push_back(index); \
            } \
            return l; \
        } else { \
            printf("Runtime Error: Type mismatch(range).\n"); \
            exit(1); \
        } \
    }); \
    _print = pa_new_function([](pa_list_t args, pa_dict_t kwargs, pa_value_t* _this) -> pa_value_t* { \
        pa_list_t::iterator it; \
        for(it = args.begin(); it != args.end(); ++it) { \
            pa_value_t* msg = *it; \
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
        return pa_new_nil(); \
    }); \
    _input = pa_new_function([](pa_list_t args, pa_dict_t kwargs, pa_value_t* _this) -> pa_value_t* { \
        long long int N; \
        register int t = scanf("%lld", &N); \
        pa_value_t* n = pa_new_integer(N); \
        return n; \
    }); \
    _len = pa_new_function([](pa_list_t args, pa_dict_t kwargs, pa_value_t* _this) -> pa_value_t* { \
        pa_value_t *o = pa_get_argument(args, kwargs, 0, "object", pa_new_nil()); \
        switch(o->type) {\
            case pa_list: \
                return pa_new_integer(PV2LIST(o)->size()); \
            case pa_string: \
                return pa_new_integer(PV2STR(o)->length()); \
            default: \
                printf("Runtime Error: type mismatch(%d).\n", o->type); \
                exit(1); \
                break; \
        } \
    });


#endif
