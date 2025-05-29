 # StrictMeta

[![PyPI Version](https://img.shields.io/pypi/v/StrictMeta)](https://pypi.org/project/StrictMeta/)
[![Python Versions](https://img.shields.io/pypi/pyversions/StrictMeta)](https://pypi.org/project/StrictMeta/)
[![License](https://img.shields.io/github/license/yourusername/StrictMeta)](https://github.com/Karsten-Merkle/StrictMeta/blob/main/lgpl-3.0.md)

A metaclass to enforce strict type checking and metadata handling for classes in Python.

`StrictMeta` is most beneficial in environments where consistency, predictability, and clear documentation of data types are crucial. It's particularly useful for maintaining API stability across different versions or releases, ensuring that future modifications respect the original design intentions. However, it should be used with caution in performance-critical applications or when flexibility in attribute manipulation is essential.

For projects where strict type enforcement is not critical but clear documentation and maintainability are priorities, a more gradual approach to adding type annotations might be more appropriate.

## Table of Contents
- [Introduction](#introduction)
- [Installation](#installation)
- [Usage Examples](#usage-examples)
  - [Type Annotations](#type-annotations)
  - [Comments and Descriptions](#comments-and-descriptions)
- [Contributing](#contributing)
- [License](#license)

## Introduction

StrictMeta is a metaclass that enforces strict type checking and metadata handling for classes. It ensures that all attributes in a class have proper type annotations, collects comments and descriptions from the class and its base classes, creates slots based on these annotations, and updates metadata for each annotation by adding or updating `Comment` objects.

### When to Use StrictMeta

1. **Ensuring Type Consistency**: If you have a class hierarchy where all subclasses must adhere to specific types for certain attributes, `StrictMeta` ensures that these type constraints are enforced across the entire inheritance chain. This is particularly useful in large codebases or when collaborating with other developers who might not strictly follow your coding standards.

2. **Documentation and Metadata**: For classes where clarity and documentation are crucial (e.g., APIs, configuration classes), `StrictMeta` can automatically collect comments and descriptions from attributes and provide a clear, documented interface to users of the class. This is particularly useful for maintaining API stability over time as attribute names and types might change but their purpose should remain consistent.

3. **Automated Testing**: In automated testing environments, where scripts or frameworks expect specific data types, `StrictMeta` can help catch type mismatches early in the development cycle, reducing runtime errors that could otherwise lead to bugs or crashes during execution.

4. **Legacy Code Refactoring**: For projects looking to refactor legacy code by gradually adding type annotations and metadata handling, `StrictMeta` provides a structured way to enforce these changes without disrupting existing functionality.

### When to Avoid StrictMeta

1. **Performance Overhead**: If your project heavily relies on dynamic attribute manipulation or if performance is critical (e.g., in high-frequency trading systems), the overhead of type checking and metadata handling might be unnecessary and could slow down execution. In such cases, a more lightweight approach without strict type enforcement might be preferable.

2. **Flexibility vs. Constraints**: If you need maximum flexibility in your class definitions (e.g., allowing attributes to change types frequently), `StrictMeta`’s rigid enforcement of types and annotations might restrict the design freedom you require. In such scenarios, a more flexible approach without strict type checking would be more appropriate.

3. **Learning Curve**: For new developers joining the project, especially those less familiar with Python's typing system or the specific conventions you've adopted for `StrictMeta`, there could be a learning curve in understanding how to properly annotate classes and what metadata means. This might slow down their productivity initially until they become comfortable with your coding standards.

## Installation

To install StrictMeta, you can use pip:

```bash
pip install StrictMeta
```

## Usage Examples


Let's assume we have a configuration class for a software application where certain attributes must be of specific types, and these types need to be clearly documented. We can use `StrictMeta` to ensure that all attributes are properly annotated and commented.

We create an instance of `AppConfig` and set values to its attributes. If a value is assigned that does not match the expected type, a `TypeError` is raised, indicating that the attribute was not set correctly according to the type annotation.


```python
from StrictMeta import strict, get_comment

@strict
class AppConfig:
    """
    Configuration class for the software application.
    """
    api_key: str  # API key used for authentication
    max_connections: int = 256  # Maximum number of simultaneous connections allowed
    """ These are the"""
    debug_mode: bool  = False  # Whether debugging is enabled or not

# Example usage
config = AppConfig()
config.api_key = "your_api_key"
try:
    config.max_connections = "not_an_integer"  # This will raise a TypeError
except TypeError as e:
    print(e)  # Output: Cannot set attribute 'max_connections' to value of type <class 'str'>. Expected type is <class 'int'>.

config.max_connections = 64

# You may still retrieve the default connections
max_connections_comment = get_comment(AppConfig, 'max_connections')
print(f"default is {max_connections_comment.default}")  # Output: default is 256

# You may als retrieve the inline comment:
print(f"comment is {max_connections_comment.comment}")  # Output: comment is Maximum number of simultaneous connections allowed

```

### Type Annotations

The attributes `api_key`, `max_connections`, and `debug_mode` are annotated with their respective types (`str`, `int`, and `bool`). These annotations will be enforced by `StrictMeta`.

### Comments and Descriptions

Comments for each attribute are provided in the docstring of the class. These comments will be collected and associated with the type annotations.

## Contributing

Contributions are welcome! Please read the [CONTRIBUTING.md](https://github.com/Karsten-Merkle/StrictMeta/blob/main/CONTRIBUTING.md) file for more information on how to contribute to this project.

## License

StrictMeta is available under the GNU Lesser General Public License version 3

---

Thank you for considering using StrictMeta! We hope it helps you enforce strict type checking and metadata handling in your Python projects.