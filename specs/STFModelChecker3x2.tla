---------------------------- MODULE STFModelChecker3x2 -------------------------
EXTENDS STFSpec, TLC

InputWorkers == {"w1", "w2"}
InputData    == {"d11", "d12", "d21", "d22", "d31", "d32"}

(* ————————————————————— LU Factorization Control Flow —————————————————————— *)

InputControlFlow == {
    <<"fact1", 1>>,
    <<"panel21", 2>>,
    <<"panel31", 3>>,
    <<"panel12", 4>>,
    <<"gemm22", 6>>,
    <<"gemm32", 8>>,
    <<"fact2", 10>>,
    <<"panel32", 11>>
}

(* ————————————————————————————— Defining Tasks ————————————————————————————— *)

NoDependency == [
    d11 |-> "None",
    d12 |-> "None",
    d21 |-> "None",
    d22 |-> "None",
    d31 |-> "None",
    d32 |-> "None"
]

Read11 == [NoDependency EXCEPT !["d11"] = "R"]
Read22 == [NoDependency EXCEPT !["d22"] = "R"]
Write11 == [NoDependency EXCEPT !["d11"] = "W"]
Write22 == [NoDependency EXCEPT !["d22"] = "W"]
Write32 == [NoDependency EXCEPT !["d32"] = "W"]

InputTasks == [
    fact1 |-> Write11,
    fact2 |-> Write22,

    panel21 |-> [Read11 EXCEPT !["d21"] = "W"],
    panel31 |-> [Read11 EXCEPT !["d31"] = "W"],
    panel12 |-> [Read11 EXCEPT !["d12"] = "W"],
    panel32 |-> [Read22 EXCEPT !["d32"] = "W"],

    gemm22 |-> [[Write22 EXCEPT !["d12"] = "R"] EXCEPT !["d21"] = "R"],
    gemm32 |-> [[Write32 EXCEPT !["d12"] = "R"] EXCEPT !["d31"] = "R"]
]

(* ——————————————————————————————— Properties ——————————————————————————————— *)

PropertyDataRaceFreedom == []DataRaceFreedom
PropertyTermination     == <>Terminated
===============================================================================
