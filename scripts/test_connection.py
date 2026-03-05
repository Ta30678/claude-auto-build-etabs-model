"""
Test script: Verify ETABS API connection.
Run this with ETABS open to confirm the connection works.
"""
import sys
import os

# Add scripts directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from etabs_connection import attach_to_etabs, get_model

def main():
    print("=" * 60)
    print("ETABS API Connection Test")
    print("=" * 60)

    try:
        print("\n[1] Attempting to connect to ETABS...")
        EtabsObject, SapModel = attach_to_etabs()
        print("    -> Connection successful!")

        print("\n[2] Reading model information...")
        info = get_model(SapModel)
        for key, value in info.items():
            print(f"    {key}: {value}")

        print("\n[3] Reading stories...")
        from etabs_utils import get_stories
        stories = get_stories(SapModel)
        if stories:
            print(f"    Found {len(stories)} stories:")
            for name, data in sorted(stories.items(), key=lambda x: x[1]['elevation']):
                print(f"      {name}: elevation={data['elevation']}, height={data['height']}")
        else:
            print("    No stories defined (blank model)")

        print("\n[4] Reading database table: Story Definitions...")
        from etabs_utils import get_table
        table = get_table(SapModel, "Story Definitions")
        if table:
            print(f"    Columns: {list(table.keys())}")
            print(f"    Records: {len(list(table.values())[0]) if table else 0}")
        else:
            print("    No table data available")

        print("\n" + "=" * 60)
        print("All tests passed! ETABS API connection is working.")
        print("=" * 60)

    except Exception as e:
        print(f"\n[ERROR] {e}")
        print("\nTroubleshooting:")
        print("  1. Make sure ETABS 22 is open and running")
        print("  2. Make sure a model is loaded (even a blank one)")
        print("  3. Try running: RegisterETABS.exe (as admin) from ETABS folder")
        print("  4. Check that ETABSv1.dll exists in the ETABS installation folder")
        sys.exit(1)


if __name__ == "__main__":
    main()
