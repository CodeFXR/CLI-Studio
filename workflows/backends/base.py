from typing import ClassVar


class Backend:
    """Base contract for a wrapped CLI tool.

    A concrete backend owns the command-construction for one external tool
    (ffmpeg, yt-dlp, Pillow, etc.). It declares:

    - `name`: a unique lowercase identifier used for lookup.
    - `operations`: the set of operation tags this backend can handle
      (e.g. `{"download_video", "download_audio"}`).
    - `supports(op)`: returns whether the backend can serve `op`.

    Constructor signatures differ across backends (some accept an
    executable override, others don't), so `__init__` is not part of the
    formal contract; only `name` and `operations` are. Validation happens
    in `__init_subclass__` below.

    See `BackendRegistry` for lookup and registration.
    """

    name: ClassVar[str] = ""
    operations: ClassVar[frozenset[str]] = frozenset()

    def supports(self, operation: str) -> bool:
        return operation in self.operations

    def __repr__(self) -> str:
        return f"<{type(self).__name__} name={self.name!r} ops={sorted(self.operations)}>"

    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        if not cls.name:
            raise TypeError(f"{cls.__name__} must set class attribute 'name'")
        if not cls.operations:
            raise TypeError(f"{cls.__name__} must set class attribute 'operations'")
