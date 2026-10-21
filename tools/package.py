# -*- coding: utf-8 -*-
# =================================================
#  ⠀
#   Author: Nuoyan <https://github.com/charminglee>
#   Email : 1279735247@qq.com
#   Date  : 2026-10-21
#  ⠀
# =================================================


import hashlib
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]


# region Package Generation ==================================================


def main():
    """
    打包行为包与资源包并校验必需文件和摘要。
    """
    # 固定交付文件名，先创建输出目录。
    target = ROOT / "dist/DualVectorFoil-0.1.0.zip"
    target.parent.mkdir(exist_ok=True)
    count = 0
    # 仅收集源包文件并排除缓存。
    with ZipFile(target, "w", ZIP_DEFLATED) as archive:
        for path in sorted((ROOT / "src").rglob("*")):
            if (
                not path.is_file()
                or path.suffix in (".pyc", ".pyo")
                or "__pycache__" in path.parts
            ):
                continue
            archive.write(path, path.relative_to(ROOT / "src"))
            count += 1
    # 重新打开归档，验证完整性、必需路径和内容一致性。
    with ZipFile(target) as archive:
        assert not archive.testzip()
        assert "bp/manifest.json" in archive.namelist()
        assert "rp/manifest.json" in archive.namelist()
        required = (
            "bp/dualvectorfoil_scripts/modules/effect/__init__.py",
            "bp/dualvectorfoil_scripts/modules/effect/client.py",
            "bp/dualvectorfoil_scripts/modules/effect/server.py",
            "bp/dualvectorfoil_scripts/modules/effect/config.py",
            "bp/dualvectorfoil_scripts/modules/foil/__init__.py",
            "bp/dualvectorfoil_scripts/modules/foil/client.py",
            "bp/dualvectorfoil_scripts/modules/foil/server.py",
            "bp/dualvectorfoil_scripts/modules/foil/config.py",
            "rp/materials/postprocess.material",
            "rp/graphics_settings/post_process.json",
            "rp/graphics_settings/post_process_rngl.json",
            "rp/shaders/dual_vector_foil/glsl/space_fall.vertex",
            "rp/shaders/dual_vector_foil/glsl/space_fall.fragment",
        )
        for relative in required:
            assert archive.read(relative) == (ROOT / "src" / relative).read_bytes(), relative
        # 两个业务模块目录只允许约定文件，防止拆分后遗留实现副本。
        for package in ("effect", "foil"):
            prefix = "bp/dualvectorfoil_scripts/modules/%s/" % package
            files = {name[len(prefix):] for name in archive.namelist() if name.startswith(prefix)}
            assert files == {"__init__.py", "client.py", "server.py", "config.py"}, files
    # 写出 SHA-256 校验文件并打印交付摘要。
    checksum = hashlib.sha256(target.read_bytes()).hexdigest()
    checksum_text = checksum + "  " + target.name + "\n"
    checksum_path = target.parent / (target.name + ".sha256")
    checksum_path.write_text(checksum_text, encoding="ascii")
    print(str(target))
    print("files:", count, "bytes:", target.stat().st_size, "sha256:", checksum)


# endregion


if __name__ == "__main__":
    main()
