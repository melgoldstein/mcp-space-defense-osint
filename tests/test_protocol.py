import asyncio
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


def test_real_mcp_stdio_round_trip() -> None:
    async def exercise() -> None:
        parameters = StdioServerParameters(command=sys.executable, args=["-m", "src.server"])
        async with stdio_client(parameters) as (reader, writer):
            async with ClientSession(reader, writer) as session:
                await session.initialize()
                response = await session.list_tools()
                assert {tool.name for tool in response.tools} == {
                    "fetch_celestrak_tle",
                    "query_noaa_swpc_kp",
                    "analyze_notam_tfr",
                }
                result = await session.call_tool("analyze_notam_tfr", {"notice": "2825N08036W010"})
                assert not result.isError

    asyncio.run(exercise())
