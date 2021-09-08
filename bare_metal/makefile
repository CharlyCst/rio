SHARED_CFLAGS= -shared
MKL_FLAGS= -DMKL_ILP64 -m64 -L$(LD_LIBRARY_PATH) -Wl,--no-as-needed -lmkl_intel_ilp64 -lmkl_sequential -lmkl_core -lpthread -lm -ldl
CFLAGS= -fPIC -O3
CC=gcc

%.so: %.o
	$(CC) $(CFLAGS) $(SHARED_CFLAGS) $^ -o $@

%: %.o
	$(CC) $(CFLAGS) $^ -o $@

%.o: %.c
	$(CC) $(CFLAGS) -c $^ -o $@
