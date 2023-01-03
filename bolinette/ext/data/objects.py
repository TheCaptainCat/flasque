from bolinette import environment
from bolinette.ext.data import __data_cache__


class _DatabaseSection:
    name: str
    url: str
    echo: bool = False


@environment("data", cache=__data_cache__)
class DataSection:
    databases: list[_DatabaseSection]