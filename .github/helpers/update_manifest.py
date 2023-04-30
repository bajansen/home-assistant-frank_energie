"""Update the manifest file.

Sets the version number in the manifest file to the version number
"""

import sys
import json
import os


def update_manifest():
    """Update the manifest file."""
    version = "0.0.0"
    for index, value in enumerate(sys.argv):
        if value in ["--version", "-V"]:
            version = sys.argv[index + 1]

    # Remove the v from the version number if it exists
    if version[0] == "v":
        version = version[1:]

    with open(
        f"{os.getcwd()}/custom_components/frank_energie/manifest.json"
    ) as manifestfile:
        manifest = json.load(manifestfile)

    manifest["version"] = version

    with open(
        f"{os.getcwd()}/custom_components/frank_energie/manifest.json", "w"
    ) as manifestfile:
        manifestfile.write(json.dumps(manifest, indent=4, sort_keys=True))


update_manifest()
