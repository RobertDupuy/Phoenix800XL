/* Test transport only: route Altirra's local UI socket over loopback TCP.
 * Neither emulated hardware nor game input/memory is altered by this shim.
 * Build: cc -shared -fPIC frontend_tcp.c -o frontend_tcp.so -ldl
 */
#define _GNU_SOURCE
#include <sys/socket.h>
#include <sys/un.h>
#include <netinet/in.h>
#include <dlfcn.h>
#include <stdio.h>
#include <string.h>
int socket(int domain, int type, int protocol) {
    int (*fn)(int,int,int) = dlsym(RTLD_NEXT, "socket");
    return fn(domain == AF_UNIX ? AF_INET : domain, type, protocol);
}
int bind(int fd, const struct sockaddr *addr, socklen_t len) {
    int (*fn)(int,const struct sockaddr*,socklen_t) = dlsym(RTLD_NEXT, "bind");
    if (addr->sa_family == AF_UNIX &&
        !strncmp(((const struct sockaddr_un*)addr)->sun_path, "/tmp/altirra-test-", 18)) {
        struct sockaddr_in in = {.sin_family=AF_INET,
            .sin_addr.s_addr=htonl(INADDR_LOOPBACK), .sin_port=0};
        int result = fn(fd, (struct sockaddr*)&in, sizeof(in));
        if (!result) {
            socklen_t size=sizeof(in);
            getsockname(fd, (struct sockaddr*)&in, &size);
            fprintf(stderr, "[UI transport] loopback-port: %u\n", ntohs(in.sin_port));
            fflush(stderr);
        }
        return result;
    }
    return fn(fd, addr, len);
}
