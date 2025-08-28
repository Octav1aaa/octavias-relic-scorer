import enka
import asyncio

async def main():
    # Create Honkai Star Rail client (English language by default)
    async with enka.HSRClient() as client:
        uid = int(input("Please enter HSR player UID: "))
        user = await client.fetch_showcase(uid)

        print(f"Player: {user.player.nickname}, Level: {user.player.level}")
        for char in user.characters:
            print(f"Character: {char.name}, Level: {char.level}")
            print("Relics:")
            for relic in char.relics:
                print(f"  Set name: {relic.set_name}")
                print(f"  Main stat: {relic.main_stat.name} - {relic.main_stat.value}")
                for sub_stat in relic.sub_stats:
                    print(f"    Substat: {sub_stat.name} - {sub_stat.value}")

if __name__ == "__main__":
    asyncio.run(main())
