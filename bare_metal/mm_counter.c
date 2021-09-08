/*
 * A simple single-threaded tiled matrix multiplication.
 */

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

// Default values
static int N_REPEAT = 1;
static int N = 1000;
static int N_TILES = 24;

// ————————————————————————————————— Kernel ————————————————————————————————— //

static void count() {
  // We use volatile to force the compiler to actually perform the writes
  volatile uint64_t c = 0;
  // The Rust version unroll by default, for fair comparison we force unrolling
  // in the C version too.
#pragma GCC unroll 8
  for (uint64_t i = 0; i < N; i++) {
    c = i;
  }
}

// ———————————————————————————— Bench Interface ————————————————————————————— //

void init(int argc, char *argv[]) {
  // Parse arguments
  int arg = 0;
  for (int i = 1; i < argc; i++) {
    int value = atoi(argv[i]);
    if (arg == 0) {
      N_REPEAT = value;
      arg++;
    } else if (arg == 1) {
      N = value;
      arg++;
    } else {
      printf("Too many arguments\n");
      exit(1);
    }
  }
}

void cleanup() {}

void run() {
  for (int repeat = 0; repeat < N_REPEAT; repeat++) {
    for (int i = 0; i < N_TILES; i++) {
      for (int j = 0; j < N_TILES; j++) {
        for (int k = 0; k < N_TILES; k++) {
          count();
        }
      }
    }
  }
}

// —————————————————————————————————— Main —————————————————————————————————— //

int main(int argc, char *argv[]) {
  init(argc, argv);
  run();
  cleanup();
}

