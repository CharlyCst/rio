/*
 * A simple single-threaded tiled matrix multiplication.
 */

#include <mkl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

// Default values
static int N = 8;
static int TILE_SIZE = 4;
static int N_TILES = 2;
static int DEBUG = 0;

// Matricies
static double *A;
static double *B;
static double *C;

static const CBLAS_LAYOUT LAYOUT = CblasColMajor;
static const CBLAS_TRANSPOSE NO_TRANSPOSE = CblasNoTrans;
static const CBLAS_TRANSPOSE TRANSPOSE = CblasTrans;

// ————————————————————————————————— Utils —————————————————————————————————— //

static void init_matrices() {
  A = calloc(N * N, sizeof(double));
  B = calloc(N * N, sizeof(double));
  C = calloc(N * N, sizeof(double));

  for (int i = 0; i < N; i++) {
    for (int j = 0; j < N; j++) {
      A[i + j * N] = i == j ? 2 : 0;
      B[i + j * N] = j + i * N;
      C[i + j * N] = 0;
    }
  }
}

static void free_matrices() {
  free(A);
  free(B);
  free(C);
}

// ————————————————————————————————— Kernel ————————————————————————————————— //

/* Computes `c = a b + c` using MKL. */
static void tile_mult(double *a, double *b, double *c) {
  cblas_dgemm(LAYOUT, NO_TRANSPOSE, NO_TRANSPOSE, TILE_SIZE, TILE_SIZE,
              TILE_SIZE, 1, a, N, b, N, 1, c, N);
}

// ————————————————————————————————— Debug —————————————————————————————————— //

static void print_matrix(double *M) {
  for (int i = 0; i < N; i++) {
    for (int j = 0; j < N; j++) {
      printf("\t%.2lf", M[i + j * N]);
    }
    printf("\n");
  }
}

static void check_result() {
  for (int i = 0; i < N; i++) {
    for (int j = 0; j < N; j++) {
      if (C[i + j * N] != 2 * B[i + j * N]) {
        printf("Error: C[%d, %d] = %f, expected %f\n", i, j, C[i + j * N],
               2 * B[i + j * N]);
        printf("\nC:\n");
        print_matrix(C);
        exit(1);
      }
    }
  }
}

// ———————————————————————————— Bench Interface ————————————————————————————— //

void init(int argc, char *argv[]) {
  N = 8;
  TILE_SIZE = 4;
  N_TILES = N / TILE_SIZE;

  // Parse arguments
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

  // Initialize matrices
  init_matrices();
}

void cleanup() {
  if (DEBUG) {
    check_result();
  }
  free_matrices();
}

void run() {
  for (int i = 0; i < N_TILES; i++) {
    for (int j = 0; j < N_TILES; j++) {
      for (int k = 0; k < N_TILES; k++) {
        tile_mult(&A[k * TILE_SIZE + j * TILE_SIZE * N],
                  &B[i * TILE_SIZE + k * TILE_SIZE * N],
                  &C[i * TILE_SIZE + j * TILE_SIZE * N]);
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
