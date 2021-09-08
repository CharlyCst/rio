/*
 * A simple LU decomposition without pivoting on top of StarPU
 */

#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

// Default values
static int N = 8;
static int TILE_SIZE = 4;
static int N_TILES = 2;
static int DEBUG = 0;

// Matrix
static double *M;

/* Initialize and register the matrix M in StarPU */
static void init_matrix() {
  M = calloc(N * N, sizeof(double));
  for (int i = 0; i < N; i++) {
    for (int j = 0; j < N; j++) {
      M[i + j * N] = i == j ? 2 : 1;
    }
  }
}

// ————————————————————————————————— Debug —————————————————————————————————— //

static void print_matrix() {
  for (int i = 0; i < N; i++) {
    for (int j = 0; j < N; j++) {
      printf("\t%.2lf", M[i + j * N]);
    }
    printf("\n");
  }
}

static void check_result() {
  double epsilon = 1.0e-10;
  for (int col = 0; col < N; col++) {
    for (int row = 0; row < N; row++) {
      double value = 0;
      if (row <= col) {
        for (int k = 0; k < row; k++) {
          value += M[row + k * N] * M[k + col * N];
        }
        value += M[row + col * N];
      } else {
        for (int k = 0; k <= col; k++) {
          value += M[row + k * N] * M[k + col * N];
        }
      }
      double expected = row == col ? 2 : 1;
      double error = fabs(expected - value);
      if (error > epsilon) {
        printf("Error: got LU[%d, %d] = %f, expected %f\n\n", row, col, value,
               expected);
        print_matrix();
        exit(1);
      }
    }
  }
}

// ———————————————————————————————— Kernels ————————————————————————————————— //

/* Triangular factorization of the tile. */
static void trfr(double *tile) {
  for (int pivot = 0; pivot < TILE_SIZE - 1; pivot++) {
    double scaling_factor = 1 / tile[pivot + pivot * N];

    // Scale column
    for (int row = pivot + 1; row < TILE_SIZE; row++) {
      tile[row + pivot * N] *= scaling_factor;
    }

    // Gauss elimination
    for (int col = pivot + 1; col < TILE_SIZE; col++) {
      for (int row = pivot + 1; row < TILE_SIZE; row++) {
        tile[row + col * N] -= tile[pivot + col * N] * tile[row + pivot * N];
      }
    }
  }
}

/* Update one of the tile below the pivot tile after it has been factorized.
 */
static void panel_update(const double *pivot_tile, double *tile) {
  for (int pivot = 0; pivot < TILE_SIZE; pivot++) {
    double scaling_factor = 1 / pivot_tile[pivot + pivot * N];

    // Scale column
    for (int row = 0; row < TILE_SIZE; row++) {
      tile[row + pivot * N] *= scaling_factor;
    }

    // Gauss elimination
    for (int col = pivot + 1; col < TILE_SIZE; col++) {
      for (int row = 0; row < TILE_SIZE; row++) {
        tile[row + col * N] -=
            pivot_tile[pivot + col * N] * tile[row + pivot * N];
      }
    }
  }
}

/* Perform a triangular update. */
static void trsm(const double *pivot_tile, double *tile) {
  for (int row = 1; row < TILE_SIZE; row++) {
    for (int col = 0; col < TILE_SIZE; col++) {
      double sum = 0;
      for (int k = 0; k < row; k++) {
        sum += pivot_tile[row + k * N] * tile[k + col * N];
      }
      tile[row + col * N] -= sum;
    }
  }
}

/* Compute C = C - A B */
static void gemm(const double *a, const double *b, double *c) {
  for (int col = 0; col < TILE_SIZE; col++) {
    for (int row = 0; row < TILE_SIZE; row++) {
      double sum = 0;
      for (int k = 0; k < TILE_SIZE; k++) {
        sum += a[row + k * N] * b[k + col * N];
      }
      c[row + col * N] -= sum;
    }
  }
}

// ————————————————————————————— Entry Points ——————————————————————————————— //

void init(int argc, char *argv[]) {
  int arg = 0;
  for (int i = 1; i < argc; i++) {
    if (strcmp(argv[i], "-d") == 0) {
      DEBUG = 1;
    } else {
      int value = atoi(argv[i]);
      if (arg == 0) {
        N = value;
        arg++;
      } else if (arg == 1) {
        TILE_SIZE = value;
        arg++;
      } else {
        printf("Too many arguments\n");
        exit(1);
      }
    }
  }

  N_TILES = N / TILE_SIZE;
  if (N % TILE_SIZE != 0) {
    printf("Invalid tile size\n");
    exit(1);
  }

  // Initialize StarPU
  init_matrix();
}

void cleanup() {
  if (DEBUG) {
    check_result();
  }
  free(M);
}

void run() {
  for (int i = 0; i < N_TILES; i++) {
    // Triangular factorization
    double *pivot_tile = &M[i * TILE_SIZE + i * TILE_SIZE * N];
    trfr(pivot_tile);

    // Panel update
    for (int row = i + 1; row < N_TILES; row++) {
      double *tile = &M[row * TILE_SIZE + i * TILE_SIZE * N];
      panel_update(pivot_tile, tile);
    }

    // Triangular update
    for (int col = i + 1; col < N_TILES; col++) {
      double *tile = &M[i * TILE_SIZE + col * TILE_SIZE * N];
      trsm(pivot_tile, tile);
    }

    // GEMM update
    for (int row = i + 1; row < N_TILES; row++) {
      for (int col = i + 1; col < N_TILES; col++) {
        double *a = &M[row * TILE_SIZE + i * TILE_SIZE * N];
        double *b = &M[i * TILE_SIZE + col * TILE_SIZE * N];
        double *c = &M[row * TILE_SIZE + col * TILE_SIZE * N];
        gemm(a, b, c);
      }
    }
  }
}

int main(int argc, char *argv[]) {
  init(argc, argv);
  run();
  cleanup();
}
