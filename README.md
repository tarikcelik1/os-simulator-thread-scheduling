# CPU/OS Simulator with Multithreading

## Overview

This project is a comprehensive CPU and Operating System simulator that demonstrates cooperative multitasking and thread management. The simulator includes a custom instruction set architecture (ISA), a round-robin scheduler, system call handling, and multiple user threads that perform various computational tasks.

## Project Structure

- `cpu_sim.py` - Main CPU simulator implementation in Python
- `os_threads.gtu` - Assembly program with OS kernel and 10 user threads

## System Architecture

### CPU Simulator Features

The CPU simulator (`cpu_sim.py`) implements:

- **Harvard Architecture**: Separate instruction and data memory
- **Memory Management**: 20,000 word memory space with memory protection
- **Privilege Levels**: Kernel mode (addresses 0-999) and user mode (addresses 1000+)
- **Thread Management**: Support for up to 10 concurrent user threads
- **System Calls**: PRN (print), YIELD (cooperative scheduling), HLT (halt)
- **Debug Modes**: Memory dumps, step-by-step execution, thread table inspection

### Instruction Set Architecture (ISA)

The simulator supports the following instructions:

#### Data Movement
- `SET B A` - Set memory location A to value B
- `CPY A1 A2` - Copy content from A1 to A2
- `CPYI A1 A2` - Indirect copy using A1 as pointer
- `CPYI2 A1 A2` - Double indirect copy

#### Arithmetic
- `ADD A B` - Add immediate value B to memory location A
- `ADDI A1 A2` - Add memory A2 to memory A1
- `SUBI A1 A2` - Subtract A2 from A1, store in A2

#### Control Flow
- `JIF A C` - Jump to C if memory A ≤ 0
- `CALL C` - Call subroutine at address C
- `RET` - Return from subroutine

#### Stack Operations
- `PUSH A` - Push memory A onto stack
- `POP A` - Pop stack value into memory A

#### System Operations
- `USER A` - Switch to user mode and jump to address at A
- `SYSCALL PRN A` - Print value at memory A
- `SYSCALL YIELD` - Yield CPU to scheduler
- `SYSCALL HLT` - Terminate current thread
- `HLT` - Halt CPU

## Operating System Features

### Thread Management
- **Thread Table**: Located at memory addresses 30-136
- **Thread States**: READY (1), RUNNING (2), BLOCKED (3), TERMINATED (4)
- **Context Switching**: Automatic save/restore of PC, SP, and CPU usage
- **Round-Robin Scheduling**: Fair time allocation among threads

### System Call Handler
- **PRN System Call**: Blocks thread for 100 instruction cycles
- **YIELD System Call**: Voluntary CPU surrender
- **HLT System Call**: Clean thread termination

## User Threads

The simulator runs 10 user threads simultaneously:

### Thread 1: Selection Sort
- Sorts an array of 13 integers using selection sort algorithm
- Demonstrates array manipulation and nested loops
- Uses cooperative yielding during sorting

### Thread 2: Linear Search
- Searches for a key value (71) in an array of 10 integers
- Implements indirect addressing for parameters
- Reports search results with position information

### Thread 3: Factorial Calculator
- Calculates factorial of 15 using repeated addition
- Demonstrates multiplication without MUL instruction
- Shows iterative algorithm implementation

### Thread 4: Message Display
- Displays a series of Turkish greeting messages
- Demonstrates string handling and sequential output
- Shows basic thread communication through print

### Thread 5: Square Numbers
- Generates and displays square numbers using incremental method
- Calculates squares without multiplication (1, 4, 9, 16, ...)
- Uses efficient difference-based algorithm

### Threads 6-10: Basic Threads
- Simple threads that display identification messages
- Demonstrate basic thread creation and execution
- Show thread lifecycle management

## How to Run

### Prerequisites
- Python 3.7 or higher
- Basic understanding of assembly language concepts

### Execution
```bash
python cpu_sim.py os_threads.gtu
```

### Debug Options
```bash
python cpu_sim.py os_threads.gtu -D 1    # Memory dump after each instruction
python cpu_sim.py os_threads.gtu -D 2    # Step-by-step execution
python cpu_sim.py os_threads.gtu -D 3    # Thread table inspection
```

## Key Implementation Details

### Memory Layout
- **0-3**: CPU registers (PC, SP, syscall_result, instr_count)
- **4-29**: OS workspace and temporary registers
- **30-136**: Thread descriptor table (10 threads × 10 words each)
- **150-300**: OS global variables and constants
- **380-499**: System call handler code
- **500+**: OS shutdown routine
- **1000+**: User thread code and data

### Thread Descriptor Format
Each thread uses 10 memory words:
1. Thread ID
2. Thread State
3. Program Counter
4. Stack Pointer
5. Starting PC
6. Print Syscall PC
7. CPU Usage Counter
8-10. Reserved for future use

### Scheduling Algorithm
1. Check for terminated threads and skip them
2. Check for blocked threads and their unblock conditions
3. Find next ready thread in round-robin order
4. Perform context switch (save current, load next)
5. Update thread states and counters

## Expected Output

The simulator will display:
- Thread identification messages
- Sorting process and results from Thread 1
- Search results from Thread 2
- Factorial calculation from Thread 3
- Personal messages from Thread 4
- Square numbers from Thread 5
- Basic messages from Threads 6-10
- Final memory dump showing system state

## Educational Value

This project demonstrates:
- **Operating System Concepts**: Process scheduling, context switching, system calls
- **Assembly Programming**: Low-level instruction execution and memory management
- **Concurrent Programming**: Multiple threads sharing CPU resources
- **Algorithm Implementation**: Sorting, searching, and mathematical computations
- **System Architecture**: CPU design, memory organization, and privilege levels

## Technical Notes

- The simulator uses cooperative multitasking (threads must yield voluntarily)
- Memory protection prevents user threads from accessing kernel space
- System calls provide controlled access to OS services
- Round-robin scheduling ensures fair CPU allocation
- Thread blocking/unblocking simulates I/O operations

## Author

Tarık Çelik 
GTU Computer Engineering - Operating Systems Course Project
