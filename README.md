# ESBMC AI

AI Augmented ESBMC processing. Passes the output from ESBMC to an AI model and
displays a prompt that allows to From the ESBMC GitHub:

> The efficient SMT-based context-bounded model checker (ESBMC)

## Initial Setup

1. Download [ESBMC](http://esbmc.org/) executable or build from [source](https://github.com/esbmc/esbmc).
2. Place it in the directory
3. Make sure it's named "ESBMC" with no extension.
4. Create a .env file using the provided .env.example as a template, and, insert your OpenAI API key.
5. Further adjust .env settings as required.

## Settings

The following settings are adjustable in the .env file, this list may be incomplete:

1. `OPENAI_API_KEY`: This is required. Your OpenAI API key.
2. `CHAT_TEMPERATURE`: The temperature parameter used when calling the chat completion API.
3. `AI_MODEL`: The model to use. Options: `gpt-3.5-turbo`, `gpt-4` (under API key conditions).

## Usage

### Basic

```bash
./main.py /path/to/source_code.c
```

### Help

```bash
./main.py -h
```

### In-Chat Commands

```
/help
```

## Contributing

Pull requests are welcome. For major changes, please open an issue first
to discuss what you would like to change.

Please make sure to update tests as appropriate.

## Acknowledgments

- [ESBMC](https://github.com/esbmc/esbmc)
- [OpenAI Chat API](https://platform.openai.com/docs/guides/chat)

## License

[GNU Affero General Public License v3.0](https://github.com/Yiannis128/esbmc-ai/blob/master/LICENSE)