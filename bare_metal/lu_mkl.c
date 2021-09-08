/*
 * A simple LU decomposition without pivoting on top of StarPU
 */

#include <math.h>
#include <mkl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

// Default values
static long long int N = 8;
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
      } else {
        printf("Too many arguments\n");
        exit(1);
      }
    }
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
  long long int error;
  mkl_dgetrfnp(&N, &N, M, &N, &error);
  if (error) {
    exit(1);
  }
}

int main(int argc, char *argv[]) {
  init(argc, argv);
  run();
  cleanup();
}
