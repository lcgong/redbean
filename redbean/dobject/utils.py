from typing import Union, _GenericAlias, get_args, get_origin
# from dataclasses import dataclass

def is_complaint(obj, typ):
    if isinstance(typ, type):
      return isinstance(obj, typ)        

    if isinstance(typ, _GenericAlias):
        alias_origin = get_origin(typ)
        if issubclass(alias_origin, (list, tuple)): # List[int]
            if isinstance(obj, (list, tuple)):
                item_type = get_args(typ)[0]
                for item in obj:
                    if not is_complaint(item, item_type):
                        return False
                return True
            
            return False

        if issubclass(get_origin(typ), dict): # Map[int]
            if isinstance(obj, dict):
                key_typ, val_typ = get_args(typ)[:2]

                for k, v in obj.items():
                    if not is_complaint(k, key_typ):
                        return False

                    if not is_complaint(v, val_typ):
                        return False
                
                return True

            return False

        return isinstance(obj, typ)

    raise ValueError(f"Unsupport '{typ}'")