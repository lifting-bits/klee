#!/usr/bin/env python
"""
  Copyright (c) 2019 Trail of Bits, Inc.
 
  Licensed under the Apache License, Version 2.0 (the "License");
  you may not use this file except in compliance with the License.
  You may obtain a copy of the License at
 
      http://www.apache.org/licenses/LICENSE-2.0
 
  Unless required by applicable law or agreed to in writing, software
  distributed under the License is distributed on an "AS IS" BASIS,
  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
  See the License for the specific language governing permissions and
  limitations under the License.
"""
from binaryninja import *
from os import listdir
from sys import argv

"""
this program assumes that the memory file provided is in the workspace and only on 64 bit linux
"""

if len(argv) < 2:
    print("please specify the location of the memory directory in the workspace as an argument for this program")
    print("Example: `python locate_traces.py ./ws/memory/`")
    exit(1)


memory_directory_path = argv[1]
if memory_directory_path[-1] != "/":
    memory_directory_path += "/"

traces = []

def create_functions_in_binaryview(mapping):
    """
    locate function stub opcodes and adds entry point to a binaryview
    """
    bv = binaryview.BinaryViewType["Raw"].open(memory_directory_path + mapping)
    arch = binaryninja.Architecture["x86_64"]
    plat = binaryninja.Platform["linux-x86_64"]
    for i in range(0,len(bv),16):
        if (bv.read(i,1) == '\xff' and bv.read(i+1,1) == '\x25'):
            if (arch.get_instruction_info(bv.read(i, arch.max_instr_length), i)):
                binaryninja.core.BNAddFunctionForAnalysis(bv.handle, plat.handle, i)
                binaryninja.core.BNAddFunctionForAnalysis(bv.handle, plat.handle, i + 16)
    return bv


def mark_traces_in_mapping(mapping):
    bv = binaryview.BinaryViewType["ELF"].open(memory_directory_path + mapping)
    if not bv:
        if "lib" in mapping and "_so" in mapping:
            print("creating functions for mapping {}".format(mapping))
            bv = create_functions_in_binaryview(mapping)
        else:
            print("could not produce binary view for mapping {}".format(mapping))
            return
    else:
        print(memory_directory_path + mapping)
    bv.update_analysis_and_wait()
    base = int(mapping.split("_")[0], 16)
    pc = base
    for func in bv.functions:
        for bb in func:
            # make the beginning of basic blocks a trace
            pc = bb.start if bb.start > base else base + bb.start
            traces.append(pc)
            for ins in bb:
                # this loop is for marking in the return addresses of function calls
                ins_array, size = ins
                pc += size
                if ins_array[0].text == 'call':
                    traces.append(pc)

def is_executable(mapping):
    umask = "".join(mapping.split("_")[2:4])
    return "x" in umask

def mark_all_traces():
    for mapping in listdir(memory_directory_path):
        if is_executable(mapping):
            mark_traces_in_mapping(mapping)

def write_all_traces_to_file():
    workspace = "/".join(memory_directory_path.split("/")[:-2])
    print("workspace: {}".format(workspace))
    with open(workspace + "/trace_list","a+") as trace_file:
        trace_file.write("======TRACE=ADDRESSES======\n")
        for trace in traces:
            trace_file.write(hex(trace).strip("L") + '\n')

if __name__  == "__main__":
    mark_all_traces()
    write_all_traces_to_file()
