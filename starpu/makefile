SHARED_CFLAGS= -shared
CFLAGS= -lstarpu-1.3 -fPIC -O3 -I/usr/local/include/starpu/1.3 -L/usr/local/lib
CC=gcc

%.so: %.o
	$(CC) $(CFLAGS) $(SHARED_CFLAGS) $^ -o $@

%: %.o
	$(CC) $(CFLAGS) $^ -o $@

%.o: %.c
	$(CC) $(CFLAGS) -c $^ -o $@
