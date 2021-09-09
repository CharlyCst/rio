#!/bin/sh

java -cp tla2tools.jar tlc2.TLC STFModelChecker.tla -deadlock
