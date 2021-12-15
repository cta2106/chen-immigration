from pathlib import Path

from src.exceptions import DirectoryError


class _Directories:
    def __init__(self):
        self.project = Path(__file__).parents[2].resolve()
        self.package = self.project / "src"
        self.data = self.project / "data"
        self.output = self.project / "output"
        self.config = self.package / "config"
        self.images = self.package / "images"
        self.html = self.package / "html"

        for dir_path in vars(self).values():
            try:
                dir_path.mkdir(exist_ok=True, parents=True)
            except Exception as e:
                raise DirectoryError(
                    f"Either '{dir_path}' is not a directory, "
                    "or it can't be created. "
                    f"Make sure all attributes of {self.__class__} "
                    "are actual directory paths."
                ) from e


directories = _Directories()
