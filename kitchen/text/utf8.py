# -*- coding: utf-8 -*-
#
# Copyright (c) 2010 Red Hat, Inc.
# Copyright (c) 2010 Ville Skyttä
# Copyright (c) 2009 Tim Lauridsen
# Copyright (c) 2007 Marcus Kuhn
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Library General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
#
# Authors:
#   James Antill <james@fedoraproject.org>
#   Marcus Kuhn
#   Toshio Kuratomi <toshio@fedoraproject.org>
#   Tim Lauridsen
#   Ville Skyttä
#
# Portions of this are from yum/i18n.py
'''
-----
UTF-8
-----

Functions for operating on byte :class:`str` encoded as :term:`utf8`

.. note:: In many cases, it is better to convert to :class:`unicode`, operate
    on the strings, then convert back to :term:`utf8`.  :class:`unicode` type
    can handle many of these functions itself.  For those that it doesn't
    (removing control characters from length calculations, for instance) the
    code to do so with a :class:`unicode` type is often simpler.
'''

import warnings

from kitchen import _
from kitchen.text.converters import to_unicode, to_bytes
from kitchen.text.utils import byte_string_valid_encoding

# This is ported from ustr_utf8_* which I got from:
#     http://www.cl.cam.ac.uk/~mgk25/ucs/wcwidth.c
#  I've tried to leave it close to the original C (same names etc.) so that
# it is easy to read/compare both versions... James Antilles

# ----------------------------- BEG utf8 -----------------------------
# This is an implementation of wcwidth() and wcswidth() (defined in
# IEEE Std 1002.1-2001) for Unicode.
#
# http://www.opengroup.org/onlinepubs/007904975/functions/wcwidth.html
# http://www.opengroup.org/onlinepubs/007904975/functions/wcswidth.html
#
# In fixed-width output devices, Latin characters all occupy a single
# "cell" position of equal width, whereas ideographic CJK characters
# occupy two such cells. Interoperability between terminal-line
# applications and (teletype-style) character terminals using the
# UTF-8 encoding requires agreement on which character should advance
# the cursor by how many cell positions. No established formal
# standards exist at present on which Unicode character shall occupy
# how many cell positions on character terminals. These routines are
# a first attempt of defining such behavior based on simple rules
# applied to data provided by the Unicode Consortium.
#
# [...]
#
# Markus Kuhn -- 2007-05-26 (Unicode 5.0)
#
# Permission to use, copy, modify, and distribute this software
# for any purpose and without fee is hereby granted. The author
# disclaims all warranties with regard to this software.
#
# Latest version: http://www.cl.cam.ac.uk/~mgk25/ucs/wcwidth.c

def _utf8_bisearch(ucs, table):
    '''Search the auxiliary function for binary search in interval table. '''

    min = 0
    max = len(table) - 1
    if ucs < table[min][0] or ucs > table[max][1]:
        return False

    while max >= min:
        mid = (min + max) / 2
        if ucs > table[mid][1]:
            min = mid + 1
        elif ucs < table[mid][0]:
            max = mid - 1
        else:
            return True

    return False


# sorted list of non-overlapping intervals of non-spacing characters
# generated by "uniset +cat=Me +cat=Mn +cat=Cf -00AD +1160-11FF +200B c"
_combining = (
    ( 0x0300, 0x036F ), ( 0x0483, 0x0486 ), ( 0x0488, 0x0489 ),
    ( 0x0591, 0x05BD ), ( 0x05BF, 0x05BF ), ( 0x05C1, 0x05C2 ),
    ( 0x05C4, 0x05C5 ), ( 0x05C7, 0x05C7 ), ( 0x0600, 0x0603 ),
    ( 0x0610, 0x0615 ), ( 0x064B, 0x065E ), ( 0x0670, 0x0670 ),
    ( 0x06D6, 0x06E4 ), ( 0x06E7, 0x06E8 ), ( 0x06EA, 0x06ED ),
    ( 0x070F, 0x070F ), ( 0x0711, 0x0711 ), ( 0x0730, 0x074A ),
    ( 0x07A6, 0x07B0 ), ( 0x07EB, 0x07F3 ), ( 0x0901, 0x0902 ),
    ( 0x093C, 0x093C ), ( 0x0941, 0x0948 ), ( 0x094D, 0x094D ),
    ( 0x0951, 0x0954 ), ( 0x0962, 0x0963 ), ( 0x0981, 0x0981 ),
    ( 0x09BC, 0x09BC ), ( 0x09C1, 0x09C4 ), ( 0x09CD, 0x09CD ),
    ( 0x09E2, 0x09E3 ), ( 0x0A01, 0x0A02 ), ( 0x0A3C, 0x0A3C ),
    ( 0x0A41, 0x0A42 ), ( 0x0A47, 0x0A48 ), ( 0x0A4B, 0x0A4D ),
    ( 0x0A70, 0x0A71 ), ( 0x0A81, 0x0A82 ), ( 0x0ABC, 0x0ABC ),
    ( 0x0AC1, 0x0AC5 ), ( 0x0AC7, 0x0AC8 ), ( 0x0ACD, 0x0ACD ),
    ( 0x0AE2, 0x0AE3 ), ( 0x0B01, 0x0B01 ), ( 0x0B3C, 0x0B3C ),
    ( 0x0B3F, 0x0B3F ), ( 0x0B41, 0x0B43 ), ( 0x0B4D, 0x0B4D ),
    ( 0x0B56, 0x0B56 ), ( 0x0B82, 0x0B82 ), ( 0x0BC0, 0x0BC0 ),
    ( 0x0BCD, 0x0BCD ), ( 0x0C3E, 0x0C40 ), ( 0x0C46, 0x0C48 ),
    ( 0x0C4A, 0x0C4D ), ( 0x0C55, 0x0C56 ), ( 0x0CBC, 0x0CBC ),
    ( 0x0CBF, 0x0CBF ), ( 0x0CC6, 0x0CC6 ), ( 0x0CCC, 0x0CCD ),
    ( 0x0CE2, 0x0CE3 ), ( 0x0D41, 0x0D43 ), ( 0x0D4D, 0x0D4D ),
    ( 0x0DCA, 0x0DCA ), ( 0x0DD2, 0x0DD4 ), ( 0x0DD6, 0x0DD6 ),
    ( 0x0E31, 0x0E31 ), ( 0x0E34, 0x0E3A ), ( 0x0E47, 0x0E4E ),
    ( 0x0EB1, 0x0EB1 ), ( 0x0EB4, 0x0EB9 ), ( 0x0EBB, 0x0EBC ),
    ( 0x0EC8, 0x0ECD ), ( 0x0F18, 0x0F19 ), ( 0x0F35, 0x0F35 ),
    ( 0x0F37, 0x0F37 ), ( 0x0F39, 0x0F39 ), ( 0x0F71, 0x0F7E ),
    ( 0x0F80, 0x0F84 ), ( 0x0F86, 0x0F87 ), ( 0x0F90, 0x0F97 ),
    ( 0x0F99, 0x0FBC ), ( 0x0FC6, 0x0FC6 ), ( 0x102D, 0x1030 ),
    ( 0x1032, 0x1032 ), ( 0x1036, 0x1037 ), ( 0x1039, 0x1039 ),
    ( 0x1058, 0x1059 ), ( 0x1160, 0x11FF ), ( 0x135F, 0x135F ),
    ( 0x1712, 0x1714 ), ( 0x1732, 0x1734 ), ( 0x1752, 0x1753 ),
    ( 0x1772, 0x1773 ), ( 0x17B4, 0x17B5 ), ( 0x17B7, 0x17BD ),
    ( 0x17C6, 0x17C6 ), ( 0x17C9, 0x17D3 ), ( 0x17DD, 0x17DD ),
    ( 0x180B, 0x180D ), ( 0x18A9, 0x18A9 ), ( 0x1920, 0x1922 ),
    ( 0x1927, 0x1928 ), ( 0x1932, 0x1932 ), ( 0x1939, 0x193B ),
    ( 0x1A17, 0x1A18 ), ( 0x1B00, 0x1B03 ), ( 0x1B34, 0x1B34 ),
    ( 0x1B36, 0x1B3A ), ( 0x1B3C, 0x1B3C ), ( 0x1B42, 0x1B42 ),
    ( 0x1B6B, 0x1B73 ), ( 0x1DC0, 0x1DCA ), ( 0x1DFE, 0x1DFF ),
    ( 0x200B, 0x200F ), ( 0x202A, 0x202E ), ( 0x2060, 0x2063 ),
    ( 0x206A, 0x206F ), ( 0x20D0, 0x20EF ), ( 0x302A, 0x302F ),
    ( 0x3099, 0x309A ), ( 0xA806, 0xA806 ), ( 0xA80B, 0xA80B ),
    ( 0xA825, 0xA826 ), ( 0xFB1E, 0xFB1E ), ( 0xFE00, 0xFE0F ),
    ( 0xFE20, 0xFE23 ), ( 0xFEFF, 0xFEFF ), ( 0xFFF9, 0xFFFB ),
    ( 0x10A01, 0x10A03 ), ( 0x10A05, 0x10A06 ), ( 0x10A0C, 0x10A0F ),
    ( 0x10A38, 0x10A3A ), ( 0x10A3F, 0x10A3F ), ( 0x1D167, 0x1D169 ),
    ( 0x1D173, 0x1D182 ), ( 0x1D185, 0x1D18B ), ( 0x1D1AA, 0x1D1AD ),
    ( 0x1D242, 0x1D244 ), ( 0xE0001, 0xE0001 ), ( 0xE0020, 0xE007F ),
    ( 0xE0100, 0xE01EF ))

def _utf8_ucp_width(ucs):
    '''Get the textual width of a ucs character.

    :arg ucs: a single unicode code point
    :returns: :term:`textual width` of the character

    .. note: It's important to remember this is :term:`textual width` and not
        the number of characters or bytes.
    '''

    # test for 8-bit control charactersT
    if ucs == 0:
        return 0

    if ucs < 32 or (ucs >= 0x7f and ucs < 0xa0):
        return (-1)

    if _utf8_bisearch(ucs, _combining):
        return 0

    # if we arrive here, ucs is not a combining or C0/C1 control character

    return (1 + 
      (ucs >= 0x1100 and
       (ucs <= 0x115f or                     # Hangul Jamo init. consonants
        ucs == 0x2329 or ucs == 0x232a or
        (ucs >= 0x2e80 and ucs <= 0xa4cf and
         ucs != 0x303f) or                   # CJK ... Yi
        (ucs >= 0xac00 and ucs <= 0xd7a3) or # Hangul Syllables
        (ucs >= 0xf900 and ucs <= 0xfaff) or # CJK Compatibility Ideographs
        (ucs >= 0xfe10 and ucs <= 0xfe19) or # Vertical forms
        (ucs >= 0xfe30 and ucs <= 0xfe6f) or # CJK Compatibility Forms
        (ucs >= 0xff00 and ucs <= 0xff60) or # Fullwidth Forms
        (ucs >= 0xffe0 and ucs <= 0xffe6) or
        (ucs >= 0x20000 and ucs <= 0x2fffd) or
        (ucs >= 0x30000 and ucs <= 0x3fffd))))


def _utf8_iter_ints(msg):
    '''Iterate through the byte :class:`str`, returning bytes as ints

    :arg msg: byte :class:`str` to iterate through
    :rtype: int
    :returns: integer representation of the next byte
    '''
    for byte in to_bytes(msg):
        yield ord(byte)

def _utf8_iter_ucs(msg):
    '''Iterate through the string, returning codepoint and number of bytes

    :arg msg: byte :class:`str` to take codepoints from
    :rtype: tuple
    :returns: Unicode codepoint and number of bytes consumed to make that
        codepoint

    On error, this function returns None as the first entry in the tuple.  The
    second entry contains the number of bytes that were read from the string
    before determining this sequence of bytes did not form a character.
    '''
    uiter = _utf8_iter_ints(msg)
    for byte0 in uiter:
        if byte0 < 0x80:             # 0xxxxxxx
            yield (byte0, 1)
        elif (byte0 & 0xe0) == 0xc0: # 110XXXXx 10xxxxxx
            try:
                byte1 = uiter.next()
            except StopIteration:
                # Too short
                yield(None, 1)
                return
            if (((byte1 & 0xc0) != 0x80) or
                ((byte0 & 0xfe) == 0xc0)):                          # overlong?
                yield (None, 2)
                return
            yield ((((byte0 & 0x1f) << 6) | (byte1 & 0x3f)), 2)
        elif (byte0 & 0xf0) == 0xe0: # 1110XXXX 10Xxxxxx 10xxxxxx
            bytes = [byte0]
            for byte_count in range(1,3):
                try:
                    bytes.append(uiter.next())
                except StopIteration:
                    # If this is triggered, the byte sequence is too short
                    yield (None, byte_count)
                    return
            if (((bytes[1] & 0xc0) != 0x80) or ((bytes[2] & 0xc0) != 0x80) or
                ((bytes[0] == 0xe0) and ((bytes[1] & 0xe0) == 0x80)) or   # overlong?
                ((bytes[0] == 0xed) and ((bytes[1] & 0xe0) == 0xa0)) or   # surrogate?
                ((bytes[0] == 0xef) and  (bytes[1] == 0xbf) and
                 ((bytes[2] & 0xfe) == 0xbe))): # U+FFFE or U+FFFF?
                yield (None, 3)
                return
            yield ((((bytes[0] & 0x0f) << 12) | ((bytes[1] & 0x3f) << 6) |
                   (bytes[2] & 0x3f)), 3)
        elif (byte0 & 0xf8) == 0xf0: # 11110XXX 10XXxxxx 10xxxxxx 10xxxxxx
            bytes = [byte0]
            for byte_count in range(1,4):
                try:
                    bytes.append(uiter.next())
                except StopIteration:
                    # If this is triggered, the byte sequence is too short
                    yield (None, byte_count)
                    return
            if (((bytes[1] & 0xc0) != 0x80) or
                ((bytes[2] & 0xc0) != 0x80) or
                ((bytes[3] & 0xc0) != 0x80) or
                ((bytes[0] == 0xf0) and ((bytes[1] & 0xf0) == 0x80)) or # overlong?
                ((bytes[0] == 0xf4) and (bytes[1] > 0x8f)) or           # > U+10FFFF?
                (bytes[0] > 0xf4)):                                  # > U+10FFFF?
                yield (None, 4)
                return

            yield ((((bytes[0] & 0x07) << 18) | ((bytes[1] & 0x3f) << 12) |
                    ((bytes[2] & 0x3f) <<  6) |  (bytes[3] & 0x3f)), 4)
        else:
            yield (None, 1)
            return

def utf8_width(msg):
    '''Get the textual width of a utf8 string.

    :arg msg: utf8 encoded byte string to get the width of
    :returns: Textual width.  This is the amount of space that the string will
        consume on a monospace display.  It's measured in the number of ASCII
        characters it would take to fill the equivalent amount of space.  This
        is **not** the number of glyphs that are in the string.

    .. note:: This function can be wrong sometimes because Unicode does not
        specify a strict width value for all of the codepoints.  In particular,
        we've found that some Tamil characters take up to 4 character cells
        but are represented with a lesser amount.
    '''
    ret = 0
    for (ucs, bytes) in _utf8_iter_ucs(msg):
        if ucs is None:
            ret += bytes # Ugly ... should not feed bad utf8
        else:
            ret += _utf8_ucp_width(ucs)
    return ret

def utf8_width_chop(msg, chop=None):
    '''Return the textual width of a utf8 string, chopping it to a specified
    value.

    :arg msg: String to chop
    :kwarg chop: Chop the string if it exceeds this textual width.
    :returns: string of the requested length

    This is what you want to use instead of %.*s, as it does the "right" thing
    with regard to utf-8 sequences. Eg::

        %.*s" % (10, msg)
            <= becomes =>
        %s" % (utf8_width_chop(msg, 10))


    .. note:: If you pass a unicode string into this function, you will get
        a unicode string back.  But the string will have been formatted with
        utf8 encoding in mind.
    '''
    if chop is None or utf8_width(msg) <= chop:
        return utf8_width(msg), msg

    ret = 0
    passed_unicode = isinstance(msg, unicode)
    msg_bytes = 0
    msg = to_bytes(msg)
    for (ucs, bytes) in _utf8_iter_ucs(msg):
        if ucs is None:
            width = bytes # Ugly ... should not feed non-utf8 bytes
        else:
            width = _utf8_ucp_width(ucs)

        if chop is not None and (ret + width) > chop:
            msg = msg[:msg_bytes]
            break
        ret += width
        msg_bytes += bytes

    if passed_unicode:
        msg = to_unicode(msg)

    return ret, msg

def utf8_width_fill(msg, fill, chop=None, left=True, prefix='', suffix=''):
    '''Expand a utf8 msg to a specified "width" or chop to same.

    :arg msg: byte string to format
    :arg fill: pad string until the textual width is this long
    :kwarg chop: before doing anything else, chop the string to this length.
        Default: Don't chop the string at all
    :kwarg left: If True (default) left justify the string and put the padding
        on the right.  If False, pad on the left side.
    :kwarg prefix: Attach this string before the field we're filling
    :kwarg suffix: Append this string to the end of the field we're filling

    Expansion can be left or right. This is what you want to use instead of
    %*.*s, as it does the "right" thing with regard to utf-8 sequences.
    prefix and suffix should be used for "invisible" bytes, like
    highlighting.  Eg::


        %-*.*s" % (10, 20, msg)
            <= becomes =>
        %s" % (utf8_width_fill(msg, 10, 20)).

        %20.10s" % (msg)
            <= becomes =>
        %s" % (utf8_width_fill(msg, 20, 10, left=False)).

        %s%.10s%s" % (prefix, msg, suffix)
            <= becomes =>
        %s" % (utf8_width_fill(msg, 0, 10, prefix=prefix, suffix=suffix)).
    '''
    passed_unicode = isinstance(msg, unicode)
    msg = to_bytes(msg)
    prefix = to_bytes(prefix)
    suffix = to_bytes(suffix)
    width, msg = utf8_width_chop(msg, chop)

    if width >= fill:
        if prefix or suffix:
            msg = ''.join([prefix, msg, suffix])
    else:
        extra = " " * (fill - width)
        if left:
            msg = ''.join([prefix, msg, suffix, extra])
        else:
            msg = ''.join([extra, prefix, msg, suffix])

    if passed_unicode:
        return to_unicode(msg)

    return msg

def _utf8_width_le(width, *args):
    '''Minor speed hack, we often want to know "does X fit in Y". It takes
    "a while" to work out a utf8_width() (see above), and we know that a utf8
    character is always <= byte. So given::

        assert bytes >= characters
        characters <= width?

        ...we can change to:

        bytes <= width or characters <= width

        ...and bytes are much faster.
    '''
    # This assumes that all args. are utf8.
    ret = 0
    for arg in args:
        ret += len(arg)
    if ret <= width:
        return True
    ret = 0
    for arg in args:
        ret += utf8_width(arg)
    return ret <= width

def utf8_valid(msg):
    '''Deprecated.  Detect if a string is valid utf8.

    Use :func:`kitchen.text.utils.byte_string_valid_encoding` instead.

    '''
    warnings.warn(_('Deprecated.  Use'
            ' kitchen.text.utils.byte_string_valid_encoding(msg) instead'),
            DeprecationWarning, stacklevel=2)
    return byte_string_valid_encoding(msg)

def utf8_text_wrap(text, width=70, initial_indent='', subsequent_indent=''):
    '''Works like we want textwrap.wrap() to work, uses utf-8 data and
    doesn't screw up lists/blocks/etc.

    :arg text: string to wrap
    :kwarg width: width at which to wrap.  Default 70
    :kwarg initial_indent: string to use to indent the first line.  Default,
        do not indent.
    :kwarg subsequent_indent: string to use to wrap subsequent lines.  Default
        do not indent
    :returns: list of lines that have been text wrapped and indented.
    '''
    # Tested with:
    # yum info robodoc gpicview php-pear-Net-Socket wmctrl ustr moreutils
    #          mediawiki-HNP ocspd insight yum mousepad
    # ...at 120, 80 and 40 chars.
    # Also, notable among lots of others, searching for "\n  ":
    #   exim-clamav, jpackage-utils, tcldom, synaptics, "quake3",
    #   perl-Class-Container, ez-ipupdate, perl-Net-XMPP, "kipi-plugins",
    #   perl-Apache-DBI, netcdf, python-configobj, "translate-toolkit", alpine,
    #   "udunits", "conntrack-tools"
    #
    # Note that, we "fail" on:
    #   alsa-plugins-jack, setools*, dblatex, uisp, "perl-Getopt-GUI-Long",
    #   suitesparse, "synce-serial", writer2latex, xenwatch, ltsp-utils

    passed_unicode = isinstance(text, unicode)

    def _indent_at_beg(line):
        count = 0
        byte = 'X'
        for byte in line:
            if byte != ' ':
                break
            count += 1
        if byte not in ("-", "*", ".", "o", '\xe2'):
            return count, 0
        list_chr = utf8_width_chop(line[count:], 1)[1]
        if list_chr in ("-", "*", ".", "o",
                        "\xe2\x80\xa2", "\xe2\x80\xa3", "\xe2\x88\x98"):
            nxt = _indent_at_beg(line[count+len(list_chr):])
            nxt = nxt[1] or nxt[0]
            if nxt:
                return count, count + 1 + nxt
        return count, 0

    initial_indent = to_bytes(initial_indent)
    subsequent_indent = to_bytes(subsequent_indent)

    text = to_bytes(text).rstrip('\n')
    lines = text.replace('\t', ' ' * 8).split('\n')

    ret = []
    indent = initial_indent
    wrap_last = False
    csab = 0
    cspc_indent = 0
    for line in lines:
        line = line.rstrip(' ')
        (lsab, lspc_indent) = (csab, cspc_indent)
        (csab, cspc_indent) = _indent_at_beg(line)
        force_nl = False # We want to stop wrapping under "certain" conditions:
        if wrap_last and cspc_indent:      # if line starts a list or
            force_nl = True
        if wrap_last and csab == len(line):# is empty line
            force_nl = True
        if wrap_last and not lspc_indent:  # if line doesn't continue a list and
            if csab >= 4 and csab != lsab: # is "block indented"
                force_nl = True
        if force_nl:
            ret.append(indent.rstrip(' '))
            indent = subsequent_indent
            wrap_last = False
        if csab == len(line): # empty line, remove spaces to make it easier.
            line = ''
        if wrap_last:
            line = line.lstrip(' ')
            cspc_indent = lspc_indent

        if _utf8_width_le(width, indent, line):
            wrap_last = False
            ret.append(indent + line)
            indent = subsequent_indent
            continue

        wrap_last = True
        words = line.split(' ')
        line = indent
        spcs = cspc_indent
        if not spcs and csab >= 4:
            spcs = csab
        for word in words:
            if (not _utf8_width_le(width, line, word) and
                utf8_width(line) > utf8_width(subsequent_indent)):
                ret.append(line.rstrip(' '))
                line = subsequent_indent + ' ' * spcs
            line += word
            line += ' '
        indent = line.rstrip(' ') + ' '
    if wrap_last:
        ret.append(indent.rstrip(' '))

    if passed_unicode:
        return map(to_unicode, ret)
    return ret

def utf8_text_fill(text, *args, **kwargs):
    '''Works like we want textwrap.fill() to work, uses utf-8 data and
        doesn't screw up lists/blocks/etc.

    :arg text: string to process
    :returns: string with each line separated by a newline.

    .. seealso::
        :func:`utf8_text_wrap`
            for other options that you can give this command.

    This function is a light wrapper around :func:`utf8_text_wrap`.  Where
    that function returns a list of lines, this function returns one string
    with each line separated by a newline.
    '''
    return '\n'.join(utf8_text_wrap(text, *args, **kwargs))

# ----------------------------- END utf8 -----------------------------

__all__ = ('utf8_text_fill', 'utf8_text_wrap', 'utf8_valid',
        'utf8_width', 'utf8_width_chop', 'utf8_width_fill',)
