import os
import dataclasses
from typing import Awaitable, Any, Callable, Iterable, Mapping, Tuple, Sequence, Union
from typing import overload
from typing import Iterator, List, Dict
from aiohttp.web_request import Request
from aiohttp.web_response import StreamResponse
from aiohttp.web_urldispatcher import AbstractRoute, UrlDispatcher
from aiohttp import hdrs
from .rest import rest_method

PathLike = Union[str, "os.PathLike[str]"]
HandlerType = Callable[[Request], Awaitable[StreamResponse]]


@dataclasses.dataclass(frozen=True, repr=False)
class RouteDef:
    method: str
    path: str
    handler: HandlerType
    handler_doc: str
    kwargs: Dict[str, Any]

    def __repr__(self) -> str:
        info = []
        for name, value in sorted(self.kwargs.items()):
            info.append(f", {name}={value!r}")
        return "<RouteDef {method} {path} -> {handler.__name__!r}" "{info}>".format(
            method=self.method, path=self.path, handler=self.handler, info="".join(
                info)
        )

    def register(self, router: UrlDispatcher) -> List[AbstractRoute]:
        if self.method in hdrs.METH_ALL:
            reg = getattr(router, "add_" + self.method.lower())
            return [reg(self.path, self.handler, **self.kwargs)]
        else:
            return [
                router.add_route(self.method, self.path,
                                 self.handler, **self.kwargs)
            ]


_Deco = Callable[[Any], Any]

class RestServiceDef(Sequence[RouteDef]):
    """Route definition table"""

    def __init__(self, *, prefix: str = None) -> None:
        self._items = []  # type: List[RouteDef]
        self._prefix = prefix if prefix is not None else ""

    def __repr__(self) -> str:
        return "<RouteTableDef count={}>".format(len(self._items))

    @overload
    def __getitem__(self, index: int) -> RouteDef:
        ...

    @overload
    def __getitem__(self, index: slice) -> List[RouteDef]:
        ...

    def __getitem__(self, index):  # type: ignore[no-untyped-def]
        return self._items[index]

    def __iter__(self) -> Iterator[RouteDef]:
        return iter(self._items)

    def __len__(self) -> int:
        return len(self._items)

    def __contains__(self, item: object) -> bool:
        return item in self._items

    def route(self, method: str, path: str, **kwargs: Dict[str, Any]) -> _Deco:
        path = self._prefix + path
        def inner(handler: Any) -> Any:
            # print(3333, handler.__doc__)
            handler = rest_method(handler)
            self._items.append(RouteDef(method, path, handler, handler.__doc__, kwargs))
            return handler

        return inner

    def head(self, path: str, **kwargs: Dict[str, Any]) -> _Deco:
        return self.route(hdrs.METH_HEAD, path, **kwargs)

    def get(self, path: str, **kwargs: Dict[str, Any]) -> _Deco:
        return self.route(hdrs.METH_GET, path, **kwargs)

    def post(self, path: str, **kwargs: Dict[str, Any]) -> _Deco:
        return self.route(hdrs.METH_POST, path, **kwargs)

    def put(self, path: str, **kwargs: Dict[str, Any]) -> _Deco:
        return self.route(hdrs.METH_PUT, path, **kwargs)

    def patch(self, path: str, **kwargs: Dict[str, Any]) -> _Deco:
        return self.route(hdrs.METH_PATCH, path, **kwargs)

    def delete(self, path: str, **kwargs: Dict[str, Any]) -> _Deco:
        return self.route(hdrs.METH_DELETE, path, **kwargs)

    def options(self, path: str, **kwargs: Dict[str, Any]) -> _Deco:
        return self.route(hdrs.METH_OPTIONS, path, **kwargs)
