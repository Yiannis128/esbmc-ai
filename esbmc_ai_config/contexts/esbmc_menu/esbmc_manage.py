# Author: Yiannis Charalambous

import os
from pathlib import Path
import shutil
from typing_extensions import override
import requests
from requests.status_codes import codes as status_codes
from platform import system as system_name
from zipfile import ZipFile

import urwid
from esbmc_ai_config.context_manager import ContextManager

from esbmc_ai_config.contexts.dialog_context import DialogContext
from esbmc_ai_config.models import ConfigManager
from esbmc_ai_config.context import Context
from esbmc_ai_config.widgets.back_button import BackButton


class ESBMCManage(Context):
    license_url: str = "https://raw.githubusercontent.com/esbmc/esbmc/master/COPYING"

    def __init__(self) -> None:
        if self.license_accepted:
            self.license: str = ""
        else:
            response: requests.Response = requests.get(ESBMCManage.license_url)
            if response.status_code == status_codes.ok:
                self.license: str = response.text
            else:
                self.license: str = (
                    f"Couldn't get the license: status code: {response.status_code}"
                )

        super().__init__(self.build_ui())

    @property
    def license_accepted(self) -> bool:
        return bool(ConfigManager.env_config.values["ESBMC_LICENSE_AGREEMENT"])

    @license_accepted.setter
    def license_accepted(self, value: bool) -> None:
        ConfigManager.env_config.values["ESBMC_LICENSE_AGREEMENT"] = value
        ConfigManager.env_config.save()

    def _get_esbmc_zip_name(self) -> str:
        match system_name():
            case "Windows":
                return "esbmc-windows.zip"
            case "Linux":
                return "esbmc-linux.zip"
            case _:
                raise ValueError(f"No compatible ESBMC version found: {system_name()}")

    def _get_esbmc_url(self) -> str:
        # Source: https://gist.github.com/lukechilds/a83e1d7127b78fef38c2914c4ececc3c
        # Will automatically assign the latest tag, which we can use to download the
        # file. Since for downloads, supplying "latest" does not work.
        r = requests.get("https://github.com/esbmc/esbmc/releases/latest")
        version = r.url.split("/")[-1]
        return f"https://github.com/esbmc/esbmc/releases/download/{version}/{self._get_esbmc_zip_name()}"

    def _on_accept_license(self, button) -> None:
        self.license_accepted = True
        self.frame.set_body(self._build_ui())

    def _build_ui_license_agreement(self) -> urwid.Widget:
        body: list[urwid.Widget] = [
            urwid.Divider(),
            urwid.Text("Read and accept the license agreement of ESBMC"),
            urwid.Divider(),
            urwid.Text(self.license),
            urwid.Columns(
                [
                    BackButton(),
                    urwid.AttrMap(
                        urwid.Button(
                            "Accept License and Save to Env",
                            on_press=self._on_accept_license,
                        ),
                        None,
                        focus_map="reversed",
                    ),
                ]
            ),
        ]

        return urwid.ScrollBar(urwid.ListBox(urwid.SimpleFocusListWalker(body)))

    def _on_press_install_esbmc(self, button) -> None:
        response: requests.Response = requests.get(self._get_esbmc_url(), stream=True)
        if response.status_code != status_codes.ok:
            ContextManager.push_context(
                DialogContext(
                    "ESBMC Install Failed",
                    f"{self._get_esbmc_url()}\n\n{response.text}",
                )
            )
            return

        # Write to temp file.
        tmp_dir: Path
        match system_name():
            case "Windows":
                win_app_data: str = os.path.expandvars("%localappdata%")
                tmp_dir = Path(win_app_data) / "Temp"
            case "Darwin" | "Linux":
                tmp_dir = Path("/tmp")
            case _:
                raise ValueError(f"OS not compatible: {system_name()}")

        tmp_dir /= self._get_esbmc_zip_name()

        # Extract zip
        with open(tmp_dir, "wb") as file:
            for chunk in response.iter_content(chunk_size=128):
                file.write(chunk)

        extract_dir: Path = Path(str(tmp_dir).removesuffix(".zip"))

        zip_file: ZipFile = ZipFile(tmp_dir)
        zip_file.extract(
            f"bin/{ConfigManager.get_esbmc_name()}",
            extract_dir,
        )

        # Copy file to correct location
        shutil.move(
            extract_dir / "bin" / ConfigManager.get_esbmc_name(),
            ConfigManager.get_esbmc_path(),
        )

        # Set permissions
        # U=RWE G=RX O=
        os.chmod(ConfigManager.get_esbmc_path(), 0o755)

        ContextManager.pop_context()
        ContextManager.push_context(
            DialogContext(
                "ESBMC Install Completed",
                f"ESBMC has been successfully installed at {ConfigManager.get_esbmc_path()}. "
                'The "ESBMC Path" setting has also been automatically set.',
            )
        )

    def _on_press_uninstall_esbmc(self, button) -> None:
        if os.path.isfile(ConfigManager.get_esbmc_path()):
            os.remove(ConfigManager.get_esbmc_path())

            ContextManager.push_context(
                DialogContext(
                    "ESBMC Uninstall Completed",
                    f"ESBMC has been uninstalled from {ConfigManager.get_esbmc_dir()}. The folder "
                    "however, has not been deleted.",
                )
            )
        else:
            ContextManager.push_context(
                DialogContext(
                    "ESBMC Uninstall Failed",
                    f"ESBMC is not found at {ConfigManager.get_esbmc_dir()}.",
                )
            )

    def _build_ui(self) -> urwid.Widget:
        body: list[urwid.Widget] = [
            urwid.Divider(),
            urwid.Text(f"ESBMC bin folder: {ConfigManager.get_esbmc_dir()}"),
            urwid.Divider(),
            urwid.Text(
                f"This tool will download the latest version of ESBMC from GitHub, "
                "extract the archive and automatically install it in the directory listed "
                'above. The setting "ESBMC Path" will also be automatically set to point '
                "there as well. After pressing download and installl, please wait for the "
                "process to complete."
            ),
            urwid.Divider(),
            urwid.AttrMap(
                urwid.Button(
                    "Download Latest Version", on_press=self._on_press_install_esbmc
                ),
                None,
                "reversed",
            ),
            urwid.AttrMap(
                urwid.Button(
                    "Uninstall ESBMC", on_press=self._on_press_uninstall_esbmc
                ),
                None,
                "reversed",
            ),
            BackButton(),
        ]

        return urwid.ScrollBar(urwid.ListBox(urwid.SimpleFocusListWalker(body)))

    @override
    def build_ui(self) -> urwid.Widget:
        content: urwid.Widget
        if self.license_accepted:
            content = self._build_ui()
        else:
            content = self._build_ui_license_agreement()

        self.frame: urwid.Frame = urwid.Frame(
            header=urwid.Text("Install ESBMC"),
            footer=urwid.Text("www.esbmc.org"),
            body=content,
            focus_part="body",
        )

        return self.frame
