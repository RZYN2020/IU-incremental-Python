# python-student-support-code

Support code for students (Python version).

The `runtime.c` file needs to be compiled by doing the following
```
   gcc -c -g -std=c99 runtime.c
```
This will produce a file named `runtime.o`. The -g flag is to tell the
compiler to produce debug information that you may need to use
the gdb (or lldb) debugger.

On a Mac with an M1 (ARM) processor, use the `-arch x86_64` flag to
compile the runtime:
```
   gcc -c -g -std=c99 -arch x86_64 runtime.c
```

# Prograss


2023.12.8 之前：完成了寄存器分配
2024.1.16 boolean and condition
if we add if else to lang, then the overall structure again become tree-like... so we need basic block to convert...
why need bb? what's the difference between expression tree -> all sub tree in expr tree are used, but if else tree not...
And resource allocation among bbs matters! because input state of a bb can varies... (what's the connect with turing complete?no, we don't have while! so the input state is finate!)


