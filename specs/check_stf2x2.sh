#!/bin/sh

java -cp tla2tools.jar tlc2.TLC STFModelChecker2x2.tla -deadlock -workers auto
