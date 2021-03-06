# -*- coding: utf-8 -*-

from __future__ import absolute_import

from collections import defaultdict
from email.header import decode_header
from re import findall

from .compat import text_type, encoded_padding


class Callback(object):
    """Base class for callbacks."""

    # DEFINITIONS
    GET_ALL_ATTACHMENTS = 255 # get all attachments from eMail
    GET_PDF_ATTACHMENTS = 1 # get only PDFs
    GET_MSOFFICE_ATTACHMENTS = 2 # get only Word documents
    GET_IMAGE_ATTACHMENTS = 4 # get only images

    def __init__(self, message, rules):
        self.matches = defaultdict(list)
        self.message = message
        self.rules = rules

    def check_rules(self, rules=None):
        """Does this message conform to the all the rules provided?

        For each item in the rules dictionnary (item, [regexp1, regexp2...]),
        call ``self.check_item``.

        """
        if rules is None:
            rules = self.rules

        if not rules:  # if no (or empty) rules, it's a catchall callback
            return True

        rules_tests = [self.check_item(item, regexps)
                       for item, regexps in rules.items()]

        return all(rules_tests)  # True only if at least one value is

    def check_item(self, item, regexps, message=None):
        """Search the email's item using the given regular expressions.

        Item is one of subject, from, to, cc, body.

        Store the result of searching the item with the regular expressions in
        self.matches[item]. If the search doesn't match anything, this will
        result in a None, otherwise it'll be a ``re.MatchObject``.

        """
        if message is None:
            message = self.message

        if item not in message and item != 'body':  # bad item, not found
            return None

        # if item is not in header, then item == 'body'
        if item == 'body':
            value = self.get_email_body(message)
        else:
            value = message[item]
            # decode header (might be encoded as latin-1, utf-8...
            value = encoded_padding.join(
                chunk.decode(encoding or 'ASCII')
                if not isinstance(chunk, text_type) else chunk
                for chunk, encoding in decode_header(value))

        for regexp in regexps:  # store all captures for easy access
            self.matches[item] += findall(regexp, value)

        return any(self.matches[item])

    def get_email_body(self, message=None):
        """Return the message text body.

        Return the first 'text/plain' part of the email.Message that doesn't
        have a filename.

        """
        if message is None:
            message = self.message

        if not hasattr(message, 'walk'):  # not an email.Message instance?
            return None

        for part in message.walk():
            content_type = part.get_content_type()
            filename = part.get_filename()
            if content_type == 'text/plain' and filename is None:
                # text body of the mail, not an attachment
                encoding = part.get_content_charset() or 'ASCII'
                content = part.get_payload()
                if not isinstance(content, text_type):
                    content = part.get_payload(decode=True).decode(encoding)
                return content

        return ''

    def get_attachments(self, message=None, documents=GET_ALL_ATTACHMENTS):
        """Return a list of attachments.

        Return all attached files within a list of 2-tuples filename and
        content of the attachment to be stored locally.

        """
        if message is None:
            message = self.message

        if not hasattr(message, 'walk'):  # not an email.Message instance?
            return None

        content = []
        for part in message.walk():
            content_type = part.get_content_type()
            filename = part.get_filename()

            # check for desired file types
            if documents == self.GET_ALL_ATTACHMENTS:

                # get any file
                if filename is not None:
                    content = content + [(filename, part.get_payload(decode=True))]

            else:

                # PDF file type
                if documents & self.GET_PDF_ATTACHMENTS and content_type == 'application/pdf' and filename is not None:
                    content = content + [(filename,part.get_payload(decode=True))]

                # MS OFFICE file types
                if documents & self.GET_MSOFFICE_ATTACHMENTS and content_type.find('application/ms') > -1 and filename is not None:
                    content = content + [(filename,part.get_payload(decode=True))]

                # IMAGE file types
                if documents & self.GET_IMAGE_ATTACHMENTS and content_type.find('image') > -1 and filename is not None:
                    content = content + [(filename,part.get_payload(decode=True))]

        return content

    def trigger(self):
        """Called when a mail matching the registered rules is received."""
        raise NotImplementedError("Must be implemented in a child class.")
