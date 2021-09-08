/*
 * A simple program that consists in counting up to N * N_TASKS.
 */

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

uint64_t N = 1000;
uint64_t N_TASKS = 1000;

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
  volatile uint64_t c = 0;
  for (uint64_t i = 0; i < N * N_TASKS; i++) {
    c = i;
  }
}

int main(int argc, char *argv[]) {
  init(argc, argv);
  run();
}

