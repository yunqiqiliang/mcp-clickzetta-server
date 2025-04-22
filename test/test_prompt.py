import asyncio
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


async def main():
    async with stdio_client(
        StdioServerParameters(command="uv", args=["run", "mcp_clickzetta_server"])
    ) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # List available prompts
            prompts = await session.list_prompts()
            print(prompts)

            resources = await session.list_resources()
            print(resources)

            tools = await session.list_tools()
            print(tools)

            # Example: Call a tool with arguments
            if "show_object_list" in tools:
                result = await session.call_tool("show_object_list", {"object_type": "schemas"})
                print(result)

            # Get the prompt with arguments
            prompt = await session.get_prompt(
                "create_table_prompt",
                {
                    "table_name": "table_created_with_prompt",
                    "columns": "id:integer, name:string, age:integer",
                },
            )
            print(prompt)


asyncio.run(main())