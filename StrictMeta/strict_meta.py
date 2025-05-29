import ast
from inspect import cleandoc, getsourcelines
import importlib.util

from typing import Annotated, get_type_hints, LiteralString, TypeVar, Type


def get_source(module_name: str) -> list[str]:
    """
    Retrieves the source code of a module by its name.

    :param module_name: The name of the module to retrieve.
    :type module_name: str
    :return: A list of strings representing the source code lines.
    :rtype: list[str]
    :raises ImportError: If the module cannot be found.
    :raises FileNotFoundError: If the source code for the module could not be found.
    """
    spec = importlib.util.find_spec(module_name)
    if not spec or not spec.loader:
        raise ImportError(f"Module '{module_name}' could not be found")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # Use exec_module instead of load_module
    source, _ = getsourcelines(module)
    if not source:
        raise FileNotFoundError(f"Source code for module '{module_name}' could not be found")
    return source

def get_inline_comment(module_name: str, class_line: int, attr_name: str) -> tuple[LiteralString | None, LiteralString | None]:
    """
    Retrieves the inline comment and docstring for a given attribute in a class.

    :param module_name: The name of the module containing the class.
    :type module_name: str
    :param class_line: The line number where the class is defined.
    :type class_line: int
    :param attr_name: The name of the attribute to retrieve the comment for.
    :type attr_name: str
    :return: A tuple containing the inline comment and docstring (if any).
    :rtype: tuple[LiteralString | None, LiteralString | None]
    """
    source = get_source(module_name)

    tree = ast.parse("".join(source))
    class_definitions = [node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]

    comment = ""
    docstring = ""

    for cls_def in class_definitions:
        if cls_def.lineno != class_line:
            continue
        prev_node = None
        for node in cls_def.body:
            if (isinstance(node, ast.AnnAssign) and
                    isinstance(node.target, ast.Name) and
                    node.target.id == attr_name):
                # Extract the lines of code where the attribute is assigned
                start_line = node.lineno
                end_line = getattr(node, 'end_lineno', None)
                if end_line is None:
                    end_line = start_line

                comment = source[end_line-1][node.end_col_offset:].strip().lstrip('#').strip()

            if isinstance(prev_node, (ast.Assign, ast.AnnAssign)) and prev_node.target.id == attr_name:
                if (isinstance(node, ast.Expr)
                        and isinstance(node.value, ast.Constant)
                        and isinstance(node.value.value, str)):
                    docstring = cleandoc(node.value.value)
            prev_node = node

        break
    else:
        # TODO: Maybe check readline history
        raise SystemError("The current Python environment does not support sufficient introspection")

    return comment if comment else None, docstring if docstring else None

class Comment:
    """
    Metadata class to store comments and descriptions for configuration fields.

    :param default: The default value of the field (optional).
    :type default: any
    :param comment: A short inline comment for the field (optional).
    :type comment: str
    :param description: A detailed description of the field (optional).
    :type description: str
    """
    def __init__(self, default=None, comment: str = None, description: str = None):
        self.default = default
        self.comment = comment
        self.description = description

    @classmethod
    def get_comment(cls, type_, attr: str) -> 'Comment | None':
        """
        Retrieves the Comment object for a given class and field.

        :param type_: The class to retrieve the comment from.
        :type type_: type
        :param attr: The attribute name to retrieve the comment for.
        :type attr: str
        :return: The Comment object if found, otherwise None.
        :rtype: Comment | None
        """
        if not hasattr(type_, '__annotations__'):
            return None
        annotations = getattr(type_, '__annotations__')
        annotation = annotations.get(attr)
        if annotation is None:
            return None
        metadata = getattr(annotation, '__metadata__', [])

        for meta in metadata:
            if isinstance(meta, Comment):
                return meta
        return None

    def __repr__(self) -> str:
        """Return a string representation of the Comment object.

        :return: String representation of the Comment object.
        :rtype: str
        """
        return f"Comment(default={self.default}, comment='{self.comment}', description='{self.description}')"


class StrictMeta(type):
    """
    Metaclass to enforce strict type checking and metadata handling for classes.

    This metaclass ensures that all attributes in a class have proper type annotations.
    It also handles comments and descriptions associated with these annotations by collecting
    them from the class and its base classes, creating slots based on these annotations,
    and updating metadata for each annotation by adding or updating `Comment` objects.
    """

    def __new__(cls, name: str, bases: tuple[type], namespace: dict[str, any]) -> type:
        """
        The `__new__` method of this metaclass is responsible for creating new classes.

        - Collects annotations from both the class itself and its base classes.
        - Inspects the docstrings of attributes to extract comments and descriptions.
        - Initializes `Comment` objects with these comments and descriptions, adding them to the metadata of type annotations.
        - Updates existing annotations with default values and comments from the docstring.
        - Creates slots for the class based on the collected annotations.
        - Removes the annotations from the namespace to avoid conflicts with slots.
        - Updates the namespace with the collected and updated annotations.

        :param name: The name of the new class.
        :type name: str
        :param bases: The base classes of the new class.
        :type bases: tuple[type]
        :param namespace: The namespace of the new class.
        :type namespace: dict[str, any]
        """

        # Collect annotations from the class and its bases
        annotations = {}
        for base in reversed(bases):
            if hasattr(base, '__annotations__'):
                annotations.update(get_type_hints(base))

        if '__annotations__' in namespace:
            annotations.update(namespace['__annotations__'])

        # Create slots based on the collected annotations
        slots = list()

        # Update metadata for each annotation
        for key, _type in annotations.items():
            if key.startswith('__'):
                continue
            slots.append(key)

            print(f"{ namespace['__module__']} {namespace.get('__firstlineno__', 0)} {key}")

            # Extract inline comments from the source code
            comment, description = get_inline_comment(
                namespace['__module__'], namespace.get('__firstlineno__', 0), key)

            if not comment and description:
                comment, *description = description.split('\n', 1)
                description = '\n'.join(description) or ""

            # Add __metadata__ if it doesn't exist
            if not hasattr(_type, '__metadata__'):
                _type = Annotated[_type, Comment(
                    default=namespace.get(key),
                    comment=comment,
                    description=description
                )]
                annotations[key] = _type
                continue

            # Update the Comment object in __metadata__
            metadata = list(getattr(_type, '__metadata__', []))
            for data in metadata:
                if isinstance(data, Comment):
                    data.default = data.default or namespace.get(key)
                    data.comment = data.comment or comment
                    data.description = data.description or description
                    break
            else:
                # Add Comment object to __metadata__
                metadata.append(Comment(
                    default=namespace.get(key),
                    comment=comment,
                    description=description
                ))
                _type.__metadata__ = tuple(metadata)

        # Check for attributes without annotations and raise an error
        for key in namespace.keys():
            if key not in annotations and not key.startswith('__'):
                raise TypeError(f"Attribute '{key}' is not annotated")

        # Add __slots__ to the class namespace
        namespace['__slots__'] = slots

        # Remove the annotations from the namespace to avoid conflicts with slots
        for key in list(annotations.keys()):
            if key in namespace:
                del namespace[key]

        # Update the namespace with the collected and updated annotations
        namespace['__annotations__'] = annotations

        return super().__new__(cls, name, bases, namespace)

    def __setattr__(cls, name: str, value: any) -> None:
        """
        Override to prevent adding new class attributes and enforce type checking.

        :param name: The name of the attribute.
        :type name: str
        :param value: The value of the attribute.
        :type value: any
        :raises AttributeError: If a new attribute is attempted to be added.
        """
        if not hasattr(cls, '__annotations__') or name not in cls.__annotations__:
            raise AttributeError(f"Cannot add new class attribute '{name}'")

        expected_type = cls.__annotations__[name]
        # Extract the base type from Annotated
        if hasattr(expected_type, '__origin__'):
            expected_type = expected_type.__origin__

        if not isinstance(value, expected_type):
            raise TypeError(f"Cannot set attribute '{name}' to value of type {type(value).__name__}. Expected type is {expected_type.__name__}.")

T = TypeVar('T')

def strict(cls: Type[T] = None) -> StrictMeta:
    """ Class decorator for classes to use StrictMeta as metaclass.

    :param cls: The class to be decorated.
    :type cls: type | None
    :return: A new class with StrictMeta as its metaclass.
    :rtype: type
    """
    __name = str(cls.__name__)
    __bases = tuple(cls.__bases__)
    __dict = dict(cls.__dict__)

    source = get_source(cls.__module__)
    line_number = cls.__firstlineno__

    tree = ast.parse("".join(source))
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            if hasattr(node, 'decorator_list'):
                for decorator in node.decorator_list:
                    if decorator.lineno == line_number:
                        line_number = node.lineno
                        break
                else:
                    continue
                break
    else:
        raise SystemError("The current Python environment does not support sufficient introspection")

    if "__slots__" in __dict:
       for each_slot in __dict["__slots__"]:
            __dict.pop(each_slot, None)

    __dict["__metaclass__"] = StrictMeta
    __dict["__firstlineno__"] = line_number
    __dict["__wrapped__"] = cls

    newcls = StrictMeta(__name, __bases, __dict)

    return newcls
