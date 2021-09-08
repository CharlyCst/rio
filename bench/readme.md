# Bench

Bench is a small benchmarking tool based on Linux's `perf_event` API and collect various metrics such as instructions per cycle, total execution time or CPU usage.

Bench has two mode, the default is to simply run an executable, to other option
is to use a shared library (.so on Linux): it expects the library to respect
the following C interface:

```c
void init(int argc, char *argv[])
void run()
void cleanup()
```

Only the execution of the `run` method will be benchmarked, allowing different frameworks to perform arbitrary initialization & cleanup without being penalized for it.

Examples of programs to benchmark are available under the `example` folder, those are built with `cargo build` and ends up in the `build` directory.

```sh
cargo build # Build the example programs
cargo run -- -c ./build/simple.so

	cycles:          773893227
	instr/cycles:    2.33
	cpu usage:       0.46
	wall clock:      1.87s
```

To learn more about the `bench` CLI run `bench --help` or `cargo run -- --help`

