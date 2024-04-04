b'ESBMC version 7.4.0 64-bit x86_64 linux
Target: 64-bit little-endian x86_64-unknown-linux with esbmclibc
Parsing patched-src-2/reinforcement_learning/cartpole_92_safe.c-amalgamation-14.c
Converting
Generating GOTO Program
GOTO program creation time: 1.287s
GOTO program processing time: 0.040s
Checking base case, k = 1
Starting Bounded Model Checking
Not unwinding loop 26 iteration 1   file cartpole_92_safe.c-amalgamation-14.c line 244 column 4 function node_Gemm_1
Symex completed in: 0.134s (79 assignments)
Slicing time: 0.000s (removed 69 assignments)
Generated 29 VCC(s), 1 remaining after simplification (10 assignments)
No solver specified; defaulting to Boolector
Encoding remaining VCC(s) using bit-vector/floating-point arithmetic
Encoding to solver time: 0.001s
Solving with solver Boolector 3.2.2
Runtime decision procedure: 0.045s
Building error trace

[Counterexample]


State 1 file cartpole_92_safe.c-amalgamation-14.c line 19 column 23 function main thread 0
----------------------------------------------------
  tensor_input[0][0] = -2.636719e-1f (10111110 10000111 00000000 00000000)

State 2 file cartpole_92_safe.c-amalgamation-14.c line 20 column 23 function main thread 0
----------------------------------------------------
  tensor_input[0][1] = -6.330566e-1f (10111111 00100010 00010000 00000000)

State 3 file cartpole_92_safe.c-amalgamation-14.c line 21 column 23 function main thread 0
----------------------------------------------------
  tensor_input[0][2] = -3.186417e-2f (10111101 00000010 10000100 00000001)

State 4 file cartpole_92_safe.c-amalgamation-14.c line 22 column 23 function main thread 0
----------------------------------------------------
  tensor_input[0][3] = 5.310059e-1f (00111111 00000111 11110000 00000000)

State 9 file cartpole_92_safe.c-amalgamation-14.c line 221 column 3 function node_Flatten_0 thread 0
----------------------------------------------------
Violated property:
  file cartpole_92_safe.c-amalgamation-14.c line 221 column 3 function node_Flatten_0
  dereference failure: array bounds violated


VERIFICATION FAILED

Bug found (k = 1)
'