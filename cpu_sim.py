import sys  # Standard library: used here mainly for stderr output
import argparse  # Parses command‑line arguments when running the simulator as a script

# ---------------------------------------------------------------------------------
# GLOBAL CONSTANTS (visible both inside and outside the CPU class)
# ---------------------------------------------------------------------------------
MEM_SIZE = 20000  # Size of simulated memory array (words)


class CPU:
    """A simple cooperative‑multitasking CPU/OS simulator.

    The simulator models a Harvard‑style machine with a single, flat memory
    (word‑addressable) and a tiny instruction set that is extended in Python.
    The *operating system* lives at the lowest addresses (0‑29) while the
    *thread table* occupies the region starting at THREAD_TABLE_BASE.  The rest
    is available to user programs.
    """

    # -------------------------------------------------------------------------
    # Architectural / OS layout constants
    # -------------------------------------------------------------------------
    MEM_SIZE           = 20000  # duplicate of global MEM_SIZE for convenience
    THREAD_TABLE_BASE  = 30     # first word of the thread‑descriptor table
    THREAD_SLOT_SIZE   = 10     # how many words each descriptor occupies
    MAX_THREADS        = 10     # maximum number of user threads the OS supports

    # -------------------------------------------------------------------------
    # ─── INITIALISATION ──────────────────────────────────────────────────────
    # -------------------------------------------------------------------------
    def __init__(self, program: tuple[list, dict], debug: int = 0):
        """Create a CPU instance and preload it with a program image.

        *program* is a pair *(mem, instructions)* produced by :func:`load_gtu`.
        The first element is a *list* containing 20 000 memory words; the second
        is a *dict* that maps addresses to decoded instructions (opcode + args).
        """

        # Unpack the program image provided by the loader
        self.mem, self.instructions = program

        # Registers are memory‑mapped in the lowest addresses (0‑3) so copy them
        # into Python attributes for quicker access.  They will be written back
        # to memory whenever they change so that the *real* state always lives
        # in the simulated RAM.
        self.pc             = self.mem[0]  # Program Counter
        self.sp             = self.mem[1]  # Stack Pointer (grows downwards)
        self.syscall_result = self.mem[2]  # Result / return code of last syscall
        self.instr_count    = self.mem[3]  # Number of executed instructions

        # Book‑keeping flags
        self.mode    = 'kernel'  # 'kernel' while executing OS code, 'user' otherwise
        self.halted  = False     # Set to True to stop :meth:`run`
        self.debug   = debug     # 0 = off, 1 = mem dump, 2 = step mode, 3 = thread table
        self.current_tid = 0     # Currently running thread ID (0 = kernel)

    # ---------------------------------------------------------------------
    # PROGRAM LOADING (allows overlays / self‑modifying systems if needed)
    # ---------------------------------------------------------------------
    def load_program(self, program):
        """Overlay *program* (data + instructions) on top of current memory."""
        data_section, instr_section = program

        # Load data words directly into memory
        for addr, val in data_section:
            self.mem[addr] = val

        # Split each textual instruction into its tokens and store them
        for addr, inst in instr_section:
            parts = inst.split()
            self.instructions[addr] = parts

    # ---------------------------------------------------------------------
    # MAIN EXECUTION LOOP
    # ---------------------------------------------------------------------
    def run(self):
        """Run instructions until :attr:`halted` becomes True."""
        while not self.halted:
            self.execute_instruction()  # fetch → decode → execute one instruction

            # --- Debugging --------------------------------------------------
            if self.debug == 1:
                self.print_memory()     # dump every cycle
            elif self.debug == 2:
                self.print_memory()
                input("Press ENTER to step")
        # After CPU halts output final memory dump if no other debug requested
        if self.debug == 0:
            self.print_memory()

    # ---------------------------------------------------------------------
    # DEBUG / INSPECTION UTILITIES
    # ---------------------------------------------------------------------
    def print_memory(self):
        """Print every non‑zero memory location to *stderr*."""
        for i, v in enumerate(self.mem):
            if v != 0:
                print(f"{i}: {v}", file=sys.stderr)

    def print_thread_table(self):
        """Pretty‑print the fixed‑size thread‑descriptor table (addresses 30‑136)."""
        headers = ["ID", "STATE", "PC", "SP", "STARTING TIME", "PRN SYSCALL", "CPU/INST"]
        col_width = 15  # monospace column width for readability

        # Header row ▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬
        header_line = " | ".join(f"{h:>{col_width}}" for h in headers)
        sep_line    = "-+-".join("-" * col_width for _ in headers)

        print("\nThread Table:", file=sys.stderr)
        print(header_line, file=sys.stderr)
        print(sep_line, file=sys.stderr)

        # Data rows ▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬
        for i in range(30, 136, 10):  # iterate over the 10‑word slots
            row_vals = [self.mem[j] for j in range(i, i + 7)]  # only first 7 shown
            row_line = " | ".join(f"{v:>{col_width}d}" for v in row_vals)
            print(row_line, file=sys.stderr)

    # ---------------------------------------------------------------------
    # ─── INSTRUCTION EXECUTION ────────────────────────────────────────────
    # ---------------------------------------------------------------------
    def execute_instruction(self):
        """Fetch, decode and execute a single instruction."""
        # Synchronise register shadow → memory mapping before fetch
        self.pc = self.mem[0]

        # Default opcode is HLT if the address has no instruction (defensive)
        raw = self.instructions.get(self.mem[0], ["HLT"])
        op  = raw[0]  # first token is the opcode string
        # -----------------------------------------------------------------
        # SPECIAL‑CASE: SYSTEM CALLS (software traps into kernel mode)
        # -----------------------------------------------------------------
        if op == "SYSCALL":
            self.mode = 'kernel'
            kind = raw[1]
            addr = int(raw[2]) if len(raw) > 2 else None
            self.op_SYSCALL(kind, addr)
            self.instr_count += 1
            self.mem[3] = self.instr_count  # keep shadow register in sync
            if self.debug == 3:
                self.print_thread_table()
            return  # SYSCALL does its own PC management

        # -----------------------------------------------------------------
        # NORMAL ARITHMETIC / CONTROL INSTRUCTIONS
        # -----------------------------------------------------------------
        args = list(map(int, raw[1:]))  # convert remaining tokens to int
        method = getattr(self, f'op_{op}')  # dynamic dispatch to op_* handler
        method(*args)  # execute

        # Auto‑increment PC *except* for special control‑flow ops handled inside
        if op not in ("CALL", "RET", "JIF"):
            self.mem[0] += 1
            self.pc     += 1

        # Update global instruction counter
        self.instr_count += 1
        self.mem[3] = self.instr_count

    # ---------------------------------------------------------------------
    # ─── MEMORY‑ACCESS CONTROL ───────────────────────────────────────
    # ---------------------------------------------------------------------
    def check_memory_access(self, addr: int, operation: str) -> bool:
        """Verify that *addr* is legal for the current privilege level.

        Kernel code is allowed to touch the entire address space.  User mode is
        restricted to addresses ≥ 1000 (the OS and thread table are read‑only
        for it).  If a violation occurs the CPU simulates a fault by jumping to
        a fixed handler and returns *False* so that the calling op can abort.
        """
        if self.mode == 'user' and 21 <= addr <= 999:
            print(f"ACCESS VIOLATION: User mode cannot {operation} address {addr}", file=sys.stderr)
            # Simulate a kernel trap to terminate the offending thread
            self.mem[2] = 1   # syscall_result set to HLT
            self.mem[0] = 380 # address of the fault handler
            self.pc     = 380
            self.mode   = 'kernel'  # switch to kernel mode
            return False
        return True

    # ---------------------------------------------------------------------
    # ─── INSTRUCTION HANDLERS (op_*) ──────────────────────────────────────
    # ---------------------------------------------------------------------
    # NOTE: All handlers *must* keep memory + register shadows consistent.

    def op_SET(self, B, A):  # SET <value>, <addr>
        if not self.check_memory_access(A, "write"):
            return
        self.mem[A] = B
        if A == 0:  # writing to MEM[0] = jump
            self.pc = B

    def op_CPY(self, A1, A2):  # CPY <src>, <dst>
        if not self.check_memory_access(A1, "read"):
            return
        if not self.check_memory_access(A2, "write"):
            return
        self.mem[A2] = self.mem[A1]

    def op_CPYI(self, A1, A2):  # CPYI <srcPtr>, <dst>
        if not self.check_memory_access(A1, "read"):
            return
        addr = self.mem[A1]  # indirect through first operand
        if not self.check_memory_access(addr, "read"):
            return
        if not self.check_memory_access(A2, "write"):
            return
        self.mem[A2] = self.mem[addr]

    # Arithmetic ▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬
    def op_ADD(self, A, B):  # ADD <addr>, <imm>
        if not self.check_memory_access(A, "read/write"):
            return
        self.mem[A] += B

    def op_ADDI(self, A1, A2):  # ADDI <dst>, <src>
        if not self.check_memory_access(A1, "read/write"):
            return
        if not self.check_memory_access(A2, "read"):
            return
        self.mem[A1] += self.mem[A2]

    def op_SUBI(self, A1, A2):  # SUBI <src>, <dst>
        if not self.check_memory_access(A1, "read"):
            return
        if not self.check_memory_access(A2, "read/write"):
            return
        self.mem[A2] = self.mem[A1] - self.mem[A2]

    # Control flow ▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬
    def op_JIF(self, A, C):  # JIF <condAddr>, <target>
        if not self.check_memory_access(A, "read"):
            return
        if self.mem[A] <= 0:
            self.mem[0] = C
            self.pc     = C
        else:
            self.mem[0] += 1
            self.pc     += 1

    # Stack ops ▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬
    def op_PUSH(self, A):
        if not self.check_memory_access(A, "read"):
            return
        self.sp -= 1  # pre‑decrement (stack grows down)
        if not self.check_memory_access(self.sp, "write"):
            return
        self.mem[self.sp] = A
        self.mem[1] = self.sp  # keep shadow

    def op_POP(self, A):
        if not self.check_memory_access(self.sp, "read"):
            return
        if not self.check_memory_access(A, "write"):
            return
        val = self.mem[self.sp]
        self.mem[A] = val
        self.sp += 1  # post‑increment
        self.mem[1] = self.sp

    # Double‑indirect copy (rarely used but handy for fast context switches)
    def op_CPYI2(self, A1, A2):
        if not self.check_memory_access(A1, "read"):
            return
        if not self.check_memory_access(A2, "read"):
            return
        if not self.check_memory_access(self.mem[A2], "write"):
            return
        if not self.check_memory_access(self.mem[A1], "read"):
            return
        # Example: A1=100, A2=120, MEM[100]=200, MEM[120]=300 → MEM[300]=MEM[200]
        self.mem[self.mem[A2]] = self.mem[self.mem[A1]]

        # Special hack: if destination is MEM[0] treat as a jump (makes CPYI2
        # usable for tail‑call style jumps in threaded code)
        if self.mem[A2] == 0:
            self.pc     = self.mem[self.mem[A1]] - 1  # −1 because main loop +1
            self.mem[0] = self.pc

    # -----------------------------------------------------------------
    # CALL/RET emulate a conventional subroutine mechanism using the stack
    # -----------------------------------------------------------------
    def op_CALL(self, C):
        # Push return address on stack then jump to C
        self.sp -= 1
        self.mem[self.sp] = self.pc + 1
        self.mem[1] = self.sp
        self.mem[0] = C
        self.pc     = C

    def op_RET(self):
        ret = self.mem[self.sp]  # pop return address
        self.sp += 1
        self.mem[1] = self.sp
        self.mem[0] = ret
        self.pc     = ret

    # -----------------------------------------------------------------
    # HALT handling: distinguishes between kernel halt and thread exit
    # -----------------------------------------------------------------
    def op_HLT(self):
        if self.current_tid == 0:  # OS halted → stop whole simulator
            self.halted = True
            print("OPERATING SYSTEM HAS HALTED THE CPU.", file=sys.stderr)
        else:  # user thread halted → return to scheduler
            self.mem[2] = 1  # signal exit to kernel

    # -----------------------------------------------------------------
    # PRIVILEGE LEVEL MANAGEMENT
    # -----------------------------------------------------------------
    def op_USER(self, A):
        """Switch to user mode and jump to *MEM[A]* (entry point)."""
        self.mode   = 'user'
        self.mem[0] = self.mem[A]
        self.pc     = self.mem[A]

    # -----------------------------------------------------------------
    # SYSTEM CALL (software interrupt) DISPATCHER
    # -----------------------------------------------------------------
    def op_SYSCALL(self, kind, A=None):
        """Handle software interrupts raised by user code."""
        self.mode = 'kernel'  # always switch to kernel mode first

        if kind == 'PRN':  # print syscall
            print(self.mem[A])  # simple console print to host stdout
            self.mem[2] = 2     # result code 2 = success (printf)
            self.mem[18] = self.mem[0] + 1  # save return PC
            self.mem[0] = 380   # enter common syscall handler stub

        elif kind == 'YIELD':  # cooperative yield to scheduler
            self.mem[2] = 0
            self.mem[18] = self.mem[0] + 1
            self.mem[0] = 380

        elif kind == 'HLT':  # terminate thread (clean exit)
            self.mem[2] = 1
            self.mem[18] = self.mem[0]  # PC already at HLT
            self.mem[0] = 380


# =============================================================================
# ─── ASSEMBLY LOADER ─────────────────────────────────────────────────────────
# =============================================================================

def load_gtu(path: str) -> tuple[list, dict[int, tuple]]:
    """Read *path* (a .gtu assembly source) and return *(mem, instr)* image.

    The loader understands two labelled sections:
      * `BEGIN DATA` / `END DATA` – initialise memory words
      * `BEGIN INSTRUCTION` / `END INSTRUCTION` – machine code listing

    Lines may contain `#` or `;` comments which are stripped.  String literals
    in the data section are loaded verbatim (useful for the PRN syscall).
    """
    with open(path, encoding='utf-8', errors='replace') as f:
        lines = f.readlines()

    mem   = [0] * MEM_SIZE             # pre‑zeroed memory image
    instr: dict[int, tuple] = {}       # address → (opcode, *args)
    in_data = False
    in_code = False

    for raw in lines:
        # Remove comments (anything after # or ;) then trim whitespace
        line = raw.split('#', 1)[0].split(';', 1)[0].strip()
        if not line:
            continue  # skip blank / comment‑only lines

        lw = line.lower()
        if lw.startswith('begin data'):
            in_data, in_code = True, False
            continue
        if lw.startswith('end data'):
            in_data = False
            continue
        if lw.startswith('begin instruction'):
            in_data, in_code = False, True
            continue
        if lw.startswith('end instruction'):
            in_code = False
            continue

        tokens = line.split()
        if in_data:
            base = int(tokens[0])
            if len(tokens) > 1 and tokens[1].startswith('"'):
                # String literal (may contain spaces, hence join + strip quotes)
                string_value = ' '.join(tokens[1:]).strip('"')
                mem[base] = string_value
            else:
                # One or more integer words on the same line
                for offset, val in enumerate(tokens[1:]):
                    try:
                        mem[base + offset] = int(val)
                    except ValueError:
                        print(f"Warning: couldn't convert '{val}' at {base+offset}")
        elif in_code:
            if len(tokens) < 2:
                continue  # malformed line; ignore
            addr   = int(tokens[0])
            opcode = tokens[1].upper()
            args   = tuple(tokens[2:])
            instr[addr] = (opcode, *args)

    return mem, instr


# =============================================================================
# ─── COMMAND‑LINE INTERFACE ──────────────────────────────────────────────────
# =============================================================================
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('program', help='Assembly file path')
    parser.add_argument('-D', type=int, default=0, help='Debug mode')
    args = parser.parse_args()

    # Load program *once* and feed it directly to the CPU constructor
    program = load_gtu(args.program)  # returns (mem, instr)
    cpu = CPU(program, debug=args.D)  # instantiate simulator
    cpu.run()                         # start execution
