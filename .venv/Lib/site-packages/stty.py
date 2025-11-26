# stty.py - A Python library that works like stty(1).
# Copyright (C) 2025 Soumendra Ganguly

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import sys
import os
import termios
import copy
import json

__all__ = [
    "Stty", "TCSANOW", "TCSADRAIN", "TCSAFLUSH",
    "settings", "settings_help_str", "settings_help"
]

# These are the "action" constants for termios.tcsetattr()
# and are the only values accepted by the "when" named
# argument of Stty.tofd().
TCSANOW = termios.TCSANOW
TCSADRAIN = termios.TCSADRAIN
TCSAFLUSH = termios.TCSAFLUSH

if not hasattr(termios, "_POSIX_VDISABLE"):
    # This is not desirable, but I have added
    # _POSIX_VDISABLE to the termios module in Python 3.13:
    # https://github.com/python/cpython/pull/114985
    #
    # I will remove this after sometime.
    termios._POSIX_VDISABLE = 0x00

def cc_str_to_bytes(s):
    """Convert string to bytes where input string is
    the "string" in "<control>-character string" under
    "Special Control Character Assignments" in the POSIX
    manpage of stty(1).
    """

    # 's' is of type 'str'

    if len(s) == 1:
        return bytes([ord(s)])

    if s in ["^-", "undef"]:
        return bytes([termios._POSIX_VDISABLE])

    if len(s) == 2 and s[0] == "^":
        if s[1] == "?":
            return bytes([0x7f]) # DEL

        if s[1].isalpha() or s[1] in "[\\]^_":
            return bytes([ord(s[1]) & 0x1f])

    return None


def cc_bytes_to_str(b):
    """Convert bytes to string where output string is
    the "string" in "<control>-character string" under
    "Special Control Character Assignments" in the POSIX
    manpage of stty(1).
    """

    # 'b' is of type 'bytes'

    if len(b) != 1:
        return None

    byte = b[0]

    if byte == termios._POSIX_VDISABLE:
        return "undef"

    if 0x20 <= byte <= 0x7e:
        return chr(byte)

    if byte == 0x7f: # DEL
        return "^?"

    if 0x01 <= byte <= 0x1f:
        c = chr(byte + 0x40)
        if c.islower():
            c = c.upper()
        return f"^{c}"

    return None


# Indices for termios attribute list.
_IFLAG = 0
_OFLAG = 1
_CFLAG = 2
_LFLAG = 3
_ISPEED = 4
_OSPEED = 5
_CC = 6

# Indices for termios winsize tuple.
_ROWS = 0
_COLS = 1

# Do we have termios.tcgetwinsize() and termios.tcsetwinsize()?
_HAVE_WINSZ = (hasattr(termios, "TIOCGWINSZ")
               and hasattr(termios, "TIOCSWINSZ")
               and hasattr(termios, "tcgetwinsize")
               and hasattr(termios, "tcsetwinsize"))

# All possible iflag boolean mask names.
_ifbool = {
    "IGNBRK", "BRKINT", "IGNPAR", "PARMRK", "INPCK", "ISTRIP",
    "INLCR", "IGNCR", "ICRNL", "IUCLC", "IXON", "IXANY",
    "IXOFF", "IMAXBEL"
}

# All possible oflag boolean mask names.
_ofbool = {
    "OPOST", "OLCUC", "ONLCR", "OCRNL",
    "ONOCR", "ONLRET", "OFILL", "OFDEL"
}

# All possible cflag boolean mask names.
_cfbool = {
    "CSTOPB", "CREAD", "PARENB", "PARODD",
    "HUPCL", "CLOCAL", "CIBAUD", "CRTSCTS"
}

# All possible lflag boolean mask names.
_lfbool = {
    "ISIG", "ICANON", "XCASE", "ECHO", "ECHOE", "ECHOK",
    "ECHONL", "ECHOCTL", "ECHOPRT", "ECHOKE", "FLUSHO",
    "NOFLSH", "TOSTOP", "PENDIN", "IEXTEN"
}

# Name of mask representing "number of bits transmitted or
# received per byte" (part of cflag) and names of all
# possible values.
_cs = {"CSIZE": {"CS5", "CS6", "CS7", "CS8"}}

# All possible delay mask names (parts of oflag)
# and names of all of their possible values.
_dly = {
    "CRDLY": {"CR0", "CR1", "CR2", "CR3"},
    "NLDLY": {"NL0", "NL1"},
    "TABDLY": {"TAB0", "TAB1", "TAB2", "TAB3"},
    "BSDLY": {"BS0", "BS1"},
    "FFDLY": {"FF0", "FF1"},
    "VTDLY": {"VT0", "VT1"}
}

# Names of all possible indices of the control character list.
_cc = {
    "VEOF", "VEOL", "VEOL2", "VERASE", "VERASE2", "VWERASE",
    "VKILL", "VREPRINT", "VINTR", "VQUIT", "VSUSP", "VDSUSP",
    "VSTART", "VSTOP", "VLNEXT", "VSTATUS", "VDISCARD", "VSWTCH"
}

# All possible Baud rate "indices".
_r = {
    0, 50, 75, 110, 134, 150, 200, 300, 600,
    1200, 1800, 2400, 4800, 9600, 19200, 38400,
    57600, 115200, 230400, 460800, 500000, 576000,
    921600, 1000000, 1152000, 1500000, 2000000,
    2500000, 3000000, 3500000, 4000000
}

# Keys of _bool_d are lowercase names of masks that take boolean values
# (for example one can turn ECHO on/off).
#
# Example element of _bool_d.items() is ("echo", (_LFLAG, termios.ECHO))
_bool_d = {}
for flag, maskset in [(_IFLAG, _ifbool),
                      (_OFLAG, _ofbool),
                      (_CFLAG, _cfbool),
                      (_LFLAG, _lfbool)]:
    for mask in maskset:
        if hasattr(termios, mask):
            _bool_d[mask.lower()] = (flag, getattr(termios, mask))

# Keys of _symbol_d are lowercase names of masks that take
# values from a small set (cardinality < 10) of named
# constants. For example, TABDLY can take values from the
# set {TAB0, TAB1, TAB2, TAB3}. This loop will make sure
# that these masks can be set using lowercase names and
# lowercase strings representing the values. For example,
# stty.tab0 will be same as termios.TAB0, and for an Stty
# object x, the following 2 lines will have same effect:
# x.tabdly = stty.tab0
# x.tabdly = "tab0"
#
# Example element of _symbol_d.items() is
# ("nldly", 4-element-tuple), where 4-element-tuple is
# (_OFLAG, termios.NLDLY,
# {stty.nl0: "nl0", stty.nl1: "nl1"},
# {"nl0": stty.nl0, "nl1": stty.nl1}).
#
# Note again that the 3rd element of this example tuple
# is same as {termios.NL0: "nl0", termios.NL1: "nl1"}
# and the 4th one is same as
# {"nl0": termios.NL0, "nl1": termios.NL1}.
_symbol_d = {}
for flag, maskdict in [(_CFLAG, _cs), (_OFLAG, _dly)]:
    for mask, maskvalues in maskdict.items():
        if hasattr(termios, mask):
            # Values of mask that are available on
            # system; for example, if mask is CRDLY
            # and system only has CR0, CR1, then
            # avail == {termios.CR0: "cr0", termios.CR1: "cr1"} ==
            # {stty.cr0: "cr0", stty.cr1: "cr1"}.
            avail = {}
            for v in maskvalues:
                if hasattr(termios, v):
                    num_v = getattr(termios, v)
                    avail[num_v] = v.lower()

                    # Example explaining this setattr: it will
                    # define stty.cr0 to be same as termios.CR0.
                    setattr(sys.modules[__name__], v.lower(), num_v)
                    __all__.append(v.lower())

            avail_inverse = {v: k for k, v in avail.items()}

            _symbol_d[mask.lower()] = (flag, getattr(termios, mask),
                                    avail, avail_inverse)

# Example element of _baud_d.items() is (50, termios.B50)
# Example element of _baud_d_inverse.items() is (termios.B50, 50)
_baud_d = {}
for n in _r:
    rate = f"B{n}"
    if hasattr(termios, rate):
        _baud_d[n] = getattr(termios, rate)

_baud_d_inverse = {v: k for k, v in _baud_d.items()}

# Example element of _cc_d.items() is ("eof", termios.VEOF)
_cc_d = {}
for s in _cc:
    if hasattr(termios, s):
        _cc_d[s[1:].lower()] = getattr(termios, s)

_noncanon_d = {"min": termios.VMIN, "time": termios.VTIME}

_speed_d = {"ispeed": _ISPEED, "ospeed": _OSPEED}

_winsz_d = {"rows": _ROWS, "cols": _COLS} if _HAVE_WINSZ else {}
_default_winsize = [24, 80]

# Set of lowercase names of all Stty object
# attributes available on system (strings),
# excluding "_termios" and "_winsize".
_available = {
    *_bool_d, *_symbol_d, *_speed_d,
    *_cc_d, *_noncanon_d, *_winsz_d
}

# Dictionary of all available Stty object
# attributes, attribute values, and other
# data; built for convenient iteration.
_available_dict = {}
_available_dict["boolean"] = {}
for flagname, maskset in [("iflag", _ifbool),
                          ("oflag", _ofbool),
                          ("cflag", _cfbool),
                          ("lflag", _lfbool)]:
    _available_dict["boolean"][flagname] = {mask.lower() for mask in maskset
                                            if hasattr(termios, mask)}
_available_dict["csize"] = {v.lower() for v in _cs["CSIZE"]
                            if hasattr(termios, v)}
_available_dict["delay_masks"] = {mask.lower(): {v.lower() for v in maskvalues
                                                 if hasattr(termios, v)}
                                  for mask, maskvalues in _dly.items()}
_available_dict["control_character"] = set(_cc_d)
_available_dict["non_canonical"] = set(_noncanon_d)
_available_dict["speed"] = set(_speed_d)
_available_dict["winsize"] = set(_winsz_d)
_available_dict["baud_rates"] = set(_baud_d)
# This copy is for the user.
settings = copy.deepcopy(_available_dict)


class Stty(object):
    """Manipulate termios and winsize in the style of stty(1)."""
    def __init__(self, fd=None, path=None, **opts):
        if fd == None and path == None:
            raise ValueError("fd or path must be provided")

        if fd != None and path != None:
            raise ValueError("only one of fd or path must be provided")

        if fd != None:
            self.fromfd(fd)

        if path != None:
            self.load(path)

        self.set(**opts)

    def __setattr__(self, name, value):
        if name == "_termios" or name == "_winsize":
            raise AttributeError(f"attribute '{name}' must not be "
                                 "directly modified")

        if name in _bool_d:
            if not isinstance(value, bool):
                raise TypeError(f"value of attribute '{name}' must have "
                                "type 'bool'")

            x = _bool_d[name]
            if value:
                self._termios[x[0]] |= x[1]
            else:
                self._termios[x[0]] &= ~x[1]

            super().__setattr__(name, value)
            return

        if name in _symbol_d:
            if not (isinstance(value, int) or isinstance(value, str)):
                raise TypeError(f"value of attribute '{name}' must have "
                                "type 'int' or 'str'")

            x = _symbol_d[name] # 4-tuple

            if isinstance(value, int):
                if value not in x[2]:
                    raise ValueError(f"unsupported value '{value}' for "
                                     f"attribute '{name}'")

                value_as_int = value
                value_as_str = x[2][value]

            if isinstance(value, str):
                if value not in x[3]:
                    raise ValueError(f"unsupported value '{value}' for "
                                     f"attribute '{name}'")

                value_as_int = x[3][value]
                value_as_str = value

            self._termios[x[0]] &= ~x[1]
            self._termios[x[0]] |= value_as_int

            super().__setattr__(name, value_as_str)
            return

        if name in _speed_d:
            if not isinstance(value, int):
                raise TypeError(f"value of attribute '{name}' must have "
                                "type 'int'")

            if value not in _baud_d:
                raise ValueError(f"unsupported value {value} for "
                                 f"attribute '{name}'")

            self._termios[_speed_d[name]] = _baud_d[value]

            super().__setattr__(name, value)
            return

        if name in _cc_d:
            if not (isinstance(value, str) or isinstance(value, bytes)):
                raise TypeError(f"value of attribute '{name}' must have "
                                "type 'str' or 'bytes'")

            if isinstance(value, str):
                value_as_bytes = cc_str_to_bytes(value)
                # cc_bytes_to_str() is not a strict inverse of
                # cc_str_to_bytes(); for example:
                # cc_bytes_to_str(cc_str_to_bytes("^-")) == "undef"
                # cc_bytes_to_str(cc_str_to_bytes("^d")) == "D"
                #
                # Calling cc_bytes_to_str() here ensures "uniformity
                # of representation"; for example, "^a" and "^A" both
                # represent <SOH> in the POSIX manpage of stty(1) and
                # the cc_bytes_to_str() call here will make sure that
                # "name" is set to "^A" for either value "^a", "^A" of
                # the variable "value".
                value_as_str = cc_bytes_to_str(value_as_bytes)

            if isinstance(value, bytes):
                value_as_bytes = value
                value_as_str = cc_bytes_to_str(value_as_bytes)

            if value_as_bytes == None or value_as_str == None:
                raise ValueError(f"unsupported value '{value}' for "
                                 f"attribute '{name}'")

            self._termios[_CC][_cc_d[name]] = value_as_bytes

            super().__setattr__(name, value_as_str)
            return

        if name in _noncanon_d:
            if not (isinstance(value, int) or isinstance(value, bytes)):
                raise TypeError(f"value of attribute '{name}' must have "
                                "type 'int' or 'bytes'")

            if isinstance(value, int):
                if value < 0:
                    raise ValueError("expected nonnegative value for "
                                     f"attribute '{name}'")
                value_as_int = value

            if isinstance(value, bytes):
                if len(value) != 1:
                    raise ValueError(f"expected 1 byte long value for "
                                     f"attribute '{name}' but got '{value}'")
                value_as_int = value[0]

            self._termios[_CC][_noncanon_d[name]] = value

            super().__setattr__(name, value_as_int)
            return

        if name in _winsz_d:
            if not isinstance(value, int):
                raise TypeError(f"value of attribute '{name}' must have "
                                "type 'int'")

            if value < 0:
                raise ValueError(f"expected nonnegative value for "
                                 f"attribute '{name}'")

            self._winsize[_winsz_d[name]] = value

            super().__setattr__(name, value)
            return

        raise AttributeError(f"attribute '{name}' unsupported on platform")

    def __repr__(self):
        ret = ""
        for l, h in [(_available_dict["boolean"]["iflag"], "iflag bool"),
                     (_available_dict["boolean"]["oflag"], "oflag bool"),
                     (_available_dict["boolean"]["cflag"], "cflag bool"),
                     (_available_dict["boolean"]["lflag"], "lflag bool"),
                     (_available_dict["control_character"], "cc"),
                     (_available_dict["non_canonical"], "min, time"),
                     (["csize"], "csize"),
                     (_available_dict["delay_masks"], "delay masks"),
                     (_available_dict["speed"], "speed"),
                     (_available_dict["winsize"], "winsize")]:
            L = [f"{x}={getattr(self, x)}" for x in sorted(l)]
            s = " ".join(L)
            ret = f"{ret}\n{h.upper()}: {s}\n"

        return ret

    def __str__(self):
        return ", ".join(sorted([f"{x}={getattr(self, x)}" for x in _available]))

    def get(self):
        """Return dictionary of relevant attributes."""
        return {x: getattr(self, x) for x in _available}

    def set(self, **opts):
        """Set multiple attributes as named arguments."""
        excess = set(opts) - _available
        if len(excess) > 0:
            raise AttributeError("attributes in the following set are "
                                 f"unsupported on this platform: {excess}")

        for x in opts:
            self.__setattr__(x, opts[x])

    def save(self, path=None):
        """Return deep copy of self or save JSON.
        This mimics "stty -g".
        """
        if not path:
            return copy.deepcopy(self)

        with open(path, "w") as f:
            json.dump(self.get(), f)

        return None

    def load(self, path):
        """Load termios and winsize from JSON file."""
        if not hasattr(super(), "_termios"):
            dev_tty_fd = os.open("/dev/tty", os.O_RDWR)
            super().__setattr__("_termios",
                                termios.tcgetattr(dev_tty_fd))
            os.close(dev_tty_fd)

        if _HAVE_WINSZ:
            if not hasattr(super(), "_winsize"):
                super().__setattr__("_winsize", _default_winsize)
        else:
            super().__setattr__("_winsize", None)

        with open(path, "r") as f:
            d = json.load(f)

        deficiency = _available - set(d)
        if len(deficiency) > 0:
            raise ValueError("JSON file does not contain the following "
                             f"necessary attributes: {deficiency}")

        # This "if" block mimics termios.tcgetattr behavior,
        # which keeps "min" and "time" fields in "bytes"
        # form in Canonical mode and converts them to
        # integers in Non-Canonical mode; the dictionary "d"
        # loaded from JSON will have integer "min" and
        # "time" values (if it was generated using Stty.save
        # and if it was not subsequently modified
        # externally).
        if d.get("icanon"): # Canonical mode.
            if "min" in d:
                d["min"] = bytes([d["min"]])
            if "time" in d:
                d["time"] = bytes([d["time"]])

        self.set(**d)

    def fromfd(self, fd):
        """Get settings from terminal."""
        super().__setattr__("_termios", termios.tcgetattr(fd))
        if _HAVE_WINSZ:
            super().__setattr__("_winsize", list(termios.tcgetwinsize(fd)))
        else:
            super().__setattr__("_winsize", None)

        for name in _bool_d:
            x = _bool_d[name]
            value = True if (self._termios[x[0]] & x[1]) else False
            self.__setattr__(name, value)

        for name in _symbol_d:
            x = _symbol_d[name]
            y = self._termios[x[0]] & x[1]
            self.__setattr__(name, y)

        for name in _speed_d:
            x = self._termios[_speed_d[name]]
            self.__setattr__(name, _baud_d_inverse[x])

        for name in _cc_d:
            self.__setattr__(name, self._termios[_CC][_cc_d[name]])

        for name in _noncanon_d:
            self.__setattr__(name, self._termios[_CC][_noncanon_d[name]])

        if self._winsize:
            for name in _winsz_d:
                self.__setattr__(name, self._winsize[_winsz_d[name]])

    def tofd(self, fd, when=termios.TCSANOW, apply_termios=True,
             apply_winsize=True):
        """Apply settings to terminal."""
        if apply_termios:
            termios.tcsetattr(fd, when, self._termios)
        if apply_winsize and self._winsize:
            termios.tcsetwinsize(fd, self._winsize)

    def evenp(self, plus=True):
        """Set/unset evenp combination mode."""
        if plus:
            self.set(parenb=True, csize=cs7, parodd=False)
        else:
            self.set(parenb=False, csize=cs8)

    def oddp(self, plus=True):
        """Set/unset oddp combination mode."""
        if plus:
            self.set(parenb=True, csize=cs7, parodd=True)
        else:
            self.set(parenb=False, csize=cs8)

    def raw(self):
        """Set raw combination mode."""
        for x in _available_dict["boolean"]["iflag"]:
            self.__setattr__(x, False)
        for x in _available_dict["boolean"]["lflag"]:
            self.__setattr__(x, False)
        self.set(opost=False, parenb=False,
                 csize=cs8, min=1, time=0)

    def nl(self, plus=True):
        """Set/unset nl combination mode."""
        if plus:
            self.icrnl = False
        else:
            self.set(icrnl=True, inlcr=False, igncr=False)

    def ek(self):
        """Set ek combination mode."""
        if hasattr(termios, "CERASE"):
            self.erase = bytes([termios.CERASE])

        if hasattr(termios, "CKILL"):
            self.kill = bytes([termios.CKILL])

    def openpty(self, apply_termios=True, apply_winsize=True):
        """Open a new pty pair and apply
        settings to slave end.
        """
        m, s = os.openpty()

        self.tofd(s, apply_termios=apply_termios,
                  apply_winsize=apply_winsize)

        return m, s, os.ttyname(s)

    def forkpty(self, apply_termios=True, apply_winsize=True):
        """Call os.forkpty() and apply settings to slave end."""
        child = 0
        stdin_fd = 0

        if hasattr(os, "ptsname"):
            pid, m = os.forkpty()

            if pid == child:
                # Slave end of pty is now standard input
                # of child process thanks to a login_tty()
                # call in forkpty().
                self.tofd(stdin_fd, apply_termios=apply_termios,
                          apply_winsize=apply_winsize)
                sname = os.ttyname(stdin_fd)
            else:
                sname = os.ptsname(m)
        else:
            m, s, sname = self.openpty(apply_termios=apply_termios,
                                       apply_winsize=apply_winsize)

            pid = os.fork()
            if pid == child:
                os.close(m)
                os.login_tty(s)
            else:
                os.close(s)

        return pid, m, sname

# Print help message about Stty attributes.

_settings_lines = []

_settings_lines.append("For details on the following attributes, "
      "check the manpage of stty(1) on your system.\n")

_settings_lines.append("Stty attributes:\n")

for x, y in [("iflag", "input mode"),
             ("oflag", "output mode"),
             ("cflag", "control mode"),
             ("lflag", "local mode")]:
    _settings_lines.append(
        f"  Boolean {y} attributes (possible values: True, False):"
    )
    _settings_lines.append(
        f"    {' '.join(sorted(_available_dict['boolean'][x]))}\n"
    )

_settings_lines.append(
    "  Winsize attributes (possible values: any nonnegative integer):"
)
_settings_lines.append(
    f"    {' '.join(sorted(_available_dict['winsize']))}\n"
)

_settings_lines.append(
    "  Non-canonical mode-related attributes (possible values: "
    "any nonnegative integer):"
)
_settings_lines.append(
    f"    {' '.join(sorted(_available_dict['non_canonical']))}\n"
)

_settings_lines.append("  CSIZE and *DLY attributes:")
heading1 = "ATTRIBUTE"
heading2 = "POSSIBLE VALUES"
csize_key = "csize"
csize_values = ", ".join(
    sorted([f'stty.{v}, "{v}"' for v in _available_dict["csize"]])
)

padding = max(len(x) for x in _available_dict["delay_masks"])
padding = max(padding, len(csize_key), len(heading1))

# Print heading for the table.
_settings_lines.append(f"    {heading1:^{padding}}  |  {heading2}")
# Print the CSIZE row.
_settings_lines.append(f"    {csize_key:^{padding}}  |  {csize_values}")
# Print the *DLY rows.
for mask, maskvalset in _available_dict["delay_masks"].items():
    mask_values = ", ".join(sorted([f'stty.{v}, "{v}"' for v in maskvalset]))
    _settings_lines.append(f"    {mask:^{padding}}  |  {mask_values}")

_settings_lines.append("\n  Control character attributes:")
_settings_lines.append(
    "    ATTRIBUTES: "
    + " ".join(sorted(_available_dict['control_character']))
)
_settings_lines.append(
    f"""    POSSIBLE VALUES: a string or bytes object. If a string value is
                     used, then it must be a string of length 1, or
                     a string of length 2 staring with "^" (caret,
                     circumflex) to represent a control character,
                     or the string "undef". Please check the manpage
                     of stty(1) for more details. If a value of type
                     "bytes" is used, then it must be of length 1.
"""
)

_settings_lines.append("  Speed attributes:")
_settings_lines.append(
    f"    ATTRIBUTES: {' '.join(sorted(_available_dict['speed']))}"
)
_settings_lines.append(
    "    POSSIBLE VALUES: "
    + ", ".join([str(n) for n in sorted(_available_dict['baud_rates'])])
)

_settings_str = "\n".join(_settings_lines)

def settings_help_str():
    """Return help string about all
    available Stty attributes and
    their possible values on the
    current platform.
    """
    return _settings_str

def settings_help():
    """Print help message about all
    available Stty attributes and
    their possible values on the
    current platform.
    """
    print(_settings_str)
