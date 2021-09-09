#!/bin/sh

java -cp tla2tools.jar tlc2.TLC RunInOrderModelChecker.tla -deadlock
