import asyncio
import base64
from typing import Optional, Dict, Any
import aiohttp
from datetime import datetime


class Dataprovider:
    """
    Dataprovider object that fetches time series data from Twelve Data API.
    
    Designed for the Twelve Data time_series endpoint which returns:
    {
        "meta": { ... metadata ... },
        "values": [ { "datetime": ..., "open": ..., "high": ..., "low": ..., "close": ..., "volume": ... }, ... ],
        "status": "ok"
    }
    
    Args:
        time_interval (int): Time interval in minutes between requests
        endpoint (str): Twelve Data API endpoint URL (e.g., https://api.twelvedata.com/time_series)
        api_key_b64 (str): Base64 encoded API key
    """
    
    def __init__(self, symbol: str, start_date: datetime, end_date: datetime, config: Dict[str, Any]):
        self.time_interval = int(config.get("time_interval", 1))
        if self.time_interval <= 0:
            raise ValueError("time_interval must be greater than zero")
        self.symbol = symbol
        self.start_date = start_date
        self.end_date = end_date
        requested_points = (end_date - start_date).total_seconds() / (self.time_interval * 60)
        # The public API limits each request to fewer than 5,000 data points.
        if requested_points >= 5000:
            raise ValueError("requested date range must contain fewer than 5,000 data points")
        self.endpoint = str(config.get("endpoint", ""))
        self.api_key = self._decode_api_key(str(config.get("api_key_b64", "")))
        self._data: Optional[Dict[str, Any]] = None  # Dictionary keyed by datetime strings
        self._response_error: Optional[str] = None
        
        self._fetch_task = asyncio.create_task(self._fetch_data())
    
    @staticmethod
    def _format_datetime(dt: datetime) -> str:
        return dt.strftime("%Y-%m-%dT%H:%M:%S")

    @staticmethod
    def _decode_api_key(api_key_b64: str) -> str:
        """Decode base64 encoded API key."""
        try:
            return base64.b64decode(api_key_b64).decode('utf-8').strip()
        except Exception as e:
            raise ValueError(f"Failed to decode API key: {e}")
    
    async def _fetch_data(self) -> None:
        """Fetch data from the Twelve Data API endpoint asynchronously."""
        try:
            async with aiohttp.ClientSession() as session:
                params = {
                    "apikey": self.api_key, 
                    "symbol": self.symbol, 
                    "start_date": self._format_datetime(self.start_date), 
                    "end_date": self._format_datetime(self.end_date), 
                    "interval": f"{self.time_interval}min", 
                    "outputsize": 5000
                }
                print(params)
                async with session.get(self.endpoint, params=params, timeout=30) as response:
                    if response.status == 200:
                        data = await response.json()
                        # Transform Twelve Data response to dictionary keyed by datetime
                        self._data = self._process_twelve_data_response(data)
                    else:
                        error_body = await response.text()
                        self._response_error = f"Status: {response.status}\nHeaders: {dict(response.headers)}\nBody: {error_body}"
        except asyncio.TimeoutError:
            self._response_error = "Request timeout"
        except Exception as e:
            self._response_error = f"Error: {str(e)}"

    async def wait(self) -> None:
        await self._fetch_task
    
    @staticmethod
    def _process_twelve_data_response(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process Twelve Data API response into a dictionary keyed by datetime.
        
        Expected Twelve Data format:
        {
            "meta": { "symbol": "AAPL", "interval": "1min", ... },
            "values": [
                { "datetime": "2021-09-16 15:59:00", "open": "...", "high": "...", "low": "...", "close": "...", "volume": "..." },
                ...
            ],
            "status": "ok"
        }
        
        Args:
            data: Raw response from Twelve Data API
            
        Returns:
            Dictionary with datetime strings as keys and OHLCV data as values
        """
        if not isinstance(data, dict):
            raise ValueError("response must be a JSON object")
        print(data.get('meta', []))
        # Extract values array from Twelve Data response
        values = data.get('values', [])
        if not isinstance(values, list):
            raise ValueError("response 'values' must be a list")

        result = {}
        for item in values:
            if not isinstance(item, dict):
                raise ValueError("each value must be an object")
            datetime_key = item.get('datetime')
            if not datetime_key:
                raise ValueError("each value must contain 'datetime'")
            result[str(datetime_key)] = item

        return result
    
    def result(self) -> Optional[Dict[str, Any]]:
        """
        Get the fetched time series data as a dictionary keyed by datetime.
        
        Returns:
            Dictionary with datetime strings as keys and OHLCV data as values,
            or None if fetch failed
        """
        return self._data
    
    def response(self) -> Optional[str]:
        """
        Get error information (headers + body) from failed request.
        
        Returns:
            Error details as string, or None if no error occurred
        """
        return self._response_error
