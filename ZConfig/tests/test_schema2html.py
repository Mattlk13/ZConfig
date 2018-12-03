##############################################################################
#
# Copyright (c) 2017, 2018 Zope Foundation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
from __future__ import absolute_import

import contextlib
import sys
import textwrap
import unittest

import docutils
import docutils.utils
import docutils.frontend
import docutils.parsers.rst
import docutils.parsers.rst.directives


try:
    # Note that we're purposely using the old
    # StringIO object on Python 2 because it auto-converts
    # Unicode to str, which io.BytesIO and io.StringIO don't
    # but which normal printing to default sys.stdout *does*
    from cStringIO import StringIO
except ImportError:
    from ZConfig._compat import NStringIO as StringIO


from ZConfig import schema2html

from ZConfig.sphinx import SchemaToRstDirective
from ZConfig.sphinx import RstSchemaFormatter

from .support import input_file
from .support import with_stdin_from_input_file


docutils.parsers.rst.directives.register_directive("zconfig",
                                                   SchemaToRstDirective)


@contextlib.contextmanager
def stdout_replaced(buf):
    old_stdout = sys.stdout
    sys.stdout = buf
    try:
        yield
    finally:
        sys.stdout = old_stdout


def run_transform(*args):
    if '--out' not in args and '-o' not in args:
        buf = StringIO()
        with stdout_replaced(buf):
            schema2html.main(args)
        return buf
    return schema2html.main(args)  # pragma: no cover


if schema2html.RstSchemaPrinter:
    def run_transform_rst(*args):
        args += ('--format', 'xml')
        return run_transform(*args)
else:
    def run_transform_rst(*args):
        pass


class TestSchema2HTML(unittest.TestCase):

    def test_schema_only(self):
        res = run_transform(input_file('simple.xml'))
        self.assertIn('</html>', res.getvalue())
        run_transform_rst(input_file('simple.xml'))

    @with_stdin_from_input_file('simple.xml')
    def test_schema_only_redirect(self):
        res = run_transform("-")
        self.assertIn('</html>', res.getvalue())

    def test_cover_all_schemas(self):
        for name in ('base-datatype1.xml',
                     'base-datatype2.xml',
                     'base-keytype1.xml',
                     'base-keytype2.xml',
                     'base.xml',
                     'library.xml',
                     'simplesections.xml',):
            res = run_transform(input_file(name))
            self.assertIn('</html>', res.getvalue())
            run_transform_rst(input_file(name))

    def test_html_section_example(self):
        name = 'simplesections.xml'
        res = run_transform(input_file(name))
        out = res.getvalue()
        self.assertIn('Section Example', out)
        self.assertIn('Multisection Example', out)

    def test_rst_section_example(self):
        name = 'simplesections.xml'
        res = run_transform_rst(input_file(name))
        out = res.getvalue()
        self.assertIn('Section Example', out)
        self.assertIn('Multisection Example', out)

    def test_cover_logging_components(self):
        res = run_transform('--package', 'ZConfig.components.logger')
        self.assertIn('eventlog', res.getvalue())
        run_transform_rst('--package', 'ZConfig.components.logger')


class TestRst(unittest.TestCase):

    def _parse(self, text):
        document = docutils.utils.new_document(
            "Schema",
            settings=docutils.frontend.OptionParser(
                components=(docutils.parsers.rst.Parser,)
            ).get_default_values())

        parser = docutils.parsers.rst.Parser()
        text = textwrap.dedent(text)
        parser.parse(text, document)
        return document

    def test_parse_package(self):
        text = """
        Document
        ========
        .. zconfig:: ZConfig.components.logger

        """
        document = self._parse(text)
        doc_text = document.astext()
        # Check that it produced output
        self.assertIn("SMTPHandler", doc_text)
        self.assertIn("Example:", doc_text)

    def test_parse_package_file(self):
        text = """
        Document
        ========
        .. zconfig:: ZConfig.components.logger
            :file: base-logger.xml

        """
        document = self._parse(text)
        doc_text = document.astext()
        # Check that it produced output, limited to
        # just that one file.
        self.assertNotIn("SMTPHandler", doc_text)
        self.assertIn("base-logger", doc_text)
        self.assertIn("Base definition", doc_text)
        self.assertIn("Example:", doc_text)

    def test_parse_package_limited_names(self):
        text = """
        Document
        ========
        .. zconfig:: ZConfig.components.logger
            :members: syslog logfile
        """
        document = self._parse(text)
        doc_text = document.astext()

        # Check that it produced output, limited to
        # just that one part of the tree
        self.assertNotIn("SMTPHandler", doc_text)
        self.assertIn("syslog", doc_text)
        self.assertIn("SyslogHandlerFactory", doc_text)
        self.assertIn("FileHandlerFactory", doc_text)

    def test_parse_package_excluded_names(self):
        text = """
        Document
        ========
        .. zconfig:: ZConfig.components.logger
            :members: ZConfig.logger.base-logger
            :excluded-members: ZConfig.logger.handler
        """
        document = self._parse(text)
        doc_text = document.astext()

        # Check that it produced output, limited to
        # just that one part of the tree
        # In this case, the root base-logger, but the handlers subtree
        # was excluded.
        self.assertIn("zconfig.logger.base-logger", doc_text)
        self.assertNotIn("SMTPHandler", doc_text)
        self.assertNotIn("syslog", doc_text)
        self.assertNotIn("SyslogHandlerFactory", doc_text)
        self.assertNotIn("FileHandlerFactory", doc_text)

    def test_description_dedent(self):
        text = """No leading whitespace on this line.
        But this line has whitespace.
        As does this one.
        """
        written = []

        class FUT(RstSchemaFormatter):

            def __init__(self):
                pass

            def _parsed(self, text, _):
                return text

            def write(self, *texts):
                written.extend(texts)

        fut = FUT()
        fut.description(text)

        dedented = ("No leading whitespace on this line.\n"
                    "But this line has whitespace.\n"
                    "As does this one.\n")

        self.assertEqual(written[0], dedented)


def test_suite():
    return unittest.defaultTestLoader.loadTestsFromName(__name__)


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')