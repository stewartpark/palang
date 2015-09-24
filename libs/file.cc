#include <palang.h>
#include <stdio.h> /* for printf() and fprintf() */ 
#include <sys/types.h> /* for Socket data types */ 
#include <sys/socket.h> /* for socket(), connect(), send(), and recv() */ 
#include <netinet/in.h> /* for IP Socket data types */ 
#include <arpa/inet.h> /* for sockaddr_in and inet_addr() */ 
#include <stdlib.h> /* for atoi() */ 
#include <string.h> /* for memset() */ 
#include <unistd.h> /* for close() */


pa_value_t* _open(pa_value_t* args, pa_value_t* kwargs) {
    pa_value_t* filename = pa_get_argument(args, kwargs, 0, "filename", pa_new_nil());
    pa_value_t* mode = pa_get_argument(args, kwargs, 1, "mode", pa_new_string("r"));

    const char* fn = PV2STR(filename)->c_str();
    const char* md = PV2STR(mode)->c_str();

    FILE* fp = fopen(fn, md);

    return pa_new_integer((int64_t)fp);
}

pa_value_t* _close(pa_value_t* args, pa_value_t* kwargs) {
    pa_value_t* handle = pa_get_argument(args, kwargs, 0, "handle", pa_new_nil());
    
    FILE* fp = (FILE*)(handle->value.ptr);    

    fclose(fp);
    return pa_new_nil();
}


pa_value_t* _read(pa_value_t* args, pa_value_t* kwargs) {
    pa_value_t* handle = pa_get_argument(args, kwargs, 0, "handle", pa_new_nil());
    char* buffer = (char*)malloc(sizeof(char) * 1024);
    FILE* fp = (FILE*)handle->value.ptr;    

    size_t szRead = fread(buffer, sizeof(char), 1024, fp);

    return pa_new_string(string(buffer));
}


pa_value_t* _write(pa_value_t* args, pa_value_t* kwargs) {
    pa_value_t* handle = pa_get_argument(args, kwargs, 0, "handle", pa_new_nil());
    pa_value_t* _buffer = pa_get_argument(args, kwargs, 1, "buffer", pa_new_nil());
    char* buffer = (char*)(PV2STR(_buffer)->c_str());
    FILE* fp = (FILE*)handle->value.ptr;    

    fwrite(buffer, sizeof(char), strlen(buffer), fp);
    
    return pa_new_nil();
}


extern "C" pa_value_t* PA_INIT() {
    return pa_new_dictionary(
        pa_new_dictionary_kv(pa_new_string("open"), pa_new_function(_open)),
        pa_new_dictionary_kv(pa_new_string("close"), pa_new_function(_close)),
        pa_new_dictionary_kv(pa_new_string("write"), pa_new_function(_write)),
        pa_new_dictionary_kv(pa_new_string("read"), pa_new_function(_read))
    );       
}
