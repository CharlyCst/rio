/*
 * A simple single-threaded matrix multiplication.
 */

#include <bits/time.h>
#include <mkl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

// Default values
static int N = 8;
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

// ————————————————————————————————— Debug —————————————————————————————————— //

static void print_matrix(double *M) {
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
      } else {
        printf("Too many arguments\n");
        exit(1);
      }
    }
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
  cblas_dgemm(LAYOUT, NO_TRANSPOSE, NO_TRANSPOSE, N, N, N, 1, A, N, B, N, 1, C,
              N);
}

// —————————————————————————————————— Main —————————————————————————————————— //

int main(int argc, char *argv[]) {
  struct timespec t0;
  struct timespec t1;
  
  init(argc, argv);
  clock_gettime(CLOCK_REALTIME, &t0);
  run();
  clock_gettime(CLOCK_REALTIME, &t1);
  printf("Debug:\n  %ld\n  %ld\n", t1.tv_nsec, t0.tv_nsec);
  printf("  %ld\n  %ld\n", t1.tv_sec, t0.tv_sec);

  long diff = t1.tv_nsec - t0.tv_nsec;
  float ns = diff > 0 ? (float)diff/1000000000. : (float)(1. + diff/1000000000.);
  printf("Elapsed: %f\n", (float)(t1.tv_sec - t0.tv_sec) + ns);
  cleanup();
}
