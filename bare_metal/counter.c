/*
 * A simple program where each tasks consists in counting up to N.
 */

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

uint64_t N = 1000;
uint64_t N_TASKS = 1000;

static void cpu_count() {
  // We use volatile to force the compiler to actually perform the writes
  volatile uint64_t c = 0;
  // The Rust version unroll by default, for fair comparison we force unrolling
  // in the C version too.
#pragma GCC unroll 8
  for (uint64_t i = 0; i < N; i++) {
    c = i;
  }
}

void init(int argc, char *argv[]) {
  int arg = 0;
  for (int i = 1; i < argc; i++) {
    int value = atoi(argv[i]);
    if (arg == 0) {
      N_TASKS = value;
      arg++;
    } else if (arg == 1) {
      N = value;
      arg++;
    } else {
      printf("Too much arguments\n");
      exit(1);
    }
  }
}

void run() {
  int ret;
  for (int i = 0; i < N_TASKS; i++) {
    cpu_count();
  }
}

int main(int argc, char *argv[]) {
  init(argc, argv);
  run();
}
