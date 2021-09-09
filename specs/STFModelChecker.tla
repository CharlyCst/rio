---------------------------- MODULE STFModelChecker -------------------------
EXTENDS STFSpec, TLC

InputWorkers     == {"w1", "w2", "w3"}
InputData        == {"d1", "d2"}
InputControlFlow == {
    <<"t1", 1>>,
    <<"t2", 2>>,
    <<"t3", 3>>,
    <<"t4", 4>>,
    <<"t5", 5>>,
    <<"t6", 6>>,
    <<"t7", 7>>,
    <<"t8", 8>>,
    <<"t9", 9>>,

    <<"t8", 10>>,
    <<"t5", 11>>,
    <<"t7", 12>>,
    <<"t3", 13>>,
    <<"t4", 14>>,
    <<"t1", 15>>
}
InputTasks == [
    t1 |-> [d1 |-> "W", d2 |-> "W"],
    t2 |-> [d1 |-> "W", d2 |-> "R"],
    t3 |-> [d1 |-> "W", d2 |-> "None"],
    t4 |-> [d1 |-> "R", d2 |-> "W"],
    t5 |-> [d1 |-> "R", d2 |-> "R"],
    t6 |-> [d1 |-> "R", d2 |-> "None"],
    t7 |-> [d1 |-> "None", d2 |-> "W"],
    t8 |-> [d1 |-> "None", d2 |-> "R"],
    t9 |-> [d1 |-> "None", d2 |-> "None"]
]

PropertyDataRaceFreedom == []DataRaceFreedom
PropertyTermination     == <>Terminated
=============================================================================
