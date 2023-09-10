#!/usr/bin/bash
# To generate the C program that outputs packed binary data, for testing cstruct2
# with read_test.py

gcc -o gen read_test_generator.c