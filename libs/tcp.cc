#include <palang.h>
#include <stdio.h> /* for printf() and fprintf() */ 
#include <sys/types.h> /* for Socket data types */ 
#include <sys/socket.h> /* for socket(), connect(), send(), and recv() */ 
#include <netinet/in.h> /* for IP Socket data types */ 
#include <arpa/inet.h> /* for sockaddr_in and inet_addr() */ 
#include <stdlib.h> /* for atoi() */ 
#include <string.h> /* for memset() */ 
#include <unistd.h> /* for close() */

pa_value_t* _socket(pa_value_t* args, pa_value_t* kwargs, pa_value_t* _this) {
    int sock = socket(PF_INET, SOCK_STREAM, IPPROTO_TCP);
    int optval = 1;
    setsockopt(sock, SOL_SOCKET, SO_REUSEPORT, &optval, sizeof(optval));
    return pa_new_integer(sock);
}

pa_value_t* _connect(pa_value_t* args, pa_value_t* kwargs, pa_value_t* _this) {
    pa_value_t* socket = pa_get_argument(args, kwargs, 0, "socket", pa_new_nil());
    pa_value_t* host = pa_get_argument(args, kwargs, 1, "host", pa_new_nil());
    pa_value_t* port = pa_get_argument(args, kwargs, 2, "port", pa_new_nil());

    struct sockaddr_in addr;
    
    memset(&addr, 0, sizeof(addr));
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = inet_addr(PV2STR(host)->c_str());
    addr.sin_port = htons(port->value.u16);
    
    int sock = socket->value.i32;
    
    return pa_new_integer(connect(sock, (struct sockaddr*)&addr, sizeof(addr)));
}

pa_value_t* _read(pa_value_t* args, pa_value_t* kwargs, pa_value_t* _this) {
    pa_value_t* socket = pa_get_argument(args, kwargs, 0, "socket", pa_new_nil());

    char* buffer = (char*)malloc(1024);
    int sock = socket->value.i32;
    
    recv(sock, buffer, 1024, 0);
    return pa_new_string(string(buffer));  
}

pa_value_t* _write(pa_value_t* args, pa_value_t* kwargs, pa_value_t* _this) {
    pa_value_t* socket = pa_get_argument(args, kwargs, 0, "socket", pa_new_nil());
    pa_value_t* _buffer = pa_get_argument(args, kwargs, 1, "buffer", pa_new_nil());

    const char* buffer = PV2STR(_buffer)->c_str();
    int sock = socket->value.i32;

    send(sock, buffer, strlen(buffer), 0);

    return pa_new_nil();
}

pa_value_t* _listen(pa_value_t* args, pa_value_t* kwargs, pa_value_t* _this) {
    pa_value_t* socket = pa_get_argument(args, kwargs, 0, "socket", pa_new_nil());
    pa_value_t* host= pa_get_argument(args, kwargs, 1, "host", pa_new_nil());
    pa_value_t* port = pa_get_argument(args, kwargs, 2, "port", pa_new_nil());

    int sock = socket->value.i32;
    struct sockaddr_in addr;
    
    memset(&addr, 0, sizeof(addr));
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = inet_addr(PV2STR(host)->c_str());
    addr.sin_port = htons(port->value.u16);
   
    bind(sock, (struct sockaddr *)&addr, sizeof addr); 
    return pa_new_integer(listen(sock, 1024));
}

pa_value_t* _accept(pa_value_t* args, pa_value_t* kwargs, pa_value_t* _this) {
    pa_value_t* socket = pa_get_argument(args, kwargs, 0, "socket", pa_new_nil());
    int sock = socket->value.i32;
    return pa_new_integer(accept(sock, NULL, NULL));
}

pa_value_t* _close(pa_value_t* args, pa_value_t* kwargs, pa_value_t* _this) {
    pa_value_t* socket = pa_get_argument(args, kwargs, 0, "socket", pa_new_nil());
    int sock = socket->value.i32;

    close(sock);

    return pa_new_nil();
}

extern "C" pa_value_t* PA_INIT() {
    return pa_new_dictionary(
        pa_new_dictionary_kv(pa_new_string("socket"), pa_new_function(_socket)),
        pa_new_dictionary_kv(pa_new_string("connect"), pa_new_function(_connect)),
        pa_new_dictionary_kv(pa_new_string("read"), pa_new_function(_read)),
        pa_new_dictionary_kv(pa_new_string("write"), pa_new_function(_write)),
        pa_new_dictionary_kv(pa_new_string("listen"), pa_new_function(_listen)),
        pa_new_dictionary_kv(pa_new_string("accept"), pa_new_function(_accept)),
        pa_new_dictionary_kv(pa_new_string("close"), pa_new_function(_close)),
    );       
}
