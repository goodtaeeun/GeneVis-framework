#!/bin/bash

apt-get install texinfo
cd Logger && make && cd llvm_mode && make
