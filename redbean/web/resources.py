from yarl import URL
from pathlib import Path
from aiohttp.web import FileResponse
from aiohttp.web import HTTPForbidden, HTTPNotFound


def redirect_not_found(app, path=None, prefix=None):

    def _redirect_not_found_handler(request):
        return HTTPNotFound()

    resource = app.router.add_resource(path)
    resource.add_route('GET', _redirect_not_found_handler)
    resource.add_route('HEAD', _redirect_not_found_handler)


def webapp_static_reources(app, prefix, directory, *,
                           index_file='index.html',
                           chunk_size: int = 256 * 1024):

    directory = directory.resolve()

    def get_filepath(filename, request):
        if filename[0] == '/':
            filename = filename[1:]

        try:
            filename = Path(filename)
            filepath = directory.joinpath(filename).resolve()

            filepath.relative_to(directory)  # relatively safe
            return filepath
        except (ValueError, FileNotFoundError) as error:
            raise HTTPNotFound() from error

        except HTTPForbidden:
            raise

        except Exception as error:
            request.app.logger.exception(error)
            raise HTTPNotFound() from error

    async def _handler(request):
        filepath = request.match_info['path']
        if filepath:
            filepath = URL.build(path=filepath, encoded=True).path
            filepath = get_filepath(filepath, request)
        else:
            filepath = get_filepath(index_file, request)

        if filepath.is_dir():
            raise HTTPForbidden()
        elif not filepath.is_file():
            filepath = get_filepath(index_file, request)
            if not filepath.is_file():
                raise HTTPNotFound()

        return FileResponse(filepath, chunk_size=chunk_size)

    path = prefix + '{path:.*}'
    resource = app.router.add_resource(path)
    resource.add_route('GET', _handler)
    resource.add_route('HEAD', _handler)
