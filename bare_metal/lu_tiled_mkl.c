/*
 * A simple LU decomposition without pivoting on top of StarPU
 */

#include <math.h>
#include <mkl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

// Default values
static int N = 8;
static int TILE_SIZE = 4;
static int N_TILES = 2;
static long long int LONG_N = 8;
static long long int LONG_TILE_SIZE = 4;
static long long int LONG_N_TILES = 2;
static int DEBUG = 0;

// Matrix
static double *M;

static const CBLAS_LAYOUT LAYOUT = CblasColMajor;
static const CBLAS_TRANSPOSE NO_TRANSPOSE = CblasNoTrans;
static const CBLAS_TRANSPOSE TRANSPOSE = CblasTrans;

/* Initialize and register the matrix M in StarPU */
static void init_matrix() {
  M = calloc(N * N, sizeof(double));
  for (int i = 0; i < N * N; i++) {
    M[i] = 1;
  }
  for (int i = 0; i < N; i++) {
    M[i + i * N] = 2;
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
  long long int error;
  mkl_dgetrfnp(&LONG_TILE_SIZE, &LONG_TILE_SIZE, tile, &LONG_N, &error);
}

/* Update one of the tile below the pivot tile after it has been factorized.
 */
static void panel_update(const double *pivot_tile, double *tile) {
  cblas_dtrsm(LAYOUT, CblasRight, CblasUpper, NO_TRANSPOSE, CblasNonUnit,
              TILE_SIZE, TILE_SIZE, 1., pivot_tile, N, tile, N);
}

/* Perform a triangular update. */
static void trsm(const double *pivot_tile, double *tile) {
  cblas_dtrsm(LAYOUT, CblasLeft, CblasLower, NO_TRANSPOSE, CblasUnit, TILE_SIZE,
              TILE_SIZE, 1., pivot_tile, N, tile, N);
}

/* Compute C = C - A B */
static void gemm(const double *a, const double *b, double *c) {
  cblas_dgemm(LAYOUT, NO_TRANSPOSE, NO_TRANSPOSE, TILE_SIZE, TILE_SIZE,
              TILE_SIZE, -1, a, N, b, N, 1, c, N);
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

  LONG_N = N;
  LONG_N_TILES = N_TILES;
  LONG_TILE_SIZE = TILE_SIZE;

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
