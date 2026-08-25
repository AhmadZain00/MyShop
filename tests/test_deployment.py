from pathlib import Path

def test_deployment_files_exist():
    root = Path(__file__).resolve().parents[1]
    for rel in ["MyShop.spec", "build.bat", "build_installer.bat", "installer/MyShop.iss"]:
        assert (root/rel).exists(), rel
