# Author: Yiannis Charalambous

import os
import re
import sys
from subprocess import PIPE, STDOUT, run, CompletedProcess
from pathlib import Path
import esbmc_ai.config as config
from typing import Optional
from . import config
import nltk
from nltk.tokenize import word_tokenize,sent_tokenize
nltk.download('punkt')


def esbmc_get_violated_property(esbmc_output: str) -> Optional[str]:
    """Gets the violated property line of the ESBMC output."""
    # Find "Violated property:" string in ESBMC output
    lines: list[str] = esbmc_output.splitlines()
    for ix, line in enumerate(lines):
        if "Violated property:" == line:
            return "\n".join(lines[ix : ix + 3])
    return None


def esbmc_get_counter_example(esbmc_output: str) -> Optional[str]:
    """Gets ESBMC output after and including [Counterexample]"""
    idx: int = esbmc_output.find("[Counterexample]\n")
    if idx == -1:
        return None
    else:
        return esbmc_output[idx:]


def esbmc_get_error_type(esbmc_output: str) -> str:
    """Gets the error of violated property, the entire line."""
    # TODO Test me
    # Start search from the marker.
    marker: str = "Violated property:\n"
    violated_property_index: int = esbmc_output.rfind(marker) + len(marker)
    from_loc_error_msg: str = esbmc_output[violated_property_index:]
    # Find second new line which contains the location of the violated
    # property and that should point to the line with the type of error.
    # In this case, the type of error is the "scenario".
    scenario_index: int = from_loc_error_msg.find("\n")
    scenario: str = from_loc_error_msg[scenario_index + 1 :]
    scenario_end_l_index: int = scenario.find("\n")
    scenario = scenario[:scenario_end_l_index].strip()
    return scenario


def get_source_code_err_line(esbmc_output: str) -> Optional[int]:
    # Find "Violated property:" string in ESBMC output
    violated_property: Optional[str] = esbmc_get_violated_property(esbmc_output)
    if violated_property:
        # Get the line of the violated property.
        pos_line: str = violated_property.splitlines()[1]
        pos_line_split: list[str] = pos_line.split(" ")
        for ix, word in enumerate(pos_line_split):
            if word == "line":
                # Get the line number
                return int(pos_line_split[ix + 1])
    return None


def get_source_code_err_line_idx(esbmc_output: str) -> Optional[int]:
    line: Optional[int] = get_source_code_err_line(esbmc_output)
    if line:
        return line - 1
    else:
        return None


def esbmc(path: str, esbmc_params: list, timeout: Optional[float] = None):
    """Exit code will be 0 if verification successful, 1 if verification
    failed. And any other number for compilation error/general errors."""
    # Build parameters
    esbmc_cmd = [config.esbmc_path]
    esbmc_cmd.extend(esbmc_params)
    esbmc_cmd.append(path)

    if "--timeout" in esbmc_cmd:
        print(
            'Do not add --timeout to ESBMC parameters, instead specify it in "verifier_timeout".'
        )
        sys.exit(1)

    esbmc_cmd.extend(["--timeout", str(timeout)])

    # Add slack time to process to allow verifier to timeout and end gracefully.
    process_timeout: Optional[float] = timeout + 1 if timeout else None

    # Run ESBMC and get output
    process: CompletedProcess = run(
        esbmc_cmd,
        stdout=PIPE,
        stderr=STDOUT,
        timeout=process_timeout,
    )

    output = esbmc_output_optimisation(output)
    output = reduce_output2(output)
    output = remove_patterns_nltk(output)

    output: str = process.stdout.decode("utf-8")
    return process.returncode, output



def esbmc_output_optimisation(esbmc_output:str) -> str:
  
    esbmc_output =re.sub(r'(^\d+\.\s*)?The output mentions that no solver was specified, so ESBMC defaults to using the Boolector solver\.', '', esbmc_output, flags=re.MULTILINE)
    esbmc_output = re.sub(r'(^\d+\.\s*)?This output states that the solving process with the Boolector solver took a certain amount of time\.','', esbmc_output, flags=re.MULTILINE)  
    esbmc_output = re.sub(r'[-]+', '', esbmc_output)  # Remove lines of dashes
    
    esbmc_output = re.sub(r'\(*\b[0-9a-fA-F]{8} [0-9a-fA-F]{8} [0-9a-fA-F]{8} [0-9a-fA-F]{8}\b\)*', '', esbmc_output)  # Remove hex patterns
    esbmc_output = re.sub(r'^Line \d+: ESBMC is using the Boolector solver \d+\.\d+\.\d+ to solve the encoding\.$', '', esbmc_output, flags=re.MULTILINE)  # Remove Boolector lines
    esbmc_output = re.sub(r'\d+. ESBMC is using the Boolector solver \d+\. \d+\. \d+ to solve the encoding\.$', '', esbmc_output, flags=re.MULTILINE)
    
    esbmc_output = re.sub(r'^Line \d+: The solver takes \d+\.\d+s to determine the runtime decision procedure\.$', '', esbmc_output, flags=re.MULTILINE)  # Remove solver time lines
    esbmc_output = re.sub(r'.*Boolector.*\n\n', '', esbmc_output, flags=re.MULTILINE)
    pattern = r"- `.*Slicing time: \d+\.\d+s \(removed \d+ assignments\)`.*: ESBMC has performed slicing, a technique that removes irrelevant assignments from the program and reduces the complexity of analysis."
    esbmc_output = re.sub(pattern, '', esbmc_output, flags=re.MULTILINE)
    
    esbmc_output = re.sub(r'\n\s*\n', '\n', esbmc_output)
    esbmc_output = esbmc_output.replace("output from ESBMC", "ESBMC output")
    esbmc_output = re.sub(r'The time.*', '', esbmc_output, flags=re.MULTILINE) 
    
    esbmc_output = re.sub(r'[^.]VCCs represent.*|[^.]These VCCs represent.*', '', esbmc_output, flags=re.MULTILINE) #These types of lines represent some sequences of VCCs that can easily be ommitted for development purposes
    esbmc_output = re.sub(r'.*bitvector.*', '', esbmc_output, flags=re.MULTILINE)
    esbmc_output = re.sub(r'\s*\(\s*`thread\d+`(?:,\s*`thread\d+`)*\s*\)', '', esbmc_output)
    
    esbmc_output = re.sub(r'.*floating-point arithmetic.*', '', esbmc_output, flags=re.MULTILINE)
    esbmc_output = re.sub(r'.*encoding.*', '', esbmc_output, flags = re.MULTILINE)
    esbmc_output = re.sub(r'.*encoding time.*', '', esbmc_output, flags= re.MULTILINE)

    esbmc_output = re.sub(r', which takes \d+\.\d+s\.*', '.', esbmc_output, flags=re.MULTILINE)
    esbmc_output = re.sub(r'The output indicates that ESBMC generates a verification condition \(VCC\) for each possible path and encodes them into a solver\.', '', esbmc_output, flags= re.MULTILINE) #This information can be disregarded for development purposes
    esbmc_output = re.sub(r'Measures the [^.]+?encoding time [^.]+?\.', '', esbmc_output, flags=re.MULTILINE)

    esbmc_output = re.sub(r'In this case, the procedure took [0-9.]+ seconds\.', '', esbmc_output, flags=re.MULTILINE)
    esbmc_output = re.sub(r'\s*It measures[^.]+? encoding time [^.]+?\.', '', esbmc_output, flags=re.MULTILINE)
    esbmc_output = re.sub(r'[^.]*GOTO program[^.]*\.', '', esbmc_output)

    esbmc_output = re.sub(r'\d+\.\d+s \.', '', esbmc_output, flags=re.MULTILINE)
    esbmc_output = re.sub(r'\.\s*.*time.*\n\n|\.\s*[^.]*time[^.]*\.', '', esbmc_output, flags=re.MULTILINE)    
    esbmc_output =  re.sub(r'.*program time: \d+\.\d+s \.', '',esbmc_output, flags=re.MULTILINE)

    esbmc_output = re.sub(r'\.\s*[^.]*?BMC program time:\d+\.\d+s', '', esbmc_output, flags= re.MULTILINE)
    esbmc_output =re.sub(r'\.\s*[^.]*?Runtime decision procedure: \d+.\d+s\"*', '', esbmc_output, flags=re.MULTILINE)
    esbmc_output = re.sub(r'.*Symex.*|.*symex.*|.*symbolic execution.*\n\n', '', esbmc_output, flags=re.MULTILINE)

    esbmc_output =re.sub(r'After[^.]*?, the code', 'The program then', esbmc_output, flags=re.MULTILINE)
    esbmc_output = re.sub(r'.*assignments.*|.*assignment.*', '', esbmc_output, flags=re.MULTILINE)
    esbmc_output = re.sub(r'.*iteratively.*', '', esbmc_output, flags=re.MULTILINE)

    esbmc_output = re.sub(r'.*branches.*', '', esbmc_output, flags=re.MULTILINE) #The informations about branches are not necessary relevant to the understanding of bugs
    esbmc_output = re.sub(r'.*analysis process.*\s','', esbmc_output, flags=re.MULTILINE ) 
    esbmc_output = re.sub(r'.*remaining VCC.*\s|.*remaining VCCs.*\s','', esbmc_output)

    esbmc_output = re.sub(r'.*0 VCCs.*', '', esbmc_output, flags= re.MULTILINE) # If there are no more VCCs left, the user is not going to take action in this regard.
    esbmc_output = re.sub(r'Finally, ESBMC confirms that the verfication.*"VERIFICATION SUCCESSFUL."', 'Finally, ESBMC indicates a successful verification.', esbmc_output, flags=re.MULTILINE)
    esbmc_output = re.sub(r'Let\'s go through the source code and the output of ESBMC to understand what is happening.|Let\'s go through the code and explain the relevant parts along with the output from ESBMC.', '', esbmc_output, flags=re.MULTILINE)

    esbmc_output = re.sub(r'\.\s*.*"Symex completed in:.*".*\s', '', esbmc_output, flags=re.MULTILINE)
    esbmc_output = re.sub(r'.*These warnings are about.*', '', esbmc_output, flags=re.MULTILINE) #Warning information are not useful for debugging purposes
   
    esbmc_output = re.sub(r'Let\'s go through the source code and the output of ESBMC to understand what is happening.|Let\'s go through the code and explain the relevant parts along with the output from ESBMC.', '', esbmc_output, flags=re.MULTILINE)
    esbmc_output = re.sub(r'Let\'s[^.]the[^.]code and explain the relevant parts of the output from ESBMC.', '', esbmc_output, flags=re.MULTILINE)
    esbmc_output = re.sub(r'virtual_table::std::.*', '', esbmc_output, flags=re.MULTILINE)

    esbmc_output = re.sub(r'foo =.*', '', esbmc_output, flags=re.MULTILINE)
    esbmc_output = re.sub(r'the .*Efficient SMT-Based Context-Bounded Model Checker \(ESBMC\)', 'ESBMC', esbmc_output, flags=re.MULTILINE)
    esbmc_output = re.sub(r'(Efficient SMT-Based Bounded Model Checker)', '', esbmc_output, flags=re.MULTILINE)      
    

    return esbmc_output


def reduce_output2(esbmc_output: str) -> str:
    
    esbmc_output = re.sub(r'\.\s*[^.]*symbolically execute the program[^.]*\.', '', esbmc_output, flags=re.MULTILINE) #Reffers to a time measurement
    esbmc_output = re.sub('In this case, it initially starts with', 'It starts with', esbmc_output, flags= re.MULTILINE)
    esbmc_output = re.sub(r'(.*)\s*before moving forward', r'\1', esbmc_output, flags=re.MULTILINE) #removes the specified sequence, as it is trivial

    esbmc_output = re.sub(r'.*k=0.*', '', esbmc_output, flags=re.MULTILINE) # for k=0, which is the base case, there is no need for an explanation for development purposes, the user would not find this information helpful 
    esbmc_output = re.sub(r'the Efficient SMT-Based Context-Bounded Model Checker \(ESBMC\)', 'ESBMC', esbmc_output, flags=re.MULTILINE) 
    esbmc_output = re.sub(r', which stands for Efficient SMT-Based Countext-Bounded Model Checker', '.', esbmc_output, flags=re.MULTILINE )   

    esbmc_output = re.sub(r'.*Warnings.*|.*warnings.*', '', esbmc_output, flags=re.MULTILINE)
    esbmc_output = re.sub(r'.*\*\*Warnings\*\*.*', '', esbmc_output, flags=re.MULTILINE)
    esbmc_output = re.sub(r'.*warning.*', '', esbmc_output, flags=re.MULTILINE)     
       
    esbmc_output =  re.sub('.*A series of warnings.*', '', esbmc_output, flags=re.MULTILINE)
    esbmc_output = re.sub(r'ESBMC \(the Efficient SMT-based Context-Bounded Model Checker\)', 'ESBMC', esbmc_output, flags=re.MULTILINE)
    esbmc_output = re.sub(r'These messages relate how ESBMC handles loops.*\.|These messages relate.*\.', '', esbmc_output, flags=re.MULTILINE) #These type of lines can be ommitted, if there is anything relevant about loops, ESBMC-AI can display other more precise explanations

    esbmc_output = re.sub(r'which, in simple terms,', 'which', esbmc_output, flags=re.MULTILINE)
    esbmc_output = re.sub(r'After[^.]*iterations[^.]*\.', '', esbmc_output, flags=re.MULTILINE) #These types of line can be removed to make the output easier to read, without ommitting any important information   
    esbmc_output = re.sub(r'[^.]*iterations[^.]*\.', '.', esbmc_output, flags=re.MULTILINE)

    esbmc_output = re.sub(r'Initially, ESBMC parses the given source file. It identifies', 'ESBMC identifies', esbmc_output, flags=re.MULTILINE)
    esbmc_output = re.sub(r'\.\s*.*parsing the source file.*|\.\s*.parses the source file.*|\s*.*parsing the source file.*|\s*.*starts by parsing the program.*|\s*.*starts by parsing the.*', '', esbmc_output, flags=re.MULTILINE) # this is an additional information that ESBMC-AI provides, it is not useful for understanding the behaviour of the tested code
    esbmc_output = re.sub(r'\*\*Parsing and Compilation Warnings:\*\*', '', esbmc_output, flags=re.MULTILINE) #This represents a type of header in the output, which is followed by an explanatory paragraph, its removal doesn't affect the understandability of the parsing and warning explanations

    esbmc_output = re.sub(r'### Conclusion.*(?:\n{2,}|$)|### In Conclusion.*(?:\n{2,}|$)', '', esbmc_output, flags=re.MULTILINE)

    esbmc_output = re.sub(r'\*\*Conclusion:\*\*.*(?:\n{2,}|$)', '', esbmc_output, flags=re.MULTILINE)   
    esbmc_output = re.sub(", revealing the tool's version for this context", '.', esbmc_output, flags=re.MULTILINE)
    esbmc_output = re.sub(r'exit condition \(`break`, `return`,.*?\)', 'exit condition (like `break` or `return`)', esbmc_output, flags=re.MULTILINE) #keeps the message concise, displays only the relevant information 

    esbmc_output = re.sub(r'.*Slicing.*\.|.*slicing.*\.', '', esbmc_output, flags=re.MULTILINE) #Slicing information doesn't help for understanding bugs or approach them differently
    esbmc_output = re.sub(r'The output contains.*are not relevant.*\n', '', esbmc_output, flags=re.MULTILINE)
    esbmc_output = re.sub(r'such as the decision procedure used (`ESBMC-boolector`) and', 'such as', esbmc_output, flags=re.MULTILINE)

    esbmc_output = re.sub(r'These details are not directly related to understanding the vulnerabilities in the code.*|\.\s*.*are not direclty related to understanding the vulnerabilities.*|\.\s*.*are not relevant to understanding the vulnerabilities.*', '', esbmc_output, flags=re.MULTILINE)
    esbmc_output = re.sub(r'\s*\(\s*`thread\d+`(?:,\s*`thread\d+`)*\s*\)', '', esbmc_output) #It is not neccesary to mention threads in parantheses, as they are all explained afterwards
    esbmc_output = re.sub(r'.*(`ESBMC-boolector`).*', '', esbmc_output, flags=re.MULTILINE)

    esbmc_output = re.sub(r'^\s*\n', '', esbmc_output)
    esbmc_output = re.sub(r'\n{2,}', '\n', esbmc_output)
    esbmc_output = re.sub(r': The version of ESBMC.*', '', esbmc_output, flags=re.MULTILINE) 

    esbmc_output = re.sub(r'\*\*"No bug has been found in the base case"\*\*:.*', '**"No bug has been found in the base case"**', esbmc_output, flags=re.MULTILINE)
    esbmc_output = re.sub(r' This suggests that the system modeled by the program, under the constraints and assertions defined, behaves as expected without leading to any undesired or erroneous states within the bounded context.', '', esbmc_output, flags=re.MULTILINE) #The output is more concise without this sentence, and all relevant aspects are still provided.
    
    return esbmc_output

def remove_patterns_nltk(text):
    # Tokenize the text into sentences
    sentences = text.split('\n')
    
    # Define the pattern to be removed
    pattern = "Runtime decision procedure:"
    pattern2 = "BMC program time:"
    thread_pattern = re.compile(r'\(`thread\d+`(?:,\s*`thread\d+`)*\)\s', re.IGNORECASE)
    warning_pattern = re.compile(r'- \*\*Warnings\*\*:.*', re.IGNORECASE)
    warning_pattern2 = re.compile(r'A series of wanings are issued', re.IGNORECASE)    
    conclusion_pattern = re.compile(r'### In Conclusion ###.*', re.IGNORECASE)
    bmc_time = re.compile(r'BMC program time:\d+\.\d+s')    
    runtime_pattern =re.compile(r'Runtime decision procedure:\d+\.\d+s')
    
    # Iterate over each sentence
    for i in range(len(sentences)):
        # Tokenize the sentence into words
        words = word_tokenize(sentences[i])
        
        # If the pattern is in the sentence, remove it
        if pattern in words:
            # Find the index of the pattern
            index = words.index(pattern)
            
            # Remove the pattern and the next two words (the time and 's')
            if len(words) > index + 2 and words[index + 2] == 's':
                del words[index:index+3]
            
            # Join the words back into a sentence
            sentences[i] = ' '.join(words)
        if pattern2 in words:
            index = words.index(pattern2)

            if len(words) > index+2 and words[index+2] == 's':
                del words[index:index+3] 
            sentences[i] = ' '.join(words)   
    
    # Remove thread patterns
    cleaned_sentences = [thread_pattern.sub('', sentence) for sentence in sentences]
    cleaned_sentences = [warning_pattern.sub('', sentence) for sentence in cleaned_sentences]
    cleaned_sentences = [warning_pattern2.sub('', sentence) for sentence in cleaned_sentences]
    cleaned_sentences = [conclusion_pattern.sub('', sentence) for sentence in cleaned_sentences]
    cleaned_sentences = [bmc_time.sub('', sentence) for sentence in cleaned_sentences]
    cleaned_sentences = [runtime_pattern.sub('', sentence) for sentence in cleaned_sentences]    
    
    cleaned_sentences = [line for line in cleaned_sentences if line.strip() !='']
    
    # Join the sentences back into a text
    modified_text = '\n'.join(cleaned_sentences)
    
    return modified_text


def esbmc_load_source_code(
    file_path: str,
    source_code: str,
    esbmc_params: list = config.esbmc_params,
    auto_clean: bool = config.temp_auto_clean,
    timeout: Optional[float] = None,
):
    source_code_path = Path(file_path)

    # Create temp path.
    delete_path: bool = False
    if not os.path.exists(config.temp_file_dir):
        os.mkdir(config.temp_file_dir)
        delete_path = True

    temp_file_path = f"{config.temp_file_dir}{os.sep}{source_code_path.name}"

    # Create temp file.
    with open(temp_file_path, "w") as file:
        # Save to temporary folder and flush contents.
        file.write(source_code)
        file.flush()

        # Call ESBMC to temporary folder.
        results = esbmc(file.name, esbmc_params, timeout=timeout)

    # Delete temp files and path
    if auto_clean:
        # Remove file
        os.remove(temp_file_path)
        # Remove file path if created this run and is empty.
        if delete_path and len(os.listdir(config.temp_file_dir)) == 0:
            os.rmdir(config.temp_file_dir)

    # Return
    return results
