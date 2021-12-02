#!/bin/sh

java -cp tla2tools.jar tlc2.TLC RunInOrderModelChecker2x2.tla -deadlock -workers auto
