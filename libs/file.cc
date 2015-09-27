#include <palang.h>
#include <stdio.h>  
#include <stdlib.h>
#include <string.h>

pa_value_t* __open(pa_value_t* args, pa_value_t* kwargs, pa_value_t* _this) {
    pa_value_t* filename = pa_get_argument(args, kwargs, 0, "filename", pa_new_nil());
    pa_value_t* mode = pa_get_argument(args, kwargs, 1, "mode", pa_new_string("r"));

    const char* fn = PV2STR(filename)->c_str();
    const char* md = PV2STR(mode)->c_str();
    
    FILE* fp = fopen(fn, md);

    return pa_new_integer((int64_t)fp);
}

pa_value_t* __close(pa_value_t* args, pa_value_t* kwargs, pa_value_t* _this) {
    pa_value_t* handle = pa_get_argument(args, kwargs, 0, "handle", pa_new_nil());
    
    FILE* fp = (FILE *)(handle->value.ptr);    

    fclose(fp);

    return pa_new_nil();
}


pa_value_t* __read(pa_value_t* args, pa_value_t* kwargs, pa_value_t* _this) {
    pa_value_t* handle = pa_get_argument(args, kwargs, 0, "handle", pa_new_nil());

    char* buffer = (char*)GC_MALLOC(sizeof(char) * 1024);
    FILE* fp = (FILE*)(handle->value.i64);    


    size_t szRead = fread(buffer, sizeof(char), 1024, fp);


    return pa_new_string(string(buffer));
}

pa_value_t* __write(pa_value_t* args, pa_value_t* kwargs, pa_value_t* _this) {
    pa_value_t* handle = pa_get_argument(args, kwargs, 0, "handle", pa_new_nil());
    pa_value_t* _buffer = pa_get_argument(args, kwargs, 1, "buffer", pa_new_nil());
    char* buffer = (char*)(PV2STR(_buffer)->c_str());
    FILE* fp = (FILE*)handle->value.ptr;    

    fwrite(buffer, sizeof(char), strlen(buffer), fp);
    
    return pa_new_nil();
}


extern "C" pa_value_t* PA_INIT() {
    return pa_new_dictionary(
        pa_new_dictionary_kv(pa_new_string("open"), pa_new_function(__open)),
        pa_new_dictionary_kv(pa_new_string("close"), pa_new_function(__close)),
        pa_new_dictionary_kv(pa_new_string("write"), pa_new_function(__write)),
        pa_new_dictionary_kv(pa_new_string("read"), pa_new_function(__read))
    );       
}
