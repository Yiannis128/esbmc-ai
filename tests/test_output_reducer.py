import re
import sys
import nltk
import unittest
from nltk.tokenize import word_tokenize,sent_tokenize
print(sys.path)

from esbmc_ai import esbmc_util
nltk.download('punkt')

class TestEsbmcOutputOptimisation(unittest.TestCase):
    
    def test_esbmc_output_optimisation(self):
      self.maxDiff = None
      input = '''Starting with the source code, we see that it includes some external functions and declares global variables. These variables are of type int and are initialized with non-deterministic values using the `__VERIFIER_nondet_int()` function. The `assume()` function is then used to specify assumptions about the values of these variables

Now let's look at the output from ESBMC. It starts with information about the version of ESBMC being used. Then it mentions the target platform and the C file being parsed. It indicates that the program is being converted into a GOTO program, which is the intermediate representation used by ESBMC for verification. The GOTO program creation time and processing time are also mentioned.

ESBMC then provides details about the symex (symbolic execution) process, including the time taken and the number of assignments. It mentions that slicing was performed, removing some assignments.

After that, it mentions the number of verification condition checks (VCCs) generated and the number remaining after simplification. These VCCs represent the conditions that need to be checked for the program to be considered correct.
1a2b3c4d 5e6f7a8b 9c0d1e2f 3a4b5c6d
Line 123: ESBMC is using the Boolector solver 1.2.3 to solve the encoding.
This is the result, which takes 1.34s.
ESBMC then mentions the solver being used, which is Boolector in this case. It indicates the time taken for encoding the VCCs and the time taken for solving using the specified solver.
Overall, the output from ESBMC shows the analysis process, including parsing, conversion, verification condition generation, encoding, solving, and bug trace generation.
Finally, it mentions the runtime decision procedure and the overall time taken for the BMC (Bounded Model Checking) program.
In this case, ESBMC reports "VERIFICATION SUCCESSFUL" and mentions that a solution was found by the forward condition. This means that all states in the program are reachable.
Finally, ESBMC confirms that the verfication has been successful: "VERIFICATION SUCCESSFUL."'''
      
      input01 = '''1. The output mentions that no solver was specified, so ESBMC defaults to using the Boolector solver.
This output states that the solving process with the Boolector solver took a certain amount of time.
-----------------------------------------
var01 = 0 (00000000 00000000 00000000 00000000)
Line 1: ESBMC is using the Boolector solver 3.3.2 to solve the encoding.
Line 3: The solver takes 2.3s to determine the runtime decision procedure.
The time it took the Boolector solve was 3.24s
- `Slicing time: 2.3s (removed 3 assignments\)`: ESBMC has performed slicing, a technique that removes irrelevant assignments from the program and reduces the complexity of analysis.
'''

      input02 = '''Now let's look at the output from ESBMC. It starts with information about the version of ESBMC being used.
virtual_table::std::ios@tag-std::iostream = { .~ios=&~ios }
foo = ( Foo *)(*dynamic_2_value)
The decision procedure involves executing various branches of the program symbolically and making decisions based on constraints and conditions.
Let's go through the source code and the output of ESBMC to understand what is happening.'''
      
      expected_output = '''Starting with the source code, we see that it includes some external functions and declares global variables. These variables are of type int and are initialized with nondeterministic values using the `__VERIFIER_nondet_int()` function. The `assume()` function is then used to specify assumptions about the values of these variables

After that, it mentions the number of verification condition checks (VCCs) generated and the number remaining after simplification.
This is the result
In this case, ESBMC reports "VERIFICATION SUCCESSFUL" and mentions that a solution was found by the forward condition. This means that all states in the program are reachable.
Finally, ESBMC indicates a successful verification.'''

      expected_output01 ='''
var01 = 0 


'''

      expected_output02 ='''Now let's look at the ESBMC output. It starts with information about the version of ESBMC being used.



'''


      output_str = esbmc_util.esbmc_output_optimisation(input)
      #print("The output is: ")
      #print(output_str)
      #print(expected_output)

      self.assertEqual(output_str, expected_output)
      output_str1 = esbmc_util.esbmc_output_optimisation(input01)
      self.assertEqual(output_str1, expected_output01)
      output_str2 = esbmc_util.esbmc_output_optimisation(input02)
      self.assertEqual(output_str2, expected_output02)


    def test_reduce_output2(self):
        input2 = '''These messages relate how ESBMC handles loops.
After 4 iterations, ESBMC found some bugs into the code.    
the output of the Efficient SMT-Based Context-Bounded Model Checker (ESBMC) goes through some verifications and iterates 5 times to find a bug.
Multiple threads (`thread1`, `thread2`, `thread3`) perform operations on a shared variable `data`
The output contains various debug and diagnostic messages, which are not relevant to understanding the vulnerabilities in the code     
The ESBMC will go thorugh some initial verifications before moving forward
Following this, it moves on to parsing the source file of the elevator system, which generally means it starts to interpret and prepare the program for model checking.
1. **Parsing and Conversion**: ESBMC starts by parsing the given C file and converting it into an internal representation. 
2. **GOTO Program Creation**: The tool generates a GOTO program. GOTO programs abstract away complex control flow to simplify the analysis. This step took approximately 0.343 seconds, with post-processing taking an additional 0.028 seconds.
3. **Bounded Model Checking (BMC)**: BMC involves checking the truth of properties up to a certain bound. Here, `k = 1` indicates that the checking is performed up to depth 1. Initially, ESBMC is checking the base case to ensure no bugs are present.
#Parsing and Compilation Warnings:
'''        

        input3 = '''3. **Bounded Model Checking (BMC)**: BMC involves checking the truth of properties up to a certain bound. Here, `k = 1` indicates that the checking is performed up to depth 1. Initially, ESBMC is checking the base case to ensure no bugs are present.
4. **Symex and Slicing**: Symbolic execution (Symex) is completed, and slicing removes irrelevant parts of the program to reduce complexity. For the base case, this reduced the assignments significantly.
5. **Verification Conditions (VCCs) Generation**: ESBMC generates VCCs, which are conditions that need to be satisfied to prove the correctness of the program. In the base case, only 1 VCC remains after simplification.
- **Warnings**: Several warnings are issued about the use of `printf` functions with non-literal format strings. This potentially insecure usage suggests replacing direct format specifiers with explicit string arguments to enhance security.
These messages relate how ESBMC handles loops.
6. **Solving**: ESBMC uses the Boolector solver to solve the generated conditions. The decision procedure's runtime and overall BMC program time are noted.
7. **Success in the Base Case**: ESBMC finds no bugs in the base case and proceeds to check the forward condition to ensure all states (up to `k = 1`) are reachable.
2. **Parsing**: ESBMC starts by parsing the provided C file (the file path indicates the file in question), preparing it for the model checking process.
- **"No bug has been found in the base case"**: Initially, ESBMC didn't find any errors under the base case scenario. This means that, at the starting point, without progressing further (`k = 1`), the program doesn't violate any of its assertions or fail to meet its specified conditions.
The BMC process starts again, and ESBMC reports that it was able to symbolically execute the program in 0.027 seconds.'''

        input4 = '''8. **Verification Successful**: The verification is successful, with the forward condition indicating that all states are reachable within the given bounds.
In this case, it initially starts with a simple base case, where k=1.
ESBMC displays various aspects for the code, such as the decision procedure used (`ESBMC-boolector`) and the number of switch points encountered during the analysis.
These details are not directly related to understanding the vulnerabilities in the code.
exit condition (`break`, `return`, or something else)
ESBMC starts with a base case for the program, revealing the tool's version for this context
The output from ESBMC (the Efficient SMT-based Context-Bounded Model Checker) pertaining to this code indicates a verification process:
- **"ESBMC version 7.5.0"**: The version of ESBMC used for verification is 7.5.0, denoting the tool's specific features and capabilities inherent to this version.
### Conclusion
- **"Solution found by the forward condition; all states are reachable (k = 1)"**: ESBMC concluded that, under the given conditions, every state it could consider within one step is reachable without uncovering any logical inconsistencies or errors. This suggests that the system modeled by the program, under the constraints and assertions defined, behaves as expected without leading to any undesired or erroneous states within the bounded context.'''

        expected_output2='''the output of ESBMC goes through some verifications and iterates 5 times to find a bug.
Multiple threads perform operations on a shared variable `data`
The ESBMC will go thorugh some initial verifications
2. **GOTO Program Creation**: The tool generates a GOTO program. GOTO programs abstract away complex control flow to simplify the analysis. This step took approximately 0.343 seconds, with post-processing taking an additional 0.028 seconds.
3. **Bounded Model Checking (BMC)**: BMC involves checking the truth of properties up to a certain bound. Here, `k = 1` indicates that the checking is performed up to depth 1. Initially, ESBMC is checking the base case to ensure no bugs are present.
'''
        expected_output3 ='''3. **Bounded Model Checking (BMC)**: BMC involves checking the truth of properties up to a certain bound. Here, `k = 1` indicates that the checking is performed up to depth 1. Initially, ESBMC is checking the base case to ensure no bugs are present.
5. **Verification Conditions (VCCs) Generation**: ESBMC generates VCCs, which are conditions that need to be satisfied to prove the correctness of the program. In the base case, only 1 VCC remains after simplification.
6. **Solving**: ESBMC uses the Boolector solver to solve the generated conditions. The decision procedure's runtime and overall BMC program time are noted.
7. **Success in the Base Case**: ESBMC finds no bugs in the base case and proceeds to check the forward condition to ensure all states (up to `k = 1`) are reachable.
- **"No bug has been found in the base case"**'''

        expected_output4 ='''8. **Verification Successful**: The verification is successful, with the forward condition indicating that all states are reachable within the given bounds.
It starts with a simple base case, where k=1.
exit condition (like `break` or `return`)
ESBMC starts with a base case for the program.
The output from ESBMC pertaining to this code indicates a verification process:
- **"ESBMC version 7.5.0"**
- **"Solution found by the forward condition; all states are reachable (k = 1)"**: ESBMC concluded that, under the given conditions, every state it could consider within one step is reachable without uncovering any logical inconsistencies or errors.'''
        self.maxDiff = None
        output_str2 = esbmc_util.reduce_output2(input2)

        #print('Filtered output2:')
        #print(output_str2)
        #print('Expected output2: ')
        self.assertEqual(output_str2, expected_output2)
        output_str3 = esbmc_util.reduce_output2(input3)
        self.assertEqual(output_str3, expected_output3)
        #print('Filtered output 3')
        #print(output_str3)
        #print('Expected output3:')
        #print(expected_output3)
        output_str4 = esbmc_util.reduce_output2(input4) 
        self.assertEqual(output_str4, expected_output4)     
        #print('Filtered output 4')
        #print(output_str4)
     #   print('Expected output4:')
      #  print(expected_output4)

    def test_remove_patterns_nltk(self):

        input5 = '''Runtime decision procedure:1.223s This part should remain.
BMC program time:2.332s
Multiple threads (`thread1`, `thread2`, `thread3`) perform operations on a shared variable `data`
- **Warnings**: Several warnings are issued about the use of `printf` functions with non-literal format strings.
A series of wanings are issued
### In Conclusion ###
The ESBMC output is shrinked.'''
        expected_output =''' This part should remain.
Multiple threads perform operations on a shared variable `data`
The ESBMC output is shrinked.''' 

        output = esbmc_util.remove_patterns_nltk(input5)
        self.assertEqual(output, expected_output)
       # print('\n'+output)
       # print(expected_output)

if __name__ == '__main__':
    unittest.main()
print(sys.path)
