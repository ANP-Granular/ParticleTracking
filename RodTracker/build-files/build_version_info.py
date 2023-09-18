from pathlib import Path
from RodTracker._version import __version__
import PyInstaller.utils.win32.versioninfo as v_info

version_tuple = tuple(
    int(num) for num in __version__.split(".") if num.isnumeric()
)
if len(version_tuple) < 4:
    version_tuple = (*version_tuple, *((4 - len(version_tuple)) * [0]))
elif len(version_tuple) > 4:
    version_tuple = version_tuple[0:4]

new_version_info = v_info.VSVersionInfo(
    ffi=v_info.FixedFileInfo(
        # filevers and prodvers should be always a tuple with four items:
        #   (1, 2, 3, 4)
        # Set not needed items to zero 0.
        filevers=version_tuple,
        prodvers=version_tuple,
        # Contains a bitmask that specifies the valid bits 'flags'r
        mask=0x3F,
        # Contains a bitmask that specifies the Boolean attributes of the file.
        flags=0x0,
        # The operating system for which this file was designed.
        # 0x4 - NT and there is no need to change it.
        OS=0x4,
        # The general type of file.
        # 0x1 - the file is an application.
        fileType=0x1,
        # The function of the file.
        # 0x0 - the function is not defined for this fileType
        subtype=0x0,
        # Creation date and time stamp.
        date=(0, 0),
    ),
    kids=[
        v_info.StringFileInfo(
            [
                v_info.StringTable(
                    "040904b0",
                    [
                        v_info.StringStruct(
                            "CompanyName",
                            "Otto-von-Guericke University Magdeburg",
                        ),
                        v_info.StringStruct("FileDescription", "RodTracker"),
                        v_info.StringStruct("FileVersion", __version__),
                        v_info.StringStruct("InternalName", "RodTracker"),
                        v_info.StringStruct(
                            "LegalCopyright",
                            "Copyright (c) 2023 Adrian Niemann, "
                            "Dmitry Puzyrev",
                        ),
                        v_info.StringStruct(
                            "OriginalFilename", "RodTrackerApp.exe"
                        ),
                        v_info.StringStruct("ProductName", "RodTracker"),
                        v_info.StringStruct("ProductVersion", __version__),
                        v_info.StringStruct("Language", "English"),
                        v_info.StringStruct("", ""),
                    ],
                )
            ]
        ),
        v_info.VarFileInfo([v_info.VarStruct("Translation", [1033, 1200])]),
    ],
)

out_file = Path(__file__).parent / "version_info.txt"
with open(out_file, "w") as f:
    f.write(new_version_info.__str__())
