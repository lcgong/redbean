import click


# __traceback_hide__ = True

import inspect
from importlib import import_module

def lookup_app_module():
    for path in ('app.py', 'main.py'):
        path = Path(path).resolve()
        if not path.exists():
            continue


        module_name = []
        while True:
            module_name.append(path.stem)
            path = path.parent
            if not ( path/ '__init__.py').exists():
                break

        module_name = '.'.join(module_name[::-1])
        path = str(path)
        if sys.path[0] != path:
            sys.path.insert(0, path)

        break
    else:
        raise NameError("Could not find app module")

    return import_module(module_name)

from collections import namedtuple

AppRunInfo = namedtuple('AppRunInfo', ['module_name', 'attribute_name', 'factory_name'])

def find_best_app_factory(module):
    __traceback_hide__ = True

    from redbean import Application

    # Search for the most common names first.
    for attr_name in ('app', 'application'):
        app = getattr(module, attr_name, None)
        if isinstance(app, Application):
            return AppRunInfo(module.__name__, attr_name, None)

    callables = []
    matched = []
    for name in dir(module):
        obj = getattr(module, name, None)
        if inspect.isfunction(obj):
            callables.append((name, obj))
            continue
        if isinstance(obj, Application):
            matched.append((name, obj))

    if len(matched) == 1:
        return AppRunInfo(module.__name__, matched[0][0], None)
    elif len(matched) > 1:
        apps = ', '.join(["'" + t[0] + "'" for t in matched])
        raise NoAppFoundError(
            # f"Auto-detected multiple applications "
            f"Auto-detected multiple applications({apps})"
            f"in module '{module.__name__ }'.  Use option "
            f"'--app={module.__name__ }:name' to specify the correct one"
        )

    matched = []
    for factory_name, factory in callables:
        if issubclass(inspect.signature(factory).return_annotation, Application):
            matched.append((factory_name, factory))
    if len(matched) == 1:
        return AppRunInfo(module.__name__, None, matched[0][0])
    elif len(matched) > 1:
        app_factories = ', '.join(["'" + t[0] + "'" for t in matched])
        raise NoAppFoundError(
            f"Auto-detected multiple application factories({app_factories})"
            f"in module '{module.__name__}'."
            f" Use option '--app={module}:name' to specify the correct one"
        )

    raise NoAppFoundError(
        f"Couldnot find the application in module '{module.__name__}'."
        f" Use option '--app={module}:name' to specify the correct one"
    )


from pathlib import Path
import os, sys

# def iter_traceback_frames(tb):
#     """
#     Given a traceback object, it will iterate over all
#     frames that do not contain the ``__traceback_hide__``
#     local variable.
#     """
#     while tb:
#         # support for __traceback_hide__ which is used by a few libraries
#         # to hide internal frames.
#         f_locals = getattr(tb.tb_frame, 'f_locals', {})
#         if not _getitem_from_frame(f_locals, '__traceback_hide__'):
#             yield tb.tb_frame, getattr(tb, 'tb_lineno', None)
#         tb = tb.tb_next
#
#
#
# def iter_stack_frames(frames=None):
#     """
#     Given an optional list of frames (defaults to current stack),
#     iterates over all frames that do not contain the ``__traceback_hide__``
#     local variable.
#     """
#     if not frames:
#         frames = inspect.stack()[1:]
#
#     for frame, lineno in ((f[0], f[2]) for f in frames):
#         f_locals = getattr(frame, 'f_locals', {})
#         if _getitem_from_frame(f_locals, '__traceback_hide__'):
#             continue
#         yield frame, lineno
#
# def _getitem_from_frame(f_locals, key, default=None):
#     """
#     f_locals is not guaranteed to have .get(), but it will always
#     support __getitem__. Even if it doesnt, we return ``default``.
#     """
#     try:
#         return f_locals[key]
#     except Exception:
#         return default


class NoAppFoundError(click.UsageError):
    """Raised if an application cannot be found or loaded."""


@click.group()
@click.option('--debug/--no-debug', default=False)
@click.pass_context
def cli(ctx, debug):
    ctx.obj['DEBUG'] = debug

@cli.command('run', short_help='Runs a development server.')
@click.option('--host', '-h', default='127.0.0.1',
              help='The interface to bind to.')
@click.option('--port', '-p', type=int, default=8000,
              help='The port to bind to.')
@click.option('--debug/--no-debug', default=False)
@click.option('--watch-dir', '-w', multiple=True,
              default=['./'], show_default=True,
              help="watch changes of files in directory in debug mode")
@click.pass_context
def run_command(ctx, host, port, debug, watch_dir):
    debug = debug or ctx.obj['DEBUG']

    import traceback

    app_module = lookup_app_module()
    app_runinfo = find_best_app_factory(app_module)

    if not debug:
        from aiohttp.web import run_app as aiohttp_run_app
        aiohttp_run_app(app_factory(), port=port, host=host)
    else:
        from .run_app import autoreload_app
        watch_dir = [str(Path(d).resolve()) for d in watch_dir]
        autoreload_app(app_runinfo, port=port, host=host, work_paths=watch_dir)
