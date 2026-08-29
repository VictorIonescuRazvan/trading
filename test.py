import asyncio
import base64
from datetime import datetime, timedelta
from dataprovider.dataprovider import Dataprovider


async def test_dataprovider():
    """Test Dataprovider class by fetching AAPL data from the whole of yesterday."""
    
    # Calculate yesterday's date range (start and end of day)
    today = datetime.now()
    yesterday_start = today.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)
    yesterday_end = yesterday_start.replace(hour=23, minute=59, second=59)
    
    # Twelve Data API endpoint
    config = {
        "endpoint": "https://api.twelvedata.com/time_series",
        "api_key_b64": api_key_b64,
    }
    
    # Stock symbol
    symbol = "AAPL"
    
    # Use demo API key (base64 encoded)
    # In production, use your own API key from config
    demo_api_key = "demo"
    api_key_b64 = base64.b64encode(demo_api_key.encode()).decode()
    
    print(f"Testing Dataprovider with {symbol} data from {yesterday_start.date()}")
    print(f"Date range: {yesterday_start} to {yesterday_end}")
    print(f"Endpoint: {config['endpoint']}")
    print("-" * 60)
    
    # Create Dataprovider instance (fetches data asynchronously on init)
    dataprovider = Dataprovider(
        symbol=symbol,
        start_date=yesterday_start,
        end_date=yesterday_end,
        config=config,
    )
    
    # Wait a bit for async fetch to complete
    await asyncio.sleep(2)
    
    # Get results
    data = dataprovider.result()
    error = dataprovider.response()
    
    if error:
        print(f"Error occurred: {error}")
        return False
    
    if data:
        print(f"Successfully fetched {len(data)} data points")
        print("\nData by datetime:")
        for datetime_key, ohlcv in sorted(data.items(), reverse=True):
            print(f"  {datetime_key}:")
            print(f"    Open:   {ohlcv.get('open', 'N/A')}")
            print(f"    High:   {ohlcv.get('high', 'N/A')}")
            print(f"    Low:    {ohlcv.get('low', 'N/A')}")
            print(f"    Close:  {ohlcv.get('close', 'N/A')}")
            print(f"    Volume: {ohlcv.get('volume', 'N/A')}")
        return True
    else:
        print("No data retrieved")
        return False


if __name__ == "__main__":
    success = asyncio.run(test_dataprovider())
    exit(0 if success else 1)
