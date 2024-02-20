# Author: Yiannis Charalambous

import json
from dataclasses import dataclass
from typing_extensions import override

from esbmc_ai_config.models.config_loader import ConfigLoader

__ALLOWED_JSON_TYPES = bool | float | int | str | list | dict

# TODO Write tests


@dataclass
class JsonConfigNode:
    default_value: "__ALLOWED_JSON_TYPES" = ""
    is_optional: bool = False
    """Will not load the config if the value is not specified by the user. If
    true will assign default_value."""
    show_in_config: bool = True
    """Show this field in the config tool UI."""
    _name: str = ""
    """Initialized automatically"""

    def __getitem__(self, subscript):
        """Allow indexing the default_values if they are a list or a dict.
        Can accept an int for default_values that are list or dict.
        Can accept a str for default_values that are dict."""
        # NOTE TestMe
        if isinstance(subscript, int) and isinstance(self.default_value, list):
            # Using list and int indexing
            return self.default_value[subscript]
        elif isinstance(subscript, str) and isinstance(self.default_value, dict):
            # Using str and dictionary indexing
            return self.default_value[subscript]
        raise IndexError(
            f"Invalid type of subscript: {type(subscript)}: type of value: {type(self.default_value)}"
        )


class JsonConfigLoader(ConfigLoader):
    def __init__(
        self,
        file_path: str = "~/.config/esbmc-ai.json",
        root_node: JsonConfigNode = JsonConfigNode(
            default_value={
                "esbmc_path": JsonConfigNode("~/.local/bin/esbmc"),
                "ai_model": JsonConfigNode("gpt-3.5-turbo-16k"),
                "ai_custom": JsonConfigNode({}),
                "allow_successful": JsonConfigNode(True),
                "esbmc_params": JsonConfigNode(
                    [
                        "--interval-analysis",
                        "--goto-unwind",
                        "--unlimited-goto-unwind",
                        "--k-induction",
                        "--state-hashing",
                        "--add-symex-value-sets",
                        "--k-step",
                        "2",
                        "--floatbv",
                        "--unlimited-k-steps",
                        "--memory-leak-check",
                        "--context-bound",
                        "2",
                    ]
                ),
                "consecutive_prompt_delay": JsonConfigNode(20),
                "temp_auto_clean": JsonConfigNode(True),
                "temp_file_dir": JsonConfigNode("~/.cache/esbmc-ai"),
                "loading_hints": JsonConfigNode(True),
                # TODO Finish fields
            }
        ),
        create_missing_fields: bool = False,
    ) -> None:
        assert file_path.endswith(
            ".json"
        ), f"{self.file_path} is not a valid json file."

        self.root_node: JsonConfigNode = root_node
        assert isinstance(self.root_node.default_value, dict)

        # TODO Initialize node default fields.
        self._init_json_nodes(self.root_node)

        super().__init__(
            file_path=file_path,
            create_missing_fields=create_missing_fields,
        )

    def _init_json_nodes(self, node: JsonConfigNode) -> None:
        """Initializes `_name` field of `JsonConfigNode`."""
        if isinstance(node.default_value, dict):
            for key, child_node in node.default_value.items():
                child_node._name = key
                self._init_json_nodes(child_node)

    @override
    def save(self) -> None:
        with open(self.file_path, "w") as f:
            json.dump(self.json_content, f)

    def _init_node_from_default(self, node: JsonConfigNode) -> "__ALLOWED_JSON_TYPES":
        """Recursively builds a json struct and returns it from the JsonConfigNode"""
        if isinstance(node.default_value, dict):
            values: dict = {}
            for key, value in node.default_value.items():
                values[key] = self._init_node_from_default(value)
            return values
        elif isinstance(node.default_value, list):
            # FIXME Not supported currently
            return node.default_value
        else:
            return node.default_value

    @override
    def _create_default_file(self) -> None:
        default_json: "__ALLOWED_JSON_TYPES" = self._init_node_from_default(
            self.root_node
        )
        assert isinstance(default_json, dict)
        with open(self.file_path, "w") as f:
            json.dump(default_json, f)

    @override
    def _read_fields(self, create_missing_fields: bool = False) -> None:
        """Parses the JSON config and loads all the values recursively. The self.values should
        map directly to how the self.node values are laid out.

        Arg:
            create_missing_field: bool - Will not give an error when an invalid/missing field
            is encountered, will instead initialize it to the default value."""
        self.json_content: dict = json.loads(self.content)

        def init_node_value(
            node: JsonConfigNode, json_node: "__ALLOWED_JSON_TYPES"
        ) -> "__ALLOWED_JSON_TYPES":
            """Initializes recursively the json nodes based on the template described in
            JsonConfigNode."""
            # Check if types match, if not then initialize to proper type. After this statement
            # all remaining types should be equal.
            if type(node.default_value) is not type(json_node):
                if create_missing_fields or node.is_optional:
                    return self._init_node_from_default(node)
                else:
                    raise ValueError(
                        f"JsonConfigLoader Error: {node._name} is not of type: "
                        f"{type(node.default_value)}, instead is {type(json_node)}"
                    )
            elif isinstance(node.default_value, list):
                # FIXME Lists not supported so they are not touched.
                return json_node
            # Recursive case: Check if type is object
            elif isinstance(node.default_value, dict):
                assert isinstance(json_node, dict)
                for name, child in node.default_value.items():
                    # Check each element of object.
                    # If node does not exist then create.
                    if name in json_node:
                        json_node[name] = init_node_value(child, json_node[name])
                    elif create_missing_fields or node.is_optional:
                        json_node[name] = self._init_node_from_default(child)
                    else:
                        raise ValueError(
                            f"JsonConfigLoader Error: {node._name} is not of type: "
                            f"{type(node.default_value)}, instead is {type(json_node)}"
                        )
                return json_node
            else:
                # Is primitive type so just return
                return json_node

        # Start with root object.
        json_content: "__ALLOWED_JSON_TYPES" = init_node_value(
            self.root_node, self.json_content
        )
        assert isinstance(json_content, dict)

        self.json_content = json_content

    def get_value(self, *path: str | int) -> "__ALLOWED_JSON_TYPES":
        current_value: "__ALLOWED_JSON_TYPES" = self.json_content
        for element in path:
            if isinstance(current_value, dict):
                current_value = current_value[element]
            elif isinstance(current_value, list) and isinstance(element, int):
                current_value = current_value[element]
            else:
                raise IndexError(f"Invalid access {element} from {path}")
        return current_value

    def set_value(self, value: "__ALLOWED_JSON_TYPES", *path: str | int) -> None:
        parent_path: tuple[int | str, ...] = path[:-1]
        parent_element = self.get_value(*parent_path)
        if isinstance(parent_element, list) and isinstance(path[-1], int):
            parent_element[path[-1]] = value
        elif isinstance(parent_element, dict):
            parent_element[path[-1]] = value
        else:
            raise IndexError(
                f"Invalid set value {value} of type {type(value)} "
                f"for {path[-1]} from {path}"
            )
