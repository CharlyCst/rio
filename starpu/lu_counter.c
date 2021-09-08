/*
 * A simple LU decomposition without pivoting simulating computation with
 * counter increments.
 */

#include <starpu.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

// Default values
static int N_REPEAT = 1;
static int N = 1000;
static int NB_TILES_ROW = 30;
static int NB_TILES_COL = 32;

// Handles
static starpu_data_handle_t *M_h;

// ——————————————————————————————— Codelets ————————————————————————————————— //

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
static void cpu_trfr(void *handles[], void *arg) { counter(); }

/* Update one of the tile below the pivot tile after it has been factorized.
 */
static void cpu_panel_update(void *handles[], void *arg) { counter(); }

/* Perform a triangular update. */
static void cpu_trsm(void *handles[], void *arg) { counter(); }

/* Compute C = C - A B */
static void cpu_gemm(void *handles[], void *arg) { counter(); }

static struct starpu_codelet trfr_codelet = {
    .cpu_funcs = {cpu_trfr},
    .nbuffers = 1,
    .modes = {STARPU_RW},
    .name = "trfr",
};

static struct starpu_codelet panel_update_codelet = {
    .cpu_funcs = {cpu_panel_update},
    .nbuffers = 2,
    .modes = {STARPU_R, STARPU_RW},
    .name = "panel_update",
};

static struct starpu_codelet trsm_codelet = {.cpu_funcs = {cpu_trsm},
                                             .nbuffers = 2,
                                             .modes = {STARPU_R, STARPU_RW},
                                             .name = "trsm"};

static struct starpu_codelet gemm_codelet = {
    .cpu_funcs = {cpu_gemm},
    .nbuffers = 3,
    .modes = {STARPU_R, STARPU_R, STARPU_RW},
    .name = "gemm",
};

// ————————————————————————————————— Utils —————————————————————————————————— //

void register_data() {
  M_h = calloc(NB_TILES_COL * NB_TILES_ROW, sizeof(starpu_data_handle_t));

  for (int i = 0; i < NB_TILES_COL; i++) {
    for (int j = 0; j < NB_TILES_ROW; j++) {
      int handle_idx = i + j * NB_TILES_COL;
      starpu_variable_data_register(&M_h[handle_idx], 0, (uintptr_t)NULL, 0);
    }
  }
}

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

  // Initialize StarPU
  int ret = starpu_init(NULL);
  STARPU_CHECK_RETURN_VALUE(ret, "starpu_init");
  register_data();
}

void cleanup() { starpu_shutdown(); }

void run() {
  int ret;

  int n = NB_TILES_ROW;
  if (NB_TILES_COL < NB_TILES_ROW) {
    n = NB_TILES_COL;
  }
  for (int repeat = 0; repeat < N_REPEAT; repeat++) {
    for (int i = 0; i < n; i++) {
      // Triangular factorization
      starpu_data_handle_t pivot_tile = M_h[i + i * NB_TILES_COL];
      struct starpu_task *trfr_task = starpu_task_create();
      trfr_task->cl = &trfr_codelet;
      trfr_task->handles[0] = pivot_tile;
      ret = starpu_task_submit(trfr_task);
      STARPU_CHECK_RETURN_VALUE(ret, "starpu_task_submit");

      // Panel update
      for (int row = i + 1; row < NB_TILES_COL; row++) {
        struct starpu_task *panel_update_task = starpu_task_create();
        panel_update_task->cl = &panel_update_codelet;
        panel_update_task->handles[0] = pivot_tile;
        panel_update_task->handles[1] = M_h[row + i * NB_TILES_COL];
        ret = starpu_task_submit(panel_update_task);
        STARPU_CHECK_RETURN_VALUE(ret, "starpu_task_submit");
      }

      // Triangular update
      for (int col = i + 1; col < NB_TILES_ROW; col++) {
        struct starpu_task *trsm_task = starpu_task_create();
        trsm_task->cl = &trsm_codelet;
        trsm_task->handles[0] = pivot_tile;
        trsm_task->handles[1] = M_h[i + col * NB_TILES_COL];
        ret = starpu_task_submit(trsm_task);
        STARPU_CHECK_RETURN_VALUE(ret, "starpu_task_submit");
      }

      // GEMM update
      for (int row = i + 1; row < NB_TILES_COL; row++) {
          for (int col = i + 1; col < NB_TILES_ROW; col++) {
            struct starpu_task *gemm_task = starpu_task_create();
            gemm_task->cl = &gemm_codelet;
            gemm_task->handles[0] = M_h[row + i * NB_TILES_COL];
            gemm_task->handles[1] = M_h[i + col * NB_TILES_COL];
            gemm_task->handles[2] = M_h[row + col * NB_TILES_COL];
            ret = starpu_task_submit(gemm_task);
            STARPU_CHECK_RETURN_VALUE(ret, "starpu_task_submit");
          }
        }
      }
    }
    starpu_task_wait_for_all();
  }

  int main(int argc, char *argv[]) {
    init(argc, argv);
    run();
    cleanup();
  }
