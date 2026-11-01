
from modules.airport_lookup import search_airport

for code in ["DEL", "BOM", "LHR"]:
    print(f"\nSearching airport: {code}")

    result = search_airport(code)

    if result.empty:
        print("Airport not found")
    else:
        print(result.to_string(index=False))
