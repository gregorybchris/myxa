import logging
from dataclasses import dataclass
from enum import Enum as StdEnum
from enum import StrEnum
from inspect import isclass, isfunction, ismodule
from inspect import signature as get_function_signature
from pathlib import Path

from rich.pretty import pprint

from myxa.code import geometry as geom
from myxa.errors import InternalError
from myxa.manager import Manager
from myxa.models import Enum, Float, Func, Int, MemberNode, Mod, Null, Package, Param, Str, Variant, VarNode

logger = logging.getLogger(__name__)


@dataclass
class Extractor:
    def extract(self, obj: object, package: Package) -> None:
        mod = self.extract_mod(obj, package.info.name)
        package.members = {mod.name: mod}

    @staticmethod
    def annotation_to_node(annotation: type) -> VarNode:
        if annotation is str:
            return Str()
        if annotation is int:
            return Int()
        if annotation is float:
            return Float()

        msg = f"Annotation type not implemented: {annotation}"
        raise InternalError(msg)

    def extract_mod(self, obj: object, module_name: str) -> Mod:
        assert ismodule(obj)

        members: dict[str, MemberNode] = {}
        for member_name, member in vars(obj).items():
            if member_name.startswith("__"):
                continue

            # TODO: Handle imports better
            if ismodule(member):
                continue

            if isfunction(member):
                signature = get_function_signature(member)

                params: dict[str, Param] = {}
                for parameter_name, parameter in signature.parameters.items():
                    param_var_node = self.annotation_to_node(parameter.annotation)
                    param = Param(name=parameter_name, var_node=param_var_node)
                    params[param.name] = param

                return_var_node = self.annotation_to_node(signature.return_annotation)

                func = Func(
                    name=member_name,
                    params=params,
                    return_var_node=return_var_node,
                )
                members[member_name] = func
            elif isclass(member):
                # TODO: Handle dataclass/struct
                # TODO: Handle imports better
                if issubclass(member, StdEnum) and member not in [StdEnum, StrEnum]:
                    print("enum", member_name)
                    variants: dict[str, Variant] = {}
                    for v in member:
                        # TODO: Is there a way to add data here?
                        var_node = Null()
                        variant_name = str(v)
                        variant = Variant(name=variant_name, var_node=var_node)
                        variants[variant_name] = variant
                    myxa_enum = Enum(name=member_name, variants=variants)
                    members[member_name] = myxa_enum
            else:
                msg = f"Module member type not implemented: {member_name}: {type(member)}"
                logger.warning(msg)

        # TODO: Handle name
        # TODO: Handle imports
        return Mod(name=module_name, imports=[], members=members)


if __name__ == "__main__":
    manager = Manager()
    package_filepath = Path(__file__).parent.parent.parent / "examples" / "pizza" / "package.json"
    package = manager.load_package(package_filepath)

    extractor = Extractor()
    # code_dirpath = Path(__file__).parent.parent.parent / "examples" / "pizza" / "code"
    # new_package = extractor.extract(code_dirpath, package)
    extractor.extract(geom, package)

    pprint(package)
