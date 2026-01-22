from __future__ import annotations
from LSP.plugin import AbstractPlugin
from LSP.plugin import ClientConfig
from LSP.plugin import register_plugin
from LSP.plugin import unregister_plugin
from pathlib import Path
from typing import final
from typing_extensions import override
import os
import shutil
import sublime
import tarfile
import urllib.request
import zipfile


SESSION_NAME = "LSP-pyproject"

TAG = "0.1.2"
"""
Update this single git tag to download a newer version.
"""

URL = "https://github.com/terror/pyproject/releases/download/{tag}/pyproject-{tag}-{arch}-{platform}.{ext}"


def arch() -> str:
    if sublime.arch() == "x64":
        return "x86_64"
    if sublime.arch() == "x32":
        raise RuntimeError("Unsupported platform: 32-bit is not supported")
    if sublime.arch() == "arm64":
        return "aarch64"
    raise RuntimeError("Unknown architecture: " + sublime.arch())


def platform() -> str:
    if sublime.platform() == "windows":
        return "pc-windows-msvc"
    if sublime.platform() == "osx":
        return "apple-darwin"
    return "unknown-linux-gnu"


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
            url = URL.format(tag=TAG, arch=arch(), platform=platform(), ext=extension)
            archive_file = os.path.join(cls.basedir(), f"pyproject.{extension}")
            server_binary_filename = "pyproject.exe" if is_windows else "pyproject"
            server_binary_path = os.path.join(cls.basedir(), server_binary_filename)
            with urllib.request.urlopen(url) as fp:
                with open(archive_file, "wb") as f:
                    f.write(fp.read())
            if is_windows:
                with zipfile.ZipFile(archive_file, "r") as zip_ref:
                    zip_ref.extract(server_binary_filename, cls.basedir())
            else:
                with tarfile.open(archive_file) as fp:
                    names = fp.getnames()
                    install_dir, _ = next(x for x in names if '/' in x).split('/', 1)
                    bad_members = [x for x in names if x.startswith('/') or x.startswith('..')]
                    if bad_members:
                        raise Exception(f'{archive_file} appears to be malicious, bad filenames: {bad_members}')
                    fp.extractall(cls.basedir())
                    # with chdir(cls.basedir()):
                    #     os.rename(install_dir, 'node')
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
