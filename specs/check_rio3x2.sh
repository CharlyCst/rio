#!/bin/sh

java -cp tla2tools.jar tlc2.TLC RunInOrderModelChecker3x2.tla -deadlock -workers auto
