from __future__ import annotations

from http.client import HTTPResponse
from LSP.plugin import IsApplicableContext
from LSP.plugin import LspPlugin
from LSP.plugin import OnPreStartContext
from pathlib import Path
from typing import cast
from typing import final
from typing_extensions import override
import shutil
import sublime
import tarfile
import urllib.request
import zipfile

TAG = "0.1.3"
ARTIFACT_URL = "https://github.com/terror/pyproject/releases/download/{tag}/{filename}"
ARTIFACT_ARCH_MAPPING = {
    'x64': 'x86_64',
    'arm64': 'aarch64',
    'x32': False,
}
ARTIFACT_PLATFORM_MAPPING = {
    'windows': 'pc-windows-msvc',
    'osx': 'apple-darwin',
    'linux': 'unknown-linux-gnu',
}


def get_artifact_name() -> str:
    sublime_arch = sublime.arch()
    arch = ARTIFACT_ARCH_MAPPING[sublime_arch]
    if arch is False:
        raise RuntimeError(f'Unsupported architecture: {sublime_arch}')
    sublime_platform = sublime.platform()
    platform = ARTIFACT_PLATFORM_MAPPING[sublime_platform]
    extension = 'zip' if sublime_platform == 'windows' else 'tar.gz'
    return f'pyproject-{TAG}-{arch}-{platform}.{extension}'


@final
class LspPyproject(LspPlugin):

    @classmethod
    @override
    def on_pre_start_async(cls, context: OnPreStartContext) -> None:
        if cls.needs_update_or_installation():
            cls.install_or_update()

    @classmethod
    def basedir(cls) -> Path:
        return cls.plugin_storage_path

    @classmethod
    def server_version(cls) -> str:
        return TAG

    @classmethod
    def current_server_version(cls) -> str:
        with open(cls.basedir() / "VERSION", "r") as fp:
            return fp.read()

    @classmethod
    @override
    def is_applicable_async(cls, context: IsApplicableContext) -> bool:
        is_applicable = super().is_applicable_async(context)
        return is_applicable and bool(filename := context.view.file_name()) and Path(filename).name == 'pyproject.toml'

    @classmethod
    def needs_update_or_installation(cls) -> bool:
        try:
            return cls.server_version() != cls.current_server_version()
        except OSError:
            return True

    @classmethod
    def install_or_update(cls) -> None:
        try:
            if cls.basedir().is_dir():
                shutil.rmtree(cls.basedir())
            cls.basedir().mkdir(parents=True, exist_ok=True)
            version = cls.server_version()
            is_windows = sublime.platform() == "windows"
            extension = "zip" if is_windows else "tar.gz"
            archive_file = cls.basedir() / f"artifact.{extension}"
            server_binary_filename = "pyproject.exe" if is_windows else "pyproject"
            url = ARTIFACT_URL.format(tag=TAG, filename=get_artifact_name())
            with urllib.request.urlopen(url) as fp:
                with open(archive_file, "wb") as f:
                    f.write(cast(HTTPResponse, fp).read())
            if is_windows:
                with zipfile.ZipFile(archive_file, "r") as zip_ref:
                    zip_ref.extract(server_binary_filename, cls.basedir())
            else:
                with tarfile.open(archive_file) as fp:
                    names = fp.getnames()
                    bad_members = [x for x in names if x.startswith('/') or x.startswith('..')]
                    if bad_members:
                        raise Exception(f'{archive_file} appears to be malicious, bad filenames: {bad_members}')
                    fp.extractall(cls.basedir())
            archive_file.unlink()
            with open(cls.basedir() / "VERSION", "w") as fp:
                fp.write(version)
        except BaseException:
            shutil.rmtree(cls.basedir(), ignore_errors=True)
            raise


def plugin_loaded() -> None:
    LspPyproject.register()


def plugin_unloaded() -> None:
    LspPyproject.unregister()
