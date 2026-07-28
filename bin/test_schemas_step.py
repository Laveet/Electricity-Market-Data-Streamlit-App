import sys
from pathlib import Path
from datetime import datetime

sys.path.append(str(Path(__file__).resolve().parent))

from src.energy_data_engine.models.schemas import (
    DayAheadPriceRecord,
    IntradayPriceRecord,
    GenerationRecord
)

def test_pydantic_schemas():
    print("\n" + "=" * 50)
    print("      STEP 2 SCHEMAS & VALIDATION TEST HARNESS     ")
    print("=" * 50 + "\n")

    # 1. Test UTC Timestamp Enforcement & Negative Price Validation
    da_record = DayAheadPriceRecord(
        timestamp="2026-03-29T02:00:00+02:00",  # DST local timestamp
        bidding_zone="de_lu",
        price_eur_mwh=-15.50  # Valid negative price event
    )
    assert da_record.timestamp.tzname() == "UTC", "Timestamp was not coerced to UTC!"
    assert da_record.bidding_zone == "DE_LU", "Bidding zone was not capitalized!"
    print(f"[+] Day-Ahead UTC Timestamp : {da_record.timestamp}")
    print(f"[+] Bidding Zone Normalized : {da_record.bidding_zone}")
    print(f"[+] Negative Price Handled : {da_record.price_eur_mwh} EUR/MWh")

    # 2. Test Missing Volume Parsing in Intraday
    id_record = IntradayPriceRecord(
        timestamp=datetime.now(),
        bidding_zone="FR",
        vwap_eur_mwh=65.20,
        volume_mw="nan"  # NaN string input from ENTSO-E parser
    )
    assert id_record.volume_mw == 0.0, "Missing NaN volume was not parsed to 0.0!"
    print(f"[+] Intraday Volume NaN fallback : {id_record.volume_mw} MW")

    # 3. Test Generation Stack Helper Property
    gen_record = GenerationRecord(
        timestamp=datetime.now(),
        bidding_zone="NL",
        solar_mw=1200.0,
        wind_onshore_mw=800.0,
        wind_offshore_mw=500.0
    )
    assert gen_record.total_renewable_mw == 2500.0
    print(f"[+] Calculated Renewable Total: {gen_record.total_renewable_mw} MW")

    print("\n✅ ALL SCHEMAS AND DATA VALIDATORS VERIFIED SUCCESSFULLY!")

if __name__ == "__main__":
    test_pydantic_schemas()