"""
Compatibility patch for undetected-chromedriver to fix Version object issues.

This module applies runtime patches to fix compatibility issues with the packaging 
library's Version object that no longer has .version and .vstring attributes.

BACKGROUND:
The packaging library changed its Version object implementation, removing the
'version' and 'vstring' attributes that older code (like undetected-chromedriver)
was expecting. This causes AttributeError exceptions when trying to access these
attributes.

ISSUES FIXED:
1. AttributeError: 'Version' object has no attribute 'version'
   - Fixed by using release.release[0] instead of release.version[0]
2. AttributeError: 'Version' object has no attribute 'vstring'  
   - Fixed by using str(self.version_full) instead of self.version_full.vstring

APPROACH:
Instead of modifying the installed package in .venv (which gets lost on reinstalls),
this module applies runtime monkey patches to the problematic methods before they
are used. This is a clean, maintainable solution that doesn't require direct
modification of third-party packages.

USAGE:
Simply import this module before importing undetected_chromedriver:
    from . import chromedriver_patch  # patches are applied automatically
    import undetected_chromedriver as uc
"""

import sys
import types
from packaging.version import Version


def patch_undetected_chromedriver():
    """Apply compatibility patches to undetected_chromedriver"""
    
    try:
        import undetected_chromedriver.patcher as patcher
        
        # Store original methods
        original_auto = patcher.Patcher.auto
        original_fetch_package = patcher.Patcher.fetch_package
        
        def patched_auto(self):
            """Patched auto method that handles Version object properly"""
            if self.executable_path:
                self.executable_path = str(self.executable_path)
            
            # Fix for Version object - use release attribute instead of version
            release = self.fetch_release_number()
            if hasattr(release, 'release'):
                self.version_main = release.release[0]  # Fixed: was release.version[0]
            else:
                # Fallback for older packaging versions
                self.version_main = int(str(release).split('.')[0])
            
            self.version_full = release
            self.unzip_package(self.fetch_package())
            return self.patch()
        
        def patched_fetch_package(self):
            """Patched fetch_package method that handles Version string properly"""
            import os
            from urllib.request import urlretrieve
            
            zip_name = f"chromedriver_{self.platform_name}.zip"
            
            if self.is_old_chromedriver:
                # Fix for Version object - use str() instead of .vstring
                download_url = "%s/%s/%s" % (self.url_repo, str(self.version_full), zip_name)
            else:
                zip_name = zip_name.replace("_", "-", 1)
                download_url = "https://storage.googleapis.com/chrome-for-testing-public/%s/%s/%s"
                # Fix for Version object - use str() instead of .vstring
                download_url %= (str(self.version_full), self.platform_name, zip_name)

            # Use the logger from the original patcher if available
            if hasattr(self, 'logger'):
                self.logger.debug("downloading from %s" % download_url)
            else:
                print(f"Debug: downloading from {download_url}")
            return urlretrieve(download_url)[0]
        
        # Apply patches
        patcher.Patcher.auto = patched_auto
        patcher.Patcher.fetch_package = patched_fetch_package
        
        print("✓ Applied undetected-chromedriver compatibility patches")
        return True
        
    except ImportError:
        print("Warning: undetected-chromedriver not installed, skipping patches")
        return False
    except Exception as e:
        print(f"Warning: Failed to apply chromedriver patches: {e}")
        return False


def ensure_chromedriver_compatibility():
    """Ensure undetected-chromedriver is compatible with current packaging library"""
    
    # Check if we need to apply patches
    try:
        from packaging.version import Version
        test_version = Version("100.0.0")
        
        # Test if the old attributes exist
        if hasattr(test_version, 'version') and hasattr(test_version, 'vstring'):
            print("✓ undetected-chromedriver should work without patches")
            return True
        else:
            # The packaging library Version object lacks the expected attributes
            # Apply patches preventively to avoid potential runtime errors
            print("! Packaging library Version object missing expected attributes")
            print("! Applying preventive compatibility patches for undetected-chromedriver")
            return patch_undetected_chromedriver()
            
    except Exception as e:
        print(f"Warning: Could not check chromedriver compatibility: {e}")
        return False


# Apply patches automatically when this module is imported
if __name__ != "__main__":
    ensure_chromedriver_compatibility()