import sys
from pathlib import Path

# Ensure root directory is on the python path
sys.path.append(str(Path(__file__).resolve().parent))

from config.settings import settings

def test_configuration():
    print("\n" + "=" * 50)
    print("      STEP 1.2 CONFIGURATION TEST HARNESS     ")
    print("=" * 50)
    
    # 1. Test Base Settings
    print(f"[+] Data Directory Path : {settings.DATA_DIR}")
    print(f"[+] Current Log Level   : {settings.LOG_LEVEL}")
    print(f"[+] Debug Mode          : {settings.DEBUG}")
    
    # 2. Test Zone Config Parsing
    try:
        zones_data = settings.load_zone_config()
        print("[+] successfully loaded 'config/zones.yaml'")
        
        bidding_zones = zones_data.get("bidding_zones", {})
        print(f"[+] Loaded Bidding Zones: {list(bidding_zones.keys())}")
        
        # Verify specific bidding zone details
        de_lu = bidding_zones.get("DE_LU")
        assert de_lu["eic"] == "10Y1001A1001A82H", "DE_LU EIC code mismatch!"
        print(f"    - DE_LU EIC Code    : {de_lu['eic']}")
        print(f"    - DE_LU Timezone    : {de_lu['timezone']}")
        
        doc_types = zones_data.get("document_types", {})
        print(f"[+] Loaded Document Types: {list(doc_types.keys())}")
        
        print("\n✅ ALL CONFIGURATION CHECKS PASSED SUCCESSFULLY!")
        
    except Exception as e:
        print(f"\n❌ CONFIGURATION TEST FAILED: {str(e)}")

if __name__ == "__main__":
    test_configuration()