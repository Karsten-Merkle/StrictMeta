import ast
from collections import defaultdict
from inspect import cleandoc, getsourcelines
import importlib.util
from types import ModuleType

from typing import Annotated, get_type_hints, LiteralString, Dict, List, Any, Optional, Generator, Tuple


def get_module(module_name: str) -> ModuleType:
    """Retrieve a module by its name.

    :param module_name: The name of the module to retrieve.
    :return: The retrieved module.
    :raises ImportError: If the module cannot be found.
    """
    spec = importlib.util.find_spec(module_name)
    if not spec or not spec.loader:
        raise ImportError(f"No module named '{module_name}'")
    return importlib.util.module_from_spec(spec)


def get_module_source(module: str | ModuleType) -> list[str]:
    """
    Retrieves the source code of a module by its name or module object.

    :param module: The name or module of the module to retrieve.
    :return: A list of strings representing the source code lines.
    :raises ImportError: If the module cannot be found.
    :raises OSError: If the source code for the module could not be found.
    """
    if isinstance(module, str):
        module = get_module(module)
    source, _ = getsourcelines(module)
    if not source:
        raise OSError(f"Source code for module '{module}' could not be found")
    return source


def get_class_source(module: str | ModuleType,
                     class_: str | type | None = None,
                     line_no: int | None = None
                     ) -> Dict[int, List[str]]:
    """
    Retrieves and formats the source code of a class within a module.

    The source code is retrieved and any leading indentation is removed.

    :param module: The name or module of the module containing the class.
    :param class_: The name or type of the class to retrieve.
    :param line_no: The specific line number where the class is defined (optional).
    :return: A dictionary where the key is the start line number of the class definition and the value is the source code of the class.
    :raises ImportError: If the module cannot be found.
    :raises OSError: If the source code for the class could not be found.
    :raises ValueError: If the source code has inconsistent indentation.
    """
    stripped_sources: Dict[int, List[str]] = {}
    for first_line, source in _get_class_source(module, class_, line_no).items():
        indent: str = ''
        stripped_source: List[str] = []
        for char in source[0]:
            if char.isspace():
                indent += char
            else:
                break
        for line in source:
            if not line.startswith(indent):
                raise ValueError(f"Inconsistent indentation in source code")
            stripped_source.append(line[len(indent):])
        stripped_sources[first_line] = stripped_source

    return stripped_sources


def _get_class_source(module: str | ModuleType,
                     class_: str | type | None = None,
                     line_no: int | None = None
                     ) -> Dict[int, List[str]]:
    """
    Retrieves the source code of a class within a module.

    :param module: The name or module of the module containing the class.
    :param class_: The name or type of the class to retrieve.
    :param line_no: The specific line number where the class is defined (optional).
    :return: A dictionary where the key is the start line number of the class definition and the value is the source code of the class.
    :raises ImportError: If the module cannot be found.
    :raises OSError: If the source code for the class could not be found.
    """
    source: List[str] = get_module_source(module)
    if class_ and not isinstance(class_, str):
        class_name: str = class_.__name__
    else:
        class_name = class_

    tree: ast.Module = ast.parse("".join(source))
    sources: Dict[int, List[str]] | None = None

    if line_no and not class_name:
        # get the class defined at line_no
        for start, end, _ in _class_iterator(tree):
            if start == line_no:
                return {start: source[start-1:end]}
    elif class_name and not line_no:
        # get all classes with the name class_
        sources = {}
        for start, end, name in _class_iterator(tree):
            if name == class_name:
                sources[start] = source[start-1:end]
    elif not class_name and not line_no:
        # get all classes in this module
        sources = {start: source[start-1:end] for start, end, _ in _class_iterator(tree)}
    else:
        # get only that class which is at line line_no and has the name class_name
        for start, end, name in _class_iterator(tree):
            if name == class_name and line_no == start:
                return {start: source[start-1:end]}

    if sources:
        return sources
    if line_no:
        raise OSError(
            f"Source code class '{class_name}' in module '{module}' could not be found at line {line_no}")
    else:
        raise OSError(
            f"Source code class '{class_name}' in module '{module}' could not be found")

def _class_iterator(tree: Any) -> Generator[Tuple[int, int, str], None, None]:
    """
    Iterates over all class definitions in an AST tree.

    :param tree: The AST tree to iterate over.
    :yield: A tuple containing the start line number, end line number, and name of each class definition.
    """
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            start_line: int = node.lineno
            end_line: int = getattr(node, 'end_lineno', None) or start_line
            yield start_line, end_line, node.name


def get_inline_comments(module_name: LiteralString,
                       class_line: int,
                        ) -> Dict[str, "Comment"]:
    """
    Extracts inline comments and docstrings from the source code of a given module and class line number.

    :param module_name:
    :param class_line:
    :return: A dictionary mapping attribute names to their corresponding Comment objects
    """
    source = get_class_source(module_name, line_no=class_line)[class_line]
    tree = ast.parse("".join(source))


    comments = defaultdict(Comment)
    prev_node = None

    for node in ast.walk(tree):
        if (isinstance(node, ast.AnnAssign) and
                isinstance(node.target, ast.Name)):
            start_line = node.lineno
            end_line = getattr(node, 'end_lineno', None)
            if end_line is None:
                end_line = start_line

            comments[node.target.id].comment = source[end_line - 1][node.end_col_offset:].strip().lstrip('#').strip()

        if isinstance(prev_node, (ast.Assign, ast.AnnAssign)):
            if (isinstance(node, ast.Expr)
                    and isinstance(node.value, ast.Constant)
                    and isinstance(node.value.value, str)):
                comments[prev_node.target.id].description= cleandoc(node.value.value)
        prev_node = node

    # normalize comments
    # if no inline comment, but docstring is multiline, take first line of docstring as comment
    for key, entry in comments.items():
        if not entry.comment and entry.description:
            comment, *description = entry.description.split("\n", 1)
            description = "\n".join(description).strip()
            if description:
                # if no comment but docstring is Multiline, first docstring is comment
                entry.description = description
                entry.comment = comment
                continue
        entry.description = entry.description or None
        entry.comment = entry.comment or None

    return comments

class Comment:
    """
    Metadata class to store comments and descriptions for configuration fields.
    """
    def __init__(self, default=None, comment: str = None, description: str = None):
        """
        :param default: The default value of the field (optional).
        :param comment: A short inline comment for the field (optional).
        :param description: A detailed description of the field (optional).
        """
        self.default = default
        self.comment = comment
        self.description = description

    def merge_into(self, comment: Optional["Comment"]):
        """
        Updates all empty values of the given comment with the values from the current comment.
        If no comment is given, a copy of this comment will be returned.

        Values existing in given comment object have precedence:
        if value in comment...
        - is None, it will be replaced.
        - is '' (empty) empty has precedence.
        :param comment: The comment object to merge into.
        :return: The merged comment object.
        """
        if comment is None:
            return Comment(self.default, self.comment, self.description)
        if comment.comment is None:
            comment.comment = self.comment
        if comment.description is None:
            comment.description = self.description
        if comment.default is None:
            comment.default = self.default
        return comment


    def __repr__(self) -> str:
        """Return a string representation of the Comment object.

        :return: String representation of the Comment object.
        """
        return f"Comment(default={self.default}, comment='{self.comment}', description='{self.description}')"


def get_comment(type_: type, attr: str) -> 'Comment | None':
    """
    Retrieves the Comment object for a given class and field if available.
    The Comment is looked up in the annotated metadata of the given attr.

    :param type_: The class to retrieve the comment from.
    :param attr: The attribute name to retrieve the comment for.
    :return: The Comment object if found, otherwise None.
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


def update_comment(_type: type, comment: Comment) -> type:
   # Add __metadata__ if it doesn't exist
    if not hasattr(_type, '__metadata__'):
        return Annotated[_type, comment]

    # Update the Comment object in __metadata__
    metadata = list(getattr(_type, '__metadata__', []))
    for data in metadata:
        if isinstance(data, Comment):
            comment.merge_into(data)
            return _type
    else:
        # create a new copy of Annotation with added Comment object to __metadata__
        return Annotated[_type, comment]


class StrictMeta(type):
    """
    Metaclass to enforce strict type checking and metadata handling for classes.

    This metaclass ensures that all attributes in a class have proper type annotations.
    It also handles comments and descriptions associated with these annotations by collecting
    them from the class and its base classes, creating slots based on these annotations,
    and updating metadata for each annotation by adding or updating `Comment` objects.
    """

    def __new__(cls, name: str, bases: tuple[type,...], namespace: dict[str, any]) -> type:
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
        :param bases: The base classes of the new class.
        :param namespace: The namespace of the new class.
        """

        # Collect annotations from the class and its bases
        # TODO: keep at least a little bit to best-practices-for-annotations
        #       see: https://docs.python.org/3/howto/annotations.html#best-practices-for-annotations-in-any-python-version
        annotations = {}
        for base in reversed(bases):
            if hasattr(base, '__annotations__'):
                annotations.update(get_type_hints(base))

        if '__annotations__' in namespace:
            annotations.update(namespace['__annotations__'])

        # Create slots based on the collected annotations
        slots = list()

        comments = get_inline_comments(namespace['__module__'], namespace['__firstlineno__'])
        for attr, comment in comments.items():
            # set default values
            comment.default = namespace.get(attr)

        # Update metadata for each annotation
        for key, _type in annotations.items():
            if key.startswith('__'):
                continue
            slots.append(key)
            annotations[key] = update_comment(_type, comments[key])

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
        :param value: The value of the attribute.
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


def strict(cls: type) -> type:
    """ Class decorator for classes to use StrictMeta as metaclass.

    :param cls: The class to be decorated.
    :return: A new class with StrictMeta as its metaclass.
    :raises SystemError if introspection fails.
    """
    __name = str(cls.__name__)
    __bases = tuple(cls.__bases__)
    __dict = dict(cls.__dict__)

    source = get_module_source(cls.__module__)
    line_number = cls.__firstlineno__
    # but this is the line_number of the decorator

    tree = ast.parse("".join(source))
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            if hasattr(node, 'decorator_list'):
                for decorator in node.decorator_list:
                    if decorator.lineno == line_number:
                        line_number = node.lineno
                        # now line_number is first lin number of the class
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

    new_cls = StrictMeta(__name, __bases, __dict)

    return new_cls
