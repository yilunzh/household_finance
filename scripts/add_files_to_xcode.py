#!/usr/bin/env python3
"""
Add new Swift files to the Xcode project.
This script modifies project.pbxproj to include the Design system files.
"""

import os
import re
import uuid
from pathlib import Path

PROJECT_FILE = Path(__file__).parent.parent / "ios" / "HouseholdTracker" / "HouseholdTracker.xcodeproj" / "project.pbxproj"


def generate_uuid():
    """Generate a 24-character UUID for Xcode."""
    return uuid.uuid4().hex[:24].upper()


def get_existing_uuids(content):
    """Get all existing UUIDs in the project."""
    return set(re.findall(r'[A-F0-9]{24}', content))


def find_group_uuid(content, group_name):
    """Find the UUID of a group by name."""
    pattern = rf'([A-F0-9]{{24}}) /\* {re.escape(group_name)} \*/ = \{{'
    match = re.search(pattern, content)
    return match.group(1) if match else None


def find_build_phase_uuid(content, phase_name="Sources"):
    """Find the build sources phase UUID."""
    # Look for the Sources build phase
    pattern = r'([A-F0-9]{24}) /\* Sources \*/ = \{[^}]*isa = PBXSourcesBuildPhase'
    match = re.search(pattern, content, re.DOTALL)
    return match.group(1) if match else None


def add_file_reference(content, file_uuid, file_name, file_path, existing_uuids):
    """Add a file reference to PBXFileReference section."""
    # Find the end of PBXFileReference section
    marker = "/* End PBXFileReference section */"

    new_ref = f'\t\t{file_uuid} /* {file_name} */ = {{isa = PBXFileReference; lastKnownFileType = sourcecode.swift; path = {file_name}; sourceTree = "<group>"; }};\n'

    return content.replace(marker, new_ref + marker)


def add_build_file(content, build_uuid, file_uuid, file_name):
    """Add a build file reference to PBXBuildFile section."""
    marker = "/* End PBXBuildFile section */"

    new_ref = f'\t\t{build_uuid} /* {file_name} in Sources */ = {{isa = PBXBuildFile; fileRef = {file_uuid} /* {file_name} */; }};\n'

    return content.replace(marker, new_ref + marker)


def add_to_sources_phase(content, build_uuid, file_name, sources_uuid):
    """Add build file to the sources build phase."""
    # Find the Sources build phase and add to its files array
    pattern = rf'({sources_uuid} /\* Sources \*/ = \{{[^}}]*files = \([^)]*)'

    def replacer(match):
        return match.group(1) + f'\n\t\t\t\t{build_uuid} /* {file_name} in Sources */,'

    return re.sub(pattern, replacer, content, flags=re.DOTALL)


def create_design_group(content, parent_group_uuid, existing_uuids):
    """Create the Design group structure."""
    # Generate UUIDs for the groups
    while True:
        design_group_uuid = generate_uuid()
        if design_group_uuid not in existing_uuids:
            existing_uuids.add(design_group_uuid)
            break

    while True:
        components_group_uuid = generate_uuid()
        if components_group_uuid not in existing_uuids:
            existing_uuids.add(components_group_uuid)
            break

    return design_group_uuid, components_group_uuid


def main():
    print("Adding Design system files to Xcode project...")

    # Read the project file
    with open(PROJECT_FILE, 'r') as f:
        content = f.read()

    # Get existing UUIDs to avoid conflicts
    existing_uuids = get_existing_uuids(content)

    # Files to add
    design_files = [
        ("Colors.swift", "Design"),
        ("Typography.swift", "Design"),
        ("Spacing.swift", "Design"),
        ("CatIcon.swift", "Design"),
        ("HapticManager.swift", "Design"),
    ]

    component_files = [
        ("Buttons.swift", "Design/Components"),
        ("CardContainer.swift", "Design/Components"),
        ("Badge.swift", "Design/Components"),
        ("EmptyState.swift", "Design/Components"),
        ("InputField.swift", "Design/Components"),
        ("CustomTabBar.swift", "Design/Components"),
    ]

    # Find the Sources build phase UUID
    # Look for pattern: UUID /* Sources */ = { isa = PBXSourcesBuildPhase
    sources_match = re.search(r'([A-F0-9]{24}) /\* Sources \*/ = \{[^}]*isa = PBXSourcesBuildPhase', content)
    if not sources_match:
        print("ERROR: Could not find Sources build phase")
        return

    sources_phase_uuid = sources_match.group(1)
    print(f"Found Sources build phase: {sources_phase_uuid}")

    # Add file references and build files
    all_files = design_files + component_files

    for file_name, folder in all_files:
        # Generate UUIDs
        while True:
            file_uuid = generate_uuid()
            if file_uuid not in existing_uuids:
                existing_uuids.add(file_uuid)
                break

        while True:
            build_uuid = generate_uuid()
            if build_uuid not in existing_uuids:
                existing_uuids.add(build_uuid)
                break

        # Add file reference
        content = add_file_reference(content, file_uuid, file_name, f"{folder}/{file_name}", existing_uuids)

        # Add build file
        content = add_build_file(content, build_uuid, file_uuid, file_name)

        # Add to sources phase
        content = add_to_sources_phase(content, build_uuid, file_name, sources_phase_uuid)

        print(f"  Added: {file_name}")

    # Write back
    with open(PROJECT_FILE, 'w') as f:
        f.write(content)

    print("\nDone! Files added to project.")
    print("NOTE: You may need to open Xcode and organize the files into groups manually.")


if __name__ == "__main__":
    main()
