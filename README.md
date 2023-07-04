# ESBMC AI

AI Augmented ESBMC processing. Passes the output from ESBMC to an AI model that allows the user to use natural language to understand the output. As the output from ESBMC can be quite technical in nature. The AI can also be asked other questions, such as suggestions on how to fix the problem outputted by ESBMC, and to offer further explanations.

This is an area of active research.

![ESBMC-AI Virtual Abstract](https://github.com/Yiannis128/esbmc-ai/assets/9535618/45101fa7-2fda-4603-856b-63739acee606)

## Demonstration

### Basic Usage Demo

[demo.webm](https://user-images.githubusercontent.com/9535618/235352993-b54c47ef-a1c6-422c-aa5b-07edc2988521.webm)

### Fix Code Demo

[demo_fix_code.webm](https://github.com/Yiannis128/esbmc-ai/assets/9535618/e35882ee-7e50-4c10-9879-d19e73d7f45d)

### YouTube Channel

More videos can be found on the [ESBMC-AI Youtube Channel](https://www.youtube.com/@esbmc-ai)

## ESBMC

From the [ESBMC website](http://esbmc.org):

> ESBMC is an open source, permissively licensed, context-bounded model checker
> based on satisfiability modulo theories for the verification of single and
> multi-threaded C/C++ programs. It does not require the user to annotate the
> programs with pre- or postconditions, but allows the user to state additional
> properties using assert-statements, that are then checked as well. Furthermore,
> ESBMC provides two approaches (lazy and schedule recording) to model check
> multi-threaded programs. It converts the verification conditions using different
> background theories and passes them directly to an SMT solver.

From the [ESBMC GitHub repo](https://github.com/esbmc/esbmc)

> The efficient SMT-based context-bounded model checker (ESBMC)

## Wiki

For full documentation, see the [ESBMC-AI Wiki](https://github.com/Yiannis128/esbmc-ai/wiki). The README file contains quick setup instructions. For more detailed setup instructions, see the [Initial Setup](https://github.com/Yiannis128/esbmc-ai/wiki/Initial-Setup) page.

## Initial Setup

1. Install required Python modules: `pip3 install -dr requirements.txt`. Alternatively use `pipenv shell` to go into a virtual environment and run `pipenv lock -d` to install dependencies from the Pipfile.
2. ESBMC-AI does not come with the original ESBMC software. In order to use ESBMC-AI you must download ESBMC. Download the [ESBMC](http://esbmc.org/) executable or build from [source](https://github.com/esbmc/esbmc).
3. Once the ESBMC software is downloaded, open the `config.json` file, and edit the `esbmc_path` field to specify the location of ESBMC, it's recommended for development purposes to either install it globally or have it in the project root folder.
4. Create a `.env` file using the provided `.env.example` as a template. **Make sure to insert your OpenAI API and Hugging Face key inside the `.env` file you just created!**
5. Further, adjust `.env` settings as required.
6. Further, adjust the `config.json` file as required. Be careful when editing AI model messages as incorrect messages can break the flow of the program, or introduce incorrect results. In general, it's recommended to leave those options alone.
7. You can now run ESBMC-AI. See usage instructions below.

## Settings

### .env

The `.env` file contains the configuration of sensitive data. An example `.env.example` file is given as a template. It should be renamed into `.env` in order to be used by the program. The following settings are adjustable in the .env file:

1. `OPENAI_API_KEY`: Your OpenAI API key.
2. `HUGGINGFACE_API_KEY`: Your Hugging Face API key.
3. `ESBMC_AI_CFG_PATH`: ESBMC AI requires a path to a JSON config file, the default path is `./config.json`. This can be changed to another path, if there is a preference for multiple files.

### config.json

The following settings are adjustable in the `config.json` file:

1. `ai_model`: The model to use. List of models available [here](https://github.com/Yiannis128/esbmc-ai/wiki/AI-Models).
2. `ai_custom`: Allows for specifying custom `text-generation-inference` servers to use. For more information see [the wiki page](https://github.com/Yiannis128/esbmc-ai/wiki/AI-Models#custom-llm).
3. `esbmc_path`: Override the default ESBMC path. Leave blank to use the default ("./esbmc").
4. `esbmc_params`: Array of strings. This represents the default ESBMC parameters to use when calling ESBMC, these will be used only when no parameters are specified after the filename. **Do not specify a source file to scan in here as ESBMC-AI will inject that in the ESBMC parameters itself**.
5. `consecutive_prompt_delay`: Rate limit wait time for API calls.
6. `temp_auto_clean`: Boolean value describing if to clean temporary files from the temporary directory as soon as they are not needed.
7. `temp_file_dir`: The directory to save temporary files in.
8. `chat_modes`: Contains settings that belong to each individual chat mode. It is not recommended to change these as changing them will impact the effectiveness of the LLMs.

## Usage

### Basic

ESBMC-AI can be used to scan a file with default parameters like this:

```bash
./esbmc_ai.py /path/to/source_code.c
```

### ESBMC-AI Parameters

Any parameters before the filename will be processed and consumed by ESBMC-AI.
So in this case `-vr` will be consumed by ESBMC-AI, and ESBMC will not get any
arguments.

```bash
./esbmc_ai.py -vr /path/to/source_code.c
```

### Help

```bash
./esbmc_ai.py -h
```

### ESBMC Arguments

Below are some very useful arguments that can be passed to ESBMC:

```
Property checking:
  --compact-trace                  add trace information to output
  --no-assertions                  ignore assertions
  --no-bounds-check                do not do array bounds check
  --no-div-by-zero-check           do not do division by zero check
  --no-pointer-check               do not do pointer check
  --no-align-check                 do not check pointer alignment
  --no-pointer-relation-check      do not check pointer relations
  --no-unlimited-scanf-check       do not do overflow check for scanf/fscanf
                                   with unlimited character width.
  --nan-check                      check floating-point for NaN
  --memory-leak-check              enable memory leak check
  --overflow-check                 enable arithmetic over- and underflow check
  --ub-shift-check                 enable undefined behaviour check on shift
                                   operations
  --struct-fields-check            enable over-sized read checks for struct
                                   fields
  --deadlock-check                 enable global and local deadlock check with
                                   mutex
  --data-races-check               enable data races check
  --lock-order-check               enable for lock acquisition ordering check
  --atomicity-check                enable atomicity check at visible
                                   assignments
  --stack-limit bits (=-1)         check if stack limit is respected
  --error-label label              check if label is unreachable
  --force-malloc-success           do not check for malloc/new failure
```

Some examples of passing parameters to ESBMC:

```
./esbmc_ai.py /path/to/source_code.c --force-malloc-success --no-assertions --unwind 5
```

Basically, any arguments **after** the filename are passed directly to ESBMC.

### In-Chat Commands Help

Type the following command when inside the chat:

```
/help
```

## Contributing

Pull requests are welcome. For major changes, please open an issue first
to discuss what you would like to change.

1. Keep the coding style consistent. Use the [Black](https://pypi.org/project/black/) code formatter.
2. Keep the righting style professional.
3. Include comments and function doc-strings.
4. Make sure to update tests as appropriate.

## Acknowledgments

- [ESBMC](https://github.com/esbmc/esbmc)
- [OpenAI Chat API](https://platform.openai.com/docs/guides/chat)
- [Technology Innovation Institute](https://www.tii.ae/)
- [Hugging Face](https://huggingface.co/)

## License

[GNU Affero General Public License v3.0](https://github.com/Yiannis128/esbmc-ai/blob/master/LICENSE)
