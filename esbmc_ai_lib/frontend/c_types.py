from esbmc_ai_lib.frontend.ast_decl import Declaration


_primitives_base_defaults: list[str] = [
    # Bool
    "bool",
    # Decimals
    "float",
    "double",
    "long double",
    # Char
    "char",
    "signed char",
    "unsigned char",
    # Int
    "int",
    "signed int",
    "unsigned int",
    # Short
    "short",
    "signed short",
    "unsigned short",
    # Short (int)
    "short int",
    "signed short int",
    "unsigned short int",
    # Long
    "long",
    "signed long",
    "unsigned long",
    # Long (int)
    "long int",
    "signed long int",
    "unsigned long int",
    # Long Long
    "long long",
    "signed long long",
    "unsigned long long",
    # Long Long (int)
    "long long int",
    "signed long long int",
    "unsigned long long int",
]
"""Assign the following values for each primitive data type."""


def get_base_type(type_name: str) -> str:
    type_name = type_name.replace("*", "").replace("[]", "").strip()
    # FIXME This is to get rid of modifiers such as const. But this REALLY needs to be replaced
    # with tokenization because of the fact that such keywords can vary in position.
    spl = type_name.split(" ")
    if len(spl) > 1:
        type_name = spl[1]
    return type_name


def is_primitive_type(d: Declaration) -> bool:
    # Strip pointer and array info before checking if is primitive type.
    return get_base_type(d.type_name) in _primitives_base_defaults
