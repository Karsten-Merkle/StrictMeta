import unittest
from typing import Annotated

from StrictMeta import StrictMeta, Comment, strict, get_comment


class TestStrictMeta(unittest.TestCase):
    def test_basic_annotation(self):
        @strict
        class ExampleClass:
            x: int
        self.assertTrue(hasattr(ExampleClass, '__slots__'))
        self.assertEqual(ExampleClass.__slots__, ['x'])

    def test_comment_and_description(self):
        @strict
        class ExampleClass:
            """A class with comments and descriptions."""
            x: int  # This is a comment

        comment = get_comment(ExampleClass, 'x')
        self.assertIsInstance(comment, Comment)
        self.assertEqual(comment.comment, 'This is a comment')
        self.assertIsNone(comment.description)

    def test_default_value(self):
        class ExampleClass(metaclass=StrictMeta):
            """A class with default values."""
            x: int = 10  # This has a default value

        comment = get_comment(ExampleClass, 'x')
        self.assertIsInstance(comment, Comment)
        self.assertEqual(comment.default, 10)
        self.assertIsNone(comment.description)

    def test_full_metadata(self):
        class ExampleClass(metaclass=StrictMeta):
            """A class with full metadata."""
            x: int = 10  # This has a default value and a comment
            """This is a detailed description of x"""

        comment = get_comment(ExampleClass, 'x')
        self.assertIsInstance(comment, Comment)
        self.assertEqual(comment.default, 10)
        self.assertEqual(comment.description, 'This is a detailed description of x')

    def test_missing_annotation(self):
        with self.assertRaises(TypeError):
            class ExampleClass(metaclass=StrictMeta):
                """A class without annotations."""
                x = 10

    def test_slots_creation(self):
        class TestClass(metaclass=StrictMeta):
            x: int  # This should create a slot for 'x'
            y: str  # This should create a slot for 'y'

        self.assertIn('__slots__', TestClass.__dict__)
        self.assertEqual(set(TestClass.__slots__), {'x', 'y'})

    def test_type_annotation_enforcement(self):
        with self.assertRaises(TypeError):
            class InvalidClass(metaclass=StrictMeta):
                x = 5  # No type annotation

    def test_comment_metadata(self):
        class TestClassWithComment(metaclass=StrictMeta):
            x: int = 10  # This should have a Comment object with default value 10
            y: str  # This should have a Comment object without default value

        comment_x = get_comment(TestClassWithComment, 'x')
        self.assertIsNotNone(comment_x)
        self.assertEqual(comment_x.default, 10)

        comment_y = get_comment(TestClassWithComment, 'y')
        self.assertIsNotNone(comment_y)
        self.assertIsNone(comment_y.default)

    def test_attribute_addition(self):
        class StrictClass(metaclass=StrictMeta):
            x: int = 10
            y: str = "hello"

        with self.assertRaises(TypeError):
            StrictClass.x = "new attribute"

        with self.assertRaises(AttributeError):
            StrictClass.z = "new attribute"

        self.instance = StrictClass()
        with self.assertRaises(AttributeError):
            self.instance.z = "new attribute"

    def test_inheritance(self):
        class BaseClass(metaclass=StrictMeta):
            x: int  # This should be inherited

        class DerivedClass(BaseClass, metaclass=StrictMeta):
            y: str  # This should create a slot for 'y'

        self.assertIn('__slots__', DerivedClass.__dict__)
        self.assertEqual(set(DerivedClass.__slots__), {'x', 'y'})

    def test_complex_types(self):
        class ComplexClass(metaclass=StrictMeta):
            x: list[int]
            y: dict[str, int]

        self.assertTrue(hasattr(ComplexClass, '__slots__'))
        self.assertEqual(ComplexClass.__slots__, ['x', 'y'])

    def test_annotated_types(self):
        class AnnotatedClass(metaclass=StrictMeta):
            x: int  # This should have a Comment object
            y: str = "hello"  # This should have a Comment object with default value

        comment_x = get_comment(AnnotatedClass, 'x')
        self.assertIsNotNone(comment_x)
        self.assertIsNone(comment_x.default)

        comment_y = get_comment(AnnotatedClass, 'y')
        self.assertIsNotNone(comment_y)
        self.assertEqual(comment_y.default, "hello")

    def test_multiple_comments_and_descriptions(self):
        class MultiCommentClass(metaclass=StrictMeta):
            x: int  # This is a comment
            """This is a detailed description of x"""
            y: str = "hello"  # Another comment
            """Another detailed description of y"""

        comment_x = get_comment(MultiCommentClass, 'x')
        self.assertIsNotNone(comment_x)
        self.assertEqual(comment_x.comment, 'This is a comment')
        self.assertEqual(comment_x.description, 'This is a detailed description of x')

        comment_y = get_comment(MultiCommentClass, 'y')
        self.assertIsNotNone(comment_y)
        self.assertEqual(comment_y.comment, 'Another comment')
        self.assertEqual(comment_y.description, 'Another detailed description of y')

    def test_annotated_precedence(self):
        class ExampleClass(metaclass=StrictMeta):
            x: Annotated[int, Comment(
                default=20, description="#Annotated #description"
            )] = 1  # This is a default comment
            """This is a default description"""

        comment = get_comment(ExampleClass, 'x')
        self.assertIsInstance(comment, Comment)
        self.assertEqual(comment.default, 20)  # Should be the Annotated default
        self.assertEqual(comment.comment, "This is a default comment")  # Should be the Annotated comment
        self.assertEqual(comment.description, "#Annotated #description")  # Should be the Annotated description

    def test_annotated_precedence_with_source_comment(self):
        class ExampleClass(metaclass=StrictMeta):
            x: Annotated[int, Comment(
                default=20, comment="Annotated comment", description="#Annotated #description"
            )] = 10  # This has a default value and a comment
            """This is a default description"""

        comment = get_comment(ExampleClass, 'x')
        self.assertIsInstance(comment, Comment)
        self.assertEqual(comment.default, 20)  # Should be the Annotated default
        self.assertEqual(comment.comment, "Annotated comment")  # Should be the Annotated comment
        self.assertEqual(comment.description, "#Annotated #description")  # Should be the Annotated description

    def test_multiline_attribute_assignment(self):
        class MultiLineClass(metaclass=StrictMeta):
            x: int = (
                10 + 20 +
                30
            )  # This is a multiline assignment with a comment

        comment = get_comment(MultiLineClass, 'x')
        self.assertIsInstance(comment, Comment)
        self.assertEqual(comment.comment, 'This is a multiline assignment with a comment')

    def test_string_value_annotated_metadata(self):
        class StringValueClass(metaclass=StrictMeta):
            x: str = "This should not be parsed as a comment"  # This is a comment

        comment = get_comment(StringValueClass, 'x')
        self.assertIsInstance(comment, Comment)
        self.assertEqual(comment.comment, 'This is a comment')

if __name__ == '__main__':
    unittest.main()
