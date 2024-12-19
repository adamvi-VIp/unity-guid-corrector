import os
import re
import logging
import time
from pathlib import Path
from typing import Dict, Optional, Tuple
from tqdm import tqdm

class UnityGUIDCorrector:
    def __init__(self, decompiled_path: str, actual_path: str, project_path: str):
        self.decompiled_path = Path(decompiled_path)
        self.actual_path = Path(actual_path)
        self.project_path = Path(project_path)
        self.guid_mappings: Dict[str, str] = {}
        
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler('guid_correction.log')
            ]
        )
        self.logger = logging.getLogger(__name__)

    def count_files(self, path: Path, pattern: str) -> int:
        """Count files matching a pattern in a directory."""
        return len(list(path.rglob(pattern)))

    def validate_paths(self) -> bool:
        """Validate if all provided paths exist and are accessible."""
        paths = [
            (self.decompiled_path, "Decompiled package path"),
            (self.actual_path, "Actual package path"),
            (self.project_path, "Unity project path")
        ]
        
        print("\n[1/4] Validating paths...")
        time.sleep(0.5)  # Brief pause for readability
        
        for path, description in paths:
            print(f"  Checking {description}...", end=' ')
            if not path.exists():
                print("❌")
                self.logger.error(f"{description} does not exist: {path}")
                return False
            if not any(path.rglob("*.meta")):
                print("❌")
                self.logger.error(f"No .meta files found in {description}: {path}")
                return False
            print("✓")
            time.sleep(0.2)  # Brief pause between checks
        
        print("All paths validated successfully! ✓")
        return True

    def extract_guid_from_meta(self, meta_path: Path) -> Optional[str]:
        """Extract GUID from a meta file."""
        try:
            content = meta_path.read_text()
            guid_match = re.search(r'guid:\s*([a-fA-F0-9]{32})', content)
            return guid_match.group(1).lower() if guid_match else None
        except Exception as e:
            self.logger.error(f"Error reading meta file {meta_path}: {e}")
            return None

    def build_guid_mappings(self):
        """Build mappings between decompiled and actual package GUIDs."""
        print("\n[2/4] Building GUID mappings...")
        time.sleep(0.5)
        
        # Count total files for progress bar
        decompiled_meta_files = list(self.decompiled_path.rglob("*.meta"))
        print(f"\nFound {len(decompiled_meta_files)} meta files in decompiled package")
        
        # Print first few decompiled meta files for verification
        print("\nSample decompiled meta files:")
        for meta in list(decompiled_meta_files)[:5]:
            print(f"  - {meta.relative_to(self.decompiled_path)}")
        
        # Print first few actual package meta files for verification
        print("\nSample actual package meta files:")
        actual_meta_files = list(self.actual_path.rglob("*.meta"))[:5]
        for meta in actual_meta_files:
            print(f"  - {meta.relative_to(self.actual_path)}")
        
        with tqdm(total=len(decompiled_meta_files), desc="  Analyzing meta files", 
                 bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} files') as pbar:
            
            for decompiled_meta in decompiled_meta_files:
                try:
                    filename = decompiled_meta.stem
                    
                    # Find corresponding meta file in actual package
                    actual_meta = None
                    for potential_meta in self.actual_path.rglob(f"{filename}.meta"):
                        if potential_meta.exists():
                            actual_meta = potential_meta
                            break
                    
                    if actual_meta:
                        decompiled_guid = self.extract_guid_from_meta(decompiled_meta)
                        actual_guid = self.extract_guid_from_meta(actual_meta)
                        
                        if decompiled_guid and actual_guid:
                            self.guid_mappings[decompiled_guid] = actual_guid
                            self.logger.info(f"Mapped {filename}: {decompiled_guid} -> {actual_guid}")
                    
                except Exception as e:
                    self.logger.error(f"Error processing {decompiled_meta}: {e}")
                
                pbar.update(1)
        
        print(f"Found {len(self.guid_mappings)} GUID mappings! ✓")

    def replace_guids_in_file(self, file_path: Path) -> bool:
        """Replace GUIDs in a single file."""
        try:
            content = file_path.read_text()
            original_content = content
            
            for old_guid, new_guid in self.guid_mappings.items():
                content = content.replace(old_guid, new_guid)
            
            if content != original_content:
                file_path.write_text(content)
                self.logger.info(f"Updated GUIDs in {file_path}")
                return True
                
        except Exception as e:
            self.logger.error(f"Error updating {file_path}: {e}")
            
        return False

    def collect_target_files(self) -> list:
        """Collect all files that need to be processed."""
        print("\n[3/4] Collecting files to process...")
        time.sleep(0.5)
        
        target_files = []
        extensions = ['.meta', '.unity', '.asset', '.prefab', '.mat']
        
        with tqdm(total=len(extensions), desc="  Scanning directories", 
                 bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} extensions') as pbar:
            for ext in extensions:
                files = list(self.project_path.rglob(f"*{ext}"))
                target_files.extend(files)
                pbar.update(1)
        
        print(f"Found {len(target_files)} files to process! ✓")
        return target_files

    def correct_guids(self) -> Tuple[int, int]:
        """Perform GUID correction across the Unity project."""
        if not self.validate_paths():
            return 0, 0

        self.build_guid_mappings()
        
        if not self.guid_mappings:
            print("\n❌ No GUID mappings found. Ensure the paths are correct.")
            self.logger.error("No GUID mappings found. Ensure the paths are correct.")
            return 0, 0

        target_files = self.collect_target_files()
        files_processed = 0
        files_modified = 0
        
        print("\n[4/4] Correcting GUIDs...")
        time.sleep(0.5)
        
        with tqdm(total=len(target_files), desc="  Updating files",
                 bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} files') as pbar:
            for file_path in target_files:
                files_processed += 1
                if self.replace_guids_in_file(file_path):
                    files_modified += 1
                pbar.update(1)

        print(f"\nOperation completed successfully! ✓")
        print(f"Files processed: {files_processed}")
        print(f"Files modified: {files_modified}")
        
        return files_processed, files_modified

def main():
    print("╔════════════════════════════════════════════╗")
    print("║        Unity GUID Corrector v1.1           ║")
    print("╚════════════════════════════════════════════╝")
    
    decompiled_path = input("\nEnter decompiled package path (usually in Assets/Scripts): ")
    actual_path = input("Enter actual package path (usually in Library/PackageCache): ")
    project_path = input("Enter Unity project Assets path: ")
    
    print("\nStarting GUID correction process...")
    corrector = UnityGUIDCorrector(decompiled_path, actual_path, project_path)
    processed, modified = corrector.correct_guids()
    
    if processed > 0:
        print("\nDetailed log has been saved to 'guid_correction.log'")
        print("\nPress Enter to exit...")
        input()

if __name__ == "__main__":
    main()