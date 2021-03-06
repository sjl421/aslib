"""
Software configuration tool.
"""

# FIXME: Examples!

#-------------------------------------------------------------------------------

from   . import py
from   .itr import chain

#-------------------------------------------------------------------------------

def _check_name(name):
    if name.isidentifier():
        return name
    else:
        raise ValueError("invalid name '{}'".format(name))


#-------------------------------------------------------------------------------

class Var:
    """
    A configuration variable.

    The variable has,
    - A constructor or conversion function.
    - Optionally, a default value.
    - Optionally, a help string.
    """

    def __init__(self, convert=py.idem, default=py.NO_DEFAULT, help=None):
        self.__convert = convert
        self.__default = default
        self.__help = help


    def __repr__(self):
        kw_args = dict(convert=self.__convert, help=self.__help)
        if self.__default is not py.NO_DEFAULT:
            kw_args["default"] = self.__default
        return py.format_ctor(self, **kw_args)


    def __str__(self):
        result = getattr(self.__convert, "__name__", str(self.__convert))
        if self.__default is not py.NO_DEFAULT:
            result += " default={!r}".format(self.__default)
        if self.__help is not None:
            result += " : " + help
        return result


    @property
    def convert(self):
        return self.__convert


    @property
    def default(self):
        if self.__default is py.NO_DEFAULT:
            raise LookupError("no default")
        else:
            return self.__default


    @property
    def help(self):
        return self.__help


    def convert(self, value):
        return value if self.__convert is None else self.__convert(value)



class Group:
    """
    A namespace of configuration variables, possibly nested.

    Maps names, which must be Python identifiers, to configuration variables
    or to other groups.
    """

    def __init__(self, args={}, **kw_args):
        self.vars = {}
        self.update(args, **kw_args)


    def __repr__(self):
        return py.format_ctor(self, self.vars)


    def __setitem__(self, name, value):
        """
        Adds or replaces a name.

        If `value` is a `Group` or `Var`, it is set directly.  Otherwise, if 
        `value` is callable, a new `Var` is used with `value` as the conversion
        function.  Otherwise, a new `Var` is used with `value` as the default
        and its type as the conversion function.
        """
        name = _check_name(name)

        if isinstance(value, (Group, Var)):
            self.vars[name] = value
        elif callable(value):
            self.vars[name] = Var(convert=value)
        else:
            self.vars[name] = Var(convert=type(value), default=value)


    def __getitem__(self, name):
        name = _check_name(name)
        try:
            return self.vars[name]
        except KeyError:
            raise KeyError(name) from None


    def update(self, args={}, **kw_args):
        for name, var in args.items():
            self.__setitem__(name, var)
        for name, var in kw_args.items():
            self.__setitem__(name, var)



#-------------------------------------------------------------------------------

class Cfg:
    """
    A configuration.

    A configuration relates to a group, and contains value assignments to some
    of the group's variables.
    """

    def __init__(self, group, args={}):
        vals = {}
        for name, var in group.vars.items():
            if isinstance(var, Group):
                vals[name] = Cfg(var, args.pop(name, {}))
            else:
                try:
                    val = args.pop(name)
                except KeyError:
                    pass
                else:
                    vals[name] = val

        if len(args) > 0:
            raise LookupError("no vars " + ", ".join(args.keys()))

        object.__setattr__(self, "_Cfg__group", group)
        object.__setattr__(self, "_Cfg__vals", vals)


    def __repr__(self):
        return py.format_ctor(self, self.__group, self.__vals)


    def __str__(self):
        return "\n".join(self.__format()) + "\n"


    def __format(self, indent="  "):
        for name, var in sorted(self.__group.vars.items()):
            if isinstance(var, Group):
                cfg = getattr(self, name)
                yield "{}.".format(name)
                for line in cfg.__format(indent):
                    yield indent + line
            else:
                try:
                    val = self.__vals[name]
                except KeyError:
                    val = ""
                else:
                    val = "={!r}".format(val)
                yield "{}{} {}".format(name, val, var)


    def __setattr__(self, name, value):
        try:
            var = self.__group[name]
        except KeyError:
            raise AttributeError(name) from None

        if isinstance(var, Group):
            try:
                cfg = self.__vals[name]
            except KeyError:
                cfg = self.__vals[name] = Cfg(var)
            cfg(value)

        else:  
            self.__vals[name] = var.convert(value)


    def __getattr__(self, name):
        try:
            return self.__vals[name]
        except KeyError:
            try:
                var = self.__group[name]
            except KeyError:
                raise AttributeError("no config " + name) from None
            else:
                try:
                    return var.default
                except AttributeError:
                    raise AttributeError(
                        "no value for config " + name) from None


    def __call__(self, args={}, **kw_args):
        for name, value in args.items():
            self.__setattr__(name, value)
        for name, value in kw_args.items():
            self.__setattr__(name, value)
        return self



