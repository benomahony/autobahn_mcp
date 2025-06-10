from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel
import httpx
from typing import Any


class Coordinate(BaseModel):
    lat: float
    long: float


class Geometry(BaseModel):
    type: str
    coordinates: list[list[float]]


class Warning(BaseModel):
    identifier: str
    icon: str
    title: str
    subtitle: str
    description: list[str]
    coordinate: Coordinate
    startTimestamp: str | None = None
    delayTimeValue: str | None = None
    abnormalTrafficType: str | None = None
    averageSpeed: str | None = None
    geometry: Geometry | None = None


class WarningsResponse(BaseModel):
    warning: list[Warning]


class Closure(BaseModel):
    identifier: str
    icon: str
    title: str
    subtitle: str
    description: list[str]
    coordinate: Coordinate
    startTimestamp: str | None = None
    delayTimeValue: str | None = None
    geometry: Geometry | None = None


class ClosuresResponse(BaseModel):
    closure: list[Closure]


class ChargingStation(BaseModel):
    identifier: str
    icon: str
    title: str
    subtitle: str
    description: list[str]
    coordinate: Coordinate
    geometry: Geometry | None = None


class ChargingStationsResponse(BaseModel):
    electric_charging_station: list[ChargingStation]


class AutobahnList(BaseModel):
    roads: list[str]


# Create MCP server
mcp = FastMCP("Autobahn Traffic Server")

BASE_URL = "https://verkehr.autobahn.de/o/autobahn"


@mcp.tool()
async def list_autobahns() -> list[str]:
    """List all available German autobahns (highways)."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/")
        response.raise_for_status()
        data = AutobahnList.model_validate(response.json())
        return data.roads


@mcp.tool()
async def get_traffic_warnings(autobahn: str) -> dict[str, Any]:
    """
    Get current traffic warnings for a specific autobahn.

    Args:
        autobahn: The autobahn identifier (e.g., 'A1', 'A7', 'A99')
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/{autobahn}/services/warning")
        response.raise_for_status()
        data = WarningsResponse.model_validate(response.json())

        return {
            "autobahn": autobahn,
            "warnings_count": len(data.warning),
            "warnings": [
                {
                    "title": w.title,
                    "subtitle": w.subtitle,
                    "description": w.description,
                    "location": {"lat": w.coordinate.lat, "long": w.coordinate.long},
                    "traffic_type": w.abnormalTrafficType,
                    "average_speed": f"{w.averageSpeed} km/h"
                    if w.averageSpeed
                    else None,
                    "delay": f"{w.delayTimeValue} minutes"
                    if w.delayTimeValue
                    else None,
                    "timestamp": w.startTimestamp,
                }
                for w in data.warning
            ],
        }


@mcp.tool()
async def get_road_closures(autobahn: str) -> dict[str, Any]:
    """
    Get current road closures for a specific autobahn.

    Args:
        autobahn: The autobahn identifier (e.g., 'A1', 'A7', 'A99')
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/{autobahn}/services/closure")
        response.raise_for_status()
        data = ClosuresResponse.model_validate(response.json())

        return {
            "autobahn": autobahn,
            "closures_count": len(data.closure),
            "closures": [
                {
                    "title": c.title,
                    "subtitle": c.subtitle,
                    "description": c.description,
                    "location": {"lat": c.coordinate.lat, "long": c.coordinate.long},
                    "delay": f"{c.delayTimeValue} minutes"
                    if c.delayTimeValue
                    else None,
                    "timestamp": c.startTimestamp,
                }
                for c in data.closure
            ],
        }


@mcp.tool()
async def get_charging_stations(autobahn: str) -> dict[str, Any]:
    """
    Get electric vehicle charging stations along a specific autobahn.

    Args:
        autobahn: The autobahn identifier (e.g., 'A1', 'A7', 'A99')
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/{autobahn}/services/electric_charging_station"
        )
        response.raise_for_status()
        data = ChargingStationsResponse.model_validate(response.json())

        return {
            "autobahn": autobahn,
            "stations_count": len(data.electric_charging_station),
            "charging_stations": [
                {
                    "title": station.title,
                    "subtitle": station.subtitle,
                    "description": station.description,
                    "location": {
                        "lat": station.coordinate.lat,
                        "long": station.coordinate.long,
                    },
                }
                for station in data.electric_charging_station
            ],
        }


@mcp.tool()
async def get_autobahn_overview(autobahn: str) -> dict[str, Any]:
    """
    Get a complete overview of an autobahn including warnings, closures, and charging stations.

    Args:
        autobahn: The autobahn identifier (e.g., 'A1', 'A7', 'A99')
    """
    warnings = await get_traffic_warnings(autobahn)
    closures = await get_road_closures(autobahn)
    charging = await get_charging_stations(autobahn)

    return {
        "autobahn": autobahn,
        "summary": {
            "warnings": warnings["warnings_count"],
            "closures": closures["closures_count"],
            "charging_stations": charging["stations_count"],
        },
        "warnings": warnings["warnings"],
        "closures": closures["closures"],
        "charging_stations": charging["charging_stations"],
    }


if __name__ == "__main__":
    mcp.run()
