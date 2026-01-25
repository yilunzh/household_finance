#!/usr/bin/env python3
"""
Add Design system files to the Xcode project properly.
Creates groups and adds file references correctly.
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


def main():
    print("Adding Design system files to Xcode project...")

    # Read the project file
    with open(PROJECT_FILE, 'r') as f:
        content = f.read()

    # Get existing UUIDs to avoid conflicts
    existing_uuids = get_existing_uuids(content)

    def new_uuid():
        while True:
            u = generate_uuid()
            if u not in existing_uuids:
                existing_uuids.add(u)
                return u

    # Generate UUIDs for groups and files
    design_group_uuid = new_uuid()
    components_group_uuid = new_uuid()

    # Files to add - format: (filename, folder, file_uuid, build_uuid)
    design_files = []
    component_files = []

    # Design folder files
    for filename in ["Colors.swift", "Typography.swift", "Spacing.swift", "CatIcon.swift", "HapticManager.swift"]:
        design_files.append((filename, new_uuid(), new_uuid()))

    # Components folder files
    for filename in ["Buttons.swift", "CardContainer.swift", "Badge.swift", "EmptyState.swift", "InputField.swift", "CustomTabBar.swift"]:
        component_files.append((filename, new_uuid(), new_uuid()))

    # 1. Add PBXFileReference entries
    file_ref_marker = "/* End PBXFileReference section */"
    new_refs = ""

    for filename, file_uuid, _ in design_files + component_files:
        new_refs += f'\t\t{file_uuid} /* {filename} */ = {{isa = PBXFileReference; lastKnownFileType = sourcecode.swift; path = {filename}; sourceTree = "<group>"; }};\n'

    content = content.replace(file_ref_marker, new_refs + file_ref_marker)

    # 2. Add PBXBuildFile entries
    build_file_marker = "/* End PBXBuildFile section */"
    new_builds = ""

    for filename, file_uuid, build_uuid in design_files + component_files:
        new_builds += f'\t\t{build_uuid} /* {filename} in Sources */ = {{isa = PBXBuildFile; fileRef = {file_uuid} /* {filename} */; }};\n'

    content = content.replace(build_file_marker, new_builds + build_file_marker)

    # 3. Create group entries
    group_marker = "/* End PBXGroup section */"

    # Components group
    component_children = ",\n".join([f'\t\t\t\t{file_uuid} /* {filename} */' for filename, file_uuid, _ in component_files])
    components_group = f'''		{components_group_uuid} /* Components */ = {{
			isa = PBXGroup;
			children = (
{component_children},
			);
			path = Components;
			sourceTree = "<group>";
		}};
'''

    # Design group
    design_children = ",\n".join([f'\t\t\t\t{file_uuid} /* {filename} */' for filename, file_uuid, _ in design_files])
    design_group = f'''		{design_group_uuid} /* Design */ = {{
			isa = PBXGroup;
			children = (
{design_children},
				{components_group_uuid} /* Components */,
			);
			path = Design;
			sourceTree = "<group>";
		}};
'''

    content = content.replace(group_marker, components_group + design_group + group_marker)

    # 4. Add Design group to HouseholdTracker main group
    # Find the HouseholdTracker group and add Design to its children
    # Look for the group that contains ContentView.swift, MainTabView.swift, etc.
    household_group_pattern = r'((?:[A-F0-9]{24}) /\* HouseholdTracker \*/ = \{[^}]*children = \([^)]*)(C11FEFAB2BC32A5A1A1B5722 /\* ContentView\.swift \*/)'

    def add_design_to_group(match):
        return match.group(1) + f'{design_group_uuid} /* Design */,\n\t\t\t\t' + match.group(2)

    content = re.sub(household_group_pattern, add_design_to_group, content, flags=re.DOTALL)

    # 5. Add files to Sources build phase
    # Find the sources phase files array and add new entries
    sources_pattern = r'(6AEE507F4D953BAE85BF8592 /\* Sources \*/ = \{[^}]*files = \([^)]*)'

    build_entries = ""
    for filename, _, build_uuid in design_files + component_files:
        build_entries += f'\n\t\t\t\t{build_uuid} /* {filename} in Sources */,'

    def add_to_sources(match):
        return match.group(1) + build_entries

    content = re.sub(sources_pattern, add_to_sources, content, flags=re.DOTALL)

    # Write back
    with open(PROJECT_FILE, 'w') as f:
        f.write(content)

    print(f"  Created Design group: {design_group_uuid}")
    print(f"  Created Components group: {components_group_uuid}")
    print(f"  Added {len(design_files)} Design files")
    print(f"  Added {len(component_files)} Components files")
    print("\nDone! Project file updated.")


if __name__ == "__main__":
    main()
