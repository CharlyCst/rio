#include <unistd.h>
#include <stdio.h>

int NB_ITERATIONS = 30000000;
long result = 0;

void init(int argc, char *argv[]) {}
void cleanup() {}

void run() {
  // Do some stuff, not something too easy that is optimized away
  unsigned long u = 0;
  for (int i = 0; i < NB_ITERATIONS; i++) {
    u = (u + i) % NB_ITERATIONS;
  }
  printf("u = %lu\n", u);
  // Then sleep some time
  sleep(1);
}

int main() {
  run();
  return 0;
}
