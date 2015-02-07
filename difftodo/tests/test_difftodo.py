# Copyright (c) 2009 Jonathan M. Lange <jml@mumak.net>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


"""Tests for extracting TODOs from comments in Python source code."""


from bzrlib import patches
from bzrlib.tests import TestCase

from pygments.token import Token

from difftodo import Comment, Todo, todo_from_comment
from difftodo._difftodo import (
    get_comments,
    get_new_content,
    lex_diff,
    parse_diff,
)


class TestLexDiffs(TestCase):
    """Test our ability to lex diffs."""

    def lex_diff(self, text):
        return list(lex_diff(text))

    def test_empty(self):
        self.assertEqual([(Token.Text, u'\n')], self.lex_diff(''))

    def test_simple_bzr_diff(self):
        diff = ("""\
=== modified file 'a'
--- a	2009-01-17 05:07:59 +0000
+++ a	2009-01-17 05:08:20 +0000
@@ -9,4 +9,5 @@
         # Line 1
         # Line 2
         # Line 3
+        # Line 4
         pass
""")
        expected = [
            (Token.Generic.Heading, u"=== modified file 'a'\n"),
            (Token.Generic.Deleted, u'--- a\t2009-01-17 05:07:59 +0000\n'),
            (Token.Generic.Inserted, u'+++ a\t2009-01-17 05:08:20 +0000\n'),
            (Token.Generic.Subheading, u'@@ -9,4 +9,5 @@\n'),
            (Token.Text, u'         # Line 1\n         # Line 2\n         # Line 3\n'),
            (Token.Generic.Inserted, u'+        # Line 4\n'),
            (Token.Text, u'         pass\n')]
        self.assertEqual(expected, self.lex_diff(diff))

    def test_simple_git_diff(self):
        diff = ('''\
diff --git a/.gitignore b/.gitignore
index 241973c..9bbeb13 100644
--- a/.gitignore
+++ b/.gitignore
@@ -1,3 +1,4 @@
+.env/
 *.pyc
 /_trial_temp/
 /difftodo.egg-info/
diff --git a/difftodo/_difftodo.py b/difftodo/_difftodo.py
index 1618681..cda4adb 100644
--- a/difftodo/_difftodo.py
+++ b/difftodo/_difftodo.py
@@ -26,6 +26,10 @@ from bzrlib import patches
 
 from extensions import filter_none
 
+# A comment
+
+# XXX: Use Pygments to do all of our lexing for us.
+
 
 class Comment(object):
     """A comment block in a Python source file."""
''')
        expected = [
            (Token.Generic.Heading,
             u'diff --git a/.gitignore b/.gitignore\nindex 241973c..9bbeb13 100644\n'),
            (Token.Generic.Deleted, u'--- a/.gitignore\n'),
            (Token.Generic.Inserted, u'+++ b/.gitignore\n'),
            (Token.Generic.Subheading, u'@@ -1,3 +1,4 @@\n'),
            (Token.Generic.Inserted, u'+.env/\n'),
            (Token.Text, u' *.pyc\n /_trial_temp/\n /difftodo.egg-info/\n'),
            (Token.Generic.Heading,
             u'diff --git a/difftodo/_difftodo.py b/difftodo/_difftodo.py\nindex '
             '1618681..cda4adb 100644\n'),
            (Token.Generic.Deleted, u'--- a/difftodo/_difftodo.py\n'),
            (Token.Generic.Inserted, u'+++ b/difftodo/_difftodo.py\n'),
            (Token.Generic.Subheading,
             u'@@ -26,6 +26,10 @@ from bzrlib import patches\n'),
            (Token.Text, u' \n from extensions import filter_none\n \n'),
            (Token.Generic.Inserted,
             u'+# A comment\n+\n+# XXX: Use Pygments to do all of our lexing for us.\n+\n'),
            (Token.Text,
             u' \n class Comment(object):\n     """A comment block in a Python source file."""\n')
        ]
        self.assertEqual(expected, self.lex_diff(diff))


class TestParseDiff(TestCase):
    """Given a lexed diff, parse it."""

    def test_git_diff(self):
        tokens = [
            (Token.Generic.Heading,
             u'diff --git a/.gitignore b/.gitignore\nindex 241973c..9bbeb13 100644\n'),
            (Token.Generic.Deleted, u'--- a/.gitignore\n'),
            (Token.Generic.Inserted, u'+++ b/.gitignore\n'),
            (Token.Generic.Subheading, u'@@ -1,3 +1,4 @@\n'),
            (Token.Generic.Inserted, u'+.env/\n'),
            (Token.Text, u' *.pyc\n /_trial_temp/\n /difftodo.egg-info/\n'),
            (Token.Generic.Heading,
             u'diff --git a/difftodo/_difftodo.py b/difftodo/_difftodo.py\nindex '
             '1618681..cda4adb 100644\n'),
            (Token.Generic.Deleted, u'--- a/difftodo/_difftodo.py\n'),
            (Token.Generic.Inserted, u'+++ b/difftodo/_difftodo.py\n'),
            (Token.Generic.Subheading,
             u'@@ -26,6 +26,10 @@ from bzrlib import patches\n'),
            (Token.Text, u' \n from extensions import filter_none\n \n'),
            (Token.Generic.Inserted,
             u'+# A comment\n+\n+# XXX: Use Pygments to do all of our lexing for us.\n+\n'),
            (Token.Text,
             u' \n class Comment(object):\n     """A comment block in a Python source file."""\n')
        ]
        # Got two choices:
        # - infer the contents of the new file from the diff
        # - given the new content, load it from the file on disk
        expected = [
            ('.gitignore',
             [(1, [
                 (Token.Generic.Inserted, ['.env/']),
                 (Token.Text, [
                     '*.pyc',
                     '/_trial_temp/',
                     '/difftodo.egg-info/'
                 ]),
             ])]),
            ('difftodo/_difftodo.py',
             # XXX: Throws away extra diff chunk header info
             [(26, [
                 (Token.Text, [
                     '',
                     'from extensions import filter_none',
                     '',
                 ]),
                 (Token.Generic.Inserted, [
                     '# A comment',
                     '',
                     '# XXX: Use Pygments to do all of our lexing for us.',
                     '',
                 ]),
                 (Token.Text, [
                     '',
                     'class Comment(object):',
                     '    """A comment block in a Python source file."""',
                 ]),
             ])]),
        ]
        self.assertEqual(expected, list(parse_diff(tokens)))

    def test_bzr_diff(self):
        tokens = [
            (Token.Generic.Heading, u"=== modified file 'a'\n"),
            (Token.Generic.Deleted, u'--- a\t2009-01-17 05:07:59 +0000\n'),
            (Token.Generic.Inserted, u'+++ a\t2009-01-17 05:08:20 +0000\n'),
            (Token.Generic.Subheading, u'@@ -9,4 +9,5 @@\n'),
            (Token.Text, u'         # Line 1\n         # Line 2\n         # Line 3\n'),
            (Token.Generic.Inserted, u'+        # Line 4\n'),
            (Token.Text, u'         pass\n')]
        expected = [
            ('a',
             [(9, [
                 (Token.Text, [
                     '        # Line 1',
                     '        # Line 2',
                     '        # Line 3',
                 ]),
                 (Token.Generic.Inserted, [
                     '        # Line 4',
                 ]),
                 (Token.Text, [
                     '        pass'
                 ]),
             ]),
          ]),
        ]
        self.assertEqual(expected, list(parse_diff(tokens)))


class TestNewContent(TestCase):

    def test_strip_files_with_only_deletes(self):
        parsed = [
            (u'a',
             [(6,
               [(Token.Text,
                 [u'class TestBar(unittest.TestCase):',
                  u'',
                  u'    def test_bar(self):']),
                (Token.Generic.Deleted,
                 [u'        # This test is going to be awesome.']),
                (Token.Text, [u'pass'])])]),
        ]
        expected = []
        self.assertEqual(expected, list(get_new_content(parsed)))

    def test_strip_chunks_with_only_deletes(self):
        parsed = [
            (u'a',
             [(6,
               [(Token.Text,
                 [u'class TestBar(unittest.TestCase):',
                  u'',
                  u'    def test_bar(self):']),
                (Token.Generic.Deleted,
                 [u'        # This test is going to be awesome.']),
                (Token.Text, [u'pass'])]),
              (20,
               [(Token.Text,
                 [u'class TestFoo(unittest.TestCase):',
                  u'',
                  u'    def test_foo(self):']),
                (Token.Generic.Inserted,
                 [u'        # This is the real awesome.']),
                (Token.Text, [u'pass'])])
          ]),
        ]
        expected = [
            (u'a',
             [(20,
               [u'class TestFoo(unittest.TestCase):',
                u'',
                u'    def test_foo(self):',
                u'        # This is the real awesome.',
                u'pass'])])]
        self.assertEqual(expected, list(get_new_content(parsed)))

    def test_strip_deletes_within_chunk(self):
        parsed = [
            (u'a',
             [(6,
               [(Token.Text,
                 [u'class TestBar(unittest.TestCase):',
                  u'',
                  u'    def test_bar(self):']),
                (Token.Generic.Deleted,
                 [u'        # This test is going to be awesome.']),
                (Token.Generic.Inserted,
                 [u'        # This test is awesome.']),
                (Token.Text, [u'pass'])]),
          ]),
        ]
        expected = [
            (u'a',
             [(6,
               [u'class TestBar(unittest.TestCase):',
                u'',
                u'    def test_bar(self):',
                u'        # This test is awesome.',
                u'pass'])])]
        self.assertEqual(expected, list(get_new_content(parsed)))


class TestGetComments(TestCase):

    def test_empty_code(self):
        code = ''
        self.assertEqual([], list(get_comments('foo.py', code)))

    def test_only_comments(self):
        code = """
        # This is a comment.
        """
        self.assertEqual(['# This is a comment.'], list(get_comments('foo.py', code)))

    def test_non_python_comments(self):
        code = "/* This is also a comment */"
        self.assertEqual(
            ['/* This is also a comment */'], list(get_comments('foo.c', code)))

    # XXX: How are we going to combine multi-line comments from Python without combining multiple single comments from C?

class TestComment(TestCase):
    """Tests for the `Comment` class."""

    def test_construction(self):
        comment = Comment("foo.py", 42, ["# hahaha\n", "# hohoho\n"])
        self.assertEqual("foo.py", comment.filename)
        self.assertEqual(42, comment.start_line)
        self.assertEqual(["# hahaha\n", "# hohoho\n"], comment.raw_lines)

    def test_equality(self):
        comment1 = Comment("foo.py", 42, ["# hahaha\n", "# hohoho\n"])
        comment2 = Comment("foo.py", 42, ["# hahaha\n", "# hohoho\n"])
        self.assertEqual(comment1, comment2)
        self.assertEqual(comment2, comment1)

    def test_trailing_filename_discarded(self):
        comment = Comment("a\t2009-01-17 02:47:31 +0000", 42, ["# foo"])
        self.assertEqual('a', comment.filename)

    def test_lines(self):
        # The text attribute gets rid of the hash character and just has the
        # text.
        comment = Comment("foo.py", 42, ["# hahaha\n", "# hohoho  \n"])
        self.assertEqual(["hahaha", "hohoho"], list(comment.lines))

    def test_lines_disregards_pre_comment_indentation(self):
        comment = Comment("foo.py", 42, ["# hahaha\n", "    # hohoho  \n"])
        self.assertEqual(["hahaha", "hohoho"], list(comment.lines))

    def test_lines_preserves_post_comment_indentation(self):
        comment = Comment("foo.py", 42, ["# hahaha\n", "#     hohoho  \n"])
        self.assertEqual(["hahaha","    hohoho"], list(comment.lines))

    def test_str(self):
        comment = Comment("foo.py", 42, ["# hahaha\n", "# hohoho\n"])
        self.assertEqual(
            ("foo.py:42:\n"
             "  hahaha\n"
             "  hohoho\n"), str(comment))

    def test_append(self):
        comment = Comment("foo.py", 42, ["# hahaha\n"])
        comment.append("# hohoho\n")
        self.assertEqual(["# hahaha\n", "# hohoho\n"], comment.raw_lines)

    def test_contains(self):
        # We can look for text in comments.
        comment = Comment("foo.py", 42, ["# hahaha\n"])
        self.assertTrue("ha" in comment)
        self.assertTrue("# h" not in comment)


class TestTodo(TestCase):

    def test_constructor(self):
        todo = Todo('filename.py', 32, ['XXX: hello', 'bar'])
        self.assertEqual('filename.py', todo.filename)
        self.assertEqual(32, todo.start_line)
        self.assertEqual(['XXX: hello', 'bar'], todo.lines)

    def test_str(self):
        todo = Todo('filename.py', 32, ['XXX: hello', 'bar'])
        self.assertEqual('filename.py:32:\n  XXX: hello\n  bar\n', str(todo))

    def test_equality(self):
        todo1 = Todo('filename.py', 32, ['XXX: hello', 'bar'])
        todo2 = Todo('filename.py', 32, ['XXX: hello', 'bar'])
        self.assertEqual(todo2, todo1)
        self.assertEqual(todo1, todo2)


class TestTodoFromComment(TestCase):

    def makeComment(self, comment_text):
        return Comment(
            'arbitrary.py', 1, ['# ' + line for line in comment_text])

    def test_no_todos(self):
        comment = self.makeComment(['hello australia!'])
        todos = list(todo_from_comment(comment, ['XXX', 'TODO']))
        self.assertEqual([], todos)

    def test_one_todo(self):
        comment = self.makeComment(['XXX: hello australia!'])
        todos = list(todo_from_comment(comment, ['XXX', 'TODO']))
        self.assertEqual(
            [Todo(
                comment.filename, comment.start_line,
                ['XXX: hello australia!'])], todos)

    def test_one_todo_embedded(self):
        comment = self.makeComment([
            'first line',
            'XXX: hello australia!',
            'second line'])
        todos = list(todo_from_comment(comment, ['XXX', 'TODO']))
        # XXX: Maybe we want to change this so that the todo starts at the
        # XXX or TODO.
        self.assertEqual(
            [Todo(
                comment.filename, comment.start_line + 1,
                ['XXX: hello australia!', 'second line'])],
            todos)

    def test_two_todos(self):
        comment = self.makeComment([
            'XXX: first line',
            'TODO: hello australia!',
            'second line'])
        todos = list(todo_from_comment(comment, ['XXX', 'TODO']))
        # XXX: Maybe we want to change this so that the todo starts at the
        # XXX or TODO.
        self.assertEqual(
            [Todo(comment.filename, comment.start_line, ['XXX: first line']),
             Todo(comment.filename, comment.start_line + 1,
                  ['TODO: hello australia!', 'second line']),], todos)