import asyncio

from .server import start_server


def main():
    """Main entry point for the package."""
    asyncio.run(start_server())


if __name__ == "__main__":
    main()
