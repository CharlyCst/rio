------------------------- MODULE RunInOrderModelChecker3x3 ---------------------
EXTENDS RunInOrder, TLC, Integers

InputWorkers == {"w1", "w2"}
InputData    == {"d11", "d12", "d13", "d21", "d22", "d23", "d31", "d32", "d33"}
InputMapping == [tid \in Int |-> IF tid % 2 = 0 THEN "w1" ELSE "w2"]

(* ————————————————————— LU Factorization Control Flow —————————————————————— *)

InputControlFlow == {
    <<"fact1", 1>>,
    <<"panel21", 2>>,
    <<"panel31", 3>>,
    <<"panel12", 4>>,
    <<"panel13", 5>>,
    <<"gemm22", 6>>,
    <<"gemm23", 7>>,
    <<"gemm32", 8>>,
    <<"gemm33", 9>>,

    <<"fact2", 10>>,
    <<"panel32", 11>>,
    <<"panel23", 12>>,
    <<"last_gemm33", 13>>,

    <<"fact3", 14>>
}

(* ————————————————————————————— Defining Tasks ————————————————————————————— *)

NoDependency == [
    d11 |-> "None",
    d12 |-> "None",
    d13 |-> "None",
    d21 |-> "None",
    d22 |-> "None",
    d23 |-> "None",
    d31 |-> "None",
    d32 |-> "None",
    d33 |-> "None"
]

Read11 == [NoDependency EXCEPT !["d11"] = "R"]
Read22 == [NoDependency EXCEPT !["d22"] = "R"]
Read33 == [NoDependency EXCEPT !["d33"] = "R"]
Write11 == [NoDependency EXCEPT !["d11"] = "W"]
Write22 == [NoDependency EXCEPT !["d22"] = "W"]
Write23 == [NoDependency EXCEPT !["d23"] = "W"]
Write32 == [NoDependency EXCEPT !["d32"] = "W"]
Write33 == [NoDependency EXCEPT !["d33"] = "W"]

InputTasks == [
    fact1 |-> Write11,
    fact2 |-> Write22,
    fact3 |-> Write33,

    panel21 |-> [Read11 EXCEPT !["d21"] = "W"],
    panel31 |-> [Read11 EXCEPT !["d31"] = "W"],
    panel12 |-> [Read11 EXCEPT !["d12"] = "W"],
    panel13 |-> [Read11 EXCEPT !["d13"] = "W"],
    panel23 |-> [Read22 EXCEPT !["d23"] = "W"],
    panel32 |-> [Read22 EXCEPT !["d32"] = "W"],

    gemm22 |-> [[Write22 EXCEPT !["d12"] = "R"] EXCEPT !["d21"] = "R"],
    gemm32 |-> [[Write32 EXCEPT !["d12"] = "R"] EXCEPT !["d31"] = "R"],
    gemm23 |-> [[Write23 EXCEPT !["d13"] = "R"] EXCEPT !["d21"] = "R"],
    gemm33 |-> [[Write33 EXCEPT !["d13"] = "R"] EXCEPT !["d31"] = "R"],
    last_gemm33 |-> [[Write33 EXCEPT !["d23"] = "R"] EXCEPT !["d32"] = "R"]
]

(* ——————————————————————————————— Properties ——————————————————————————————— *)

PropertyIsSTF == STF!Spec
=============================================================================
