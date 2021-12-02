#!/bin/sh

java -cp tla2tools.jar tlc2.TLC STFModelChecker3x3.tla -deadlock -workers auto
