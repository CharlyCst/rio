---------------------------- MODULE STFModelChecker2x2 -------------------------
EXTENDS STFSpec, TLC

InputWorkers == {"w1", "w2"}
InputData    == {"d11", "d12", "d21", "d22"}

(* ————————————————————— LU Factorization Control Flow —————————————————————— *)

InputControlFlow == {
    <<"fact1", 1>>,
    <<"panel21", 2>>,
    <<"panel12", 4>>,
    <<"gemm22", 6>>,
    <<"fact2", 10>>
}

(* ————————————————————————————— Defining Tasks ————————————————————————————— *)

NoDependency == [
    d11 |-> "None",
    d12 |-> "None",
    d21 |-> "None",
    d22 |-> "None"
]

Read11 == [NoDependency EXCEPT !["d11"] = "R"]
Read22 == [NoDependency EXCEPT !["d22"] = "R"]
Write11 == [NoDependency EXCEPT !["d11"] = "W"]
Write22 == [NoDependency EXCEPT !["d22"] = "W"]

InputTasks == [
    fact1 |-> Write11,
    fact2 |-> Write22,
    panel21 |-> [Read11 EXCEPT !["d21"] = "W"],
    panel12 |-> [Read11 EXCEPT !["d12"] = "W"],
    gemm22 |-> [[Write22 EXCEPT !["d12"] = "R"] EXCEPT !["d21"] = "R"]
]

(* ——————————————————————————————— Properties ——————————————————————————————— *)

PropertyDataRaceFreedom == []DataRaceFreedom
PropertyTermination     == <>Terminated
===============================================================================
