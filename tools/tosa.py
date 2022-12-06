import re
import xml.etree.ElementTree as ET


class TOSAOperatorArgumentCategory:
    def __init__(self, name, profiles=None):
        self.name = name
        self.profiles = profiles


class TOSAOperatorArgument:
    def __init__(self, name, description, categories, ty, shape, levellimits):
        self.name = name
        self.description = description
        self.categories = categories
        self.type = ty
        self.shape = shape
        self.levellimits = levellimits


class TOSAOperatorDataTypeSupport:
    def __init__(self, mode, tymap, profiles=None):
        self.mode = mode
        self.tymap = tymap
        self.profiles = profiles


class TOSAOperator:
    def __init__(self, name, arguments, types, typesupports):
        self.name = name
        self.arguments = arguments
        self.types = types
        self.typesupports = typesupports


class TOSAOperatorGroup:
    def __init__(self, name, operators):
        self.name = name
        self.operators = operators


class TOSASpec:
    def __init__(self, xmlpath):
        tree = ET.parse(xmlpath)
        self.xmlroot = tree.getroot()
        self.operatorgroups = []
        self.__load_spec()

    def __load_spec(self):
        self.__load_version()
        for group in self.xmlroot.findall("./operators/operatorgroup"):
            self.operatorgroups.append(self.__load_operator_group(group))

    def __load_version(self):
        version = self.xmlroot.find("./version")
        self.version_major = int(version.get("major"))
        self.version_minor = int(version.get("minor"))
        self.version_patch = int(version.get("patch"))
        if version.get("draft") == "true":
            self.version_is_draft = True
        else:
            self.version_is_draft = False

    def __load_operator_group(self, group):
        name = group.get("name")
        operators = []
        for op in group.findall("operator"):
            operators.append(self.__load_operator(op))
        return TOSAOperatorGroup(name, operators)

    def __load_operator(self, op):
        name = op.find("name").text
        args = []
        types = []
        typesupports = []
        for arg in op.findall("arguments/argument"):
            args.append(self.__load_operator_argument(arg))

        # TODO add pseudo-code to operator object?

        for ty in op.findall("types/type"):
            types.append(ty.get("name"))

        for tysup in op.findall("typesupport"):
            tsmode = tysup.get("mode")
            tsmap = {}
            profiles = tysup.findall("profile")
            tsprofiles = []
            for p in profiles:
                tsprofiles.append(p.get("name"))
            for ty in types:
                tsmap[ty] = tysup.get(ty)
            typesupports.append(TOSAOperatorDataTypeSupport(tsmode, tsmap, tsprofiles))
        return TOSAOperator(name, args, types, typesupports)

    def __load_operator_argument(self, arg):
        name = arg.get("name")
        desc = arg.find("description").text.strip()
        argcats = []
        argtype = arg.get("type")
        shape = arg.get("shape")
        levellimits = []
        for levellimit in arg.findall("levellimit"):
            value = levellimit.get("value")
            limit = levellimit.get("limit")
            levellimits.append([value, limit])

        cats = re.findall(
            r"(input|output|attribute)\(?([A-Z,]+)?\)?", arg.get("category")
        )
        for cat in cats:
            argcats.append(TOSAOperatorArgumentCategory(cat[0], cat[1].split(",")))

        return TOSAOperatorArgument(name, desc, argcats, argtype, shape, levellimits)
