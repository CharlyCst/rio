/*
 * A simple LU decomposition without pivoting on top of StarPU
 */

#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

// Default values
static int N_REPEAT = 1;
static int N = 1000;
static int NB_TILES_ROW = 30;
static int NB_TILES_COL = 32;

// Matrix
static double *M;

// ———————————————————————————————— Kernels ————————————————————————————————— //

static void counter() {
  // We use volatile to force the compiler to actually perform the writes
  volatile uint64_t c = 0;
  // The Rust version unroll by default, for fair comparison we force unrolling
  // in the C version too.
#pragma GCC unroll 8
  for (uint64_t i = 0; i < N; i++) {
    c = i;
  }
}

/* Triangular factorization of the tile. */
static void trfr(double *tile) { counter(); }

/* Update one of the tile below the pivot tile after it has been factorized.
 */
static void panel_update(const double *pivot_tile, double *tile) { counter(); }

/* Perform a triangular update. */
static void trsm(const double *pivot_tile, double *tile) { counter(); }

/* Compute C = C - A B */
static void gemm(const double *a, const double *b, double *c) { counter(); }

// ————————————————————————————— Entry Points ——————————————————————————————— //

void init(int argc, char *argv[]) {
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
  int n = NB_TILES_ROW;
  if (NB_TILES_COL < NB_TILES_ROW) {
    n = NB_TILES_COL;
  }
  for (int repeat = 0; repeat < N_REPEAT; repeat++) {
    for (int i = 0; i < n; i++) {
      // Triangular factorization
      counter();

      // Panel update
      for (int row = i + 1; row < NB_TILES_COL; row++) {
        counter();
      }

      // Triangular update
      for (int col = i + 1; col < NB_TILES_ROW; col++) {
        counter();
      }

      // GEMM update
      for (int row = i + 1; row < NB_TILES_COL; row++) {
        for (int col = i + 1; col < NB_TILES_ROW; col++) {
          counter();
        }
      }
    }
  }
}

int main(int argc, char *argv[]) {
  init(argc, argv);
  run();
  cleanup();
}
