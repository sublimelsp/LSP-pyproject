from __future__ import annotations
from http.client import HTTPResponse
from LSP.plugin import AbstractPlugin
from LSP.plugin import ClientConfig
from LSP.plugin import register_plugin
from LSP.plugin import unregister_plugin
from pathlib import Path
from typing import cast, final
from typing_extensions import override
import os
import shutil
import sublime
import tarfile
import urllib.request
import zipfile


TAG = "0.1.2"
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
class LspPyproject(AbstractPlugin):

    @classmethod
    @override
    def name(cls) -> str:
        return 'pyproject'

    @classmethod
    def basedir(cls) -> str:
        return os.path.join(cls.storage_path(), str(__package__))

    @classmethod
    def server_version(cls) -> str:
        return TAG

    @classmethod
    def current_server_version(cls) -> str:
        with open(os.path.join(cls.basedir(), "VERSION"), "r") as fp:
            return fp.read()

    @classmethod
    @override
    def is_applicable(cls, view: sublime.View, config: ClientConfig) -> bool:
        is_applicable = super().is_applicable(view, config)
        return is_applicable and bool(filename := view.file_name()) and Path(filename).name == 'pyproject.toml'

    @classmethod
    @override
    def needs_update_or_installation(cls) -> bool:
        try:
            return cls.server_version() != cls.current_server_version()
        except OSError:
            return True

    @classmethod
    @override
    def install_or_update(cls) -> None:
        try:
            if os.path.isdir(cls.basedir()):
                shutil.rmtree(cls.basedir())
            os.makedirs(cls.basedir(), exist_ok=True)
            version = cls.server_version()
            is_windows = sublime.platform() == "windows"
            extension = "zip" if is_windows else "tar.gz"
            archive_file = os.path.join(cls.basedir(), f"artifact.{extension}")
            server_binary_filename = "pyproject.exe" if is_windows else "pyproject"
            server_binary_path = os.path.join(cls.basedir(), server_binary_filename)
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
            os.remove(archive_file)
            os.chmod(server_binary_path, 0o744)
            with open(os.path.join(cls.basedir(), "VERSION"), "w") as fp:
                fp.write(version)
        except BaseException:
            shutil.rmtree(cls.basedir(), ignore_errors=True)
            raise


def plugin_loaded() -> None:
    register_plugin(LspPyproject)


def plugin_unloaded() -> None:
    unregister_plugin(LspPyproject)
