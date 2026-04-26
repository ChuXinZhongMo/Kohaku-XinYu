"""CLI extension commands -- list and inspect package extension modules."""

from kohakuterrarium.packages import get_package_modules, list_packages
from kohakuterrarium.utils.logging import get_logger

logger = get_logger(__name__)

_MODULE_TYPES = ("tools", "plugins", "llm_presets")


def extension_list_cli() -> int:
    """Show all installed extension modules (tools, plugins, presets)."""
    packages = list_packages()
    if not packages:
        print("No packages installed.")
        return 0

    found_any = False
    for pkg in packages:
        counts = {mt: len(pkg.get(mt, [])) for mt in _MODULE_TYPES}
        if not any(counts.values()):
            continue

        found_any = True
        editable_tag = " (editable)" if pkg["editable"] else ""
        print(f"{pkg['name']} v{pkg['version']}{editable_tag}")
        if pkg.get("description"):
            print(f"  {pkg['description']}")
        for mt in _MODULE_TYPES:
            items = pkg.get(mt, [])
            if items:
                label = mt.replace("_", " ")
                names = [(i["name"] if isinstance(i, dict) else str(i)) for i in items]
                print(f"  {label} ({len(items)}): {', '.join(names)}")
        print()

    if not found_any:
        print("No extension modules found in installed packages.")

    return 0


def extension_info_cli(name: str) -> int:
    """Show details of a specific package's extension modules."""
    # Verify the package exists
    packages = list_packages()
    pkg_match = [p for p in packages if p["name"] == name]
    if not pkg_match:
        print(f"Package not found: {name}")
        return 1

    pkg = pkg_match[0]
    editable_tag = " (editable)" if pkg["editable"] else ""
    print(f"Package: {pkg['name']} v{pkg['version']}{editable_tag}")
    if pkg.get("description"):
        print(f"Description: {pkg['description']}")
    print(f"Path: {pkg['path']}")
    print()

    all_types = ("creatures", "terrariums", *_MODULE_TYPES)
    for module_type in all_types:
        modules = get_package_modules(name, module_type)
        if not modules:
            continue
        label = module_type.replace("_", " ").title()
        print(f"{label} ({len(modules)}):")
        for mod in modules:
            if isinstance(mod, dict):
                mod_name = mod.get("name", "?")
                desc = mod.get("description", "")
                line = f"  - {mod_name}"
                if desc:
                    line += f": {desc}"
                if mod.get("module"):
                    line += f"  [{mod['module']}]"
                print(line)
            else:
                print(f"  - {mod}")
        print()

    return 0
