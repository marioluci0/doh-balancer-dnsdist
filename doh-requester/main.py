from fastapi import HTTPException
from tqdm.asyncio import tqdm
import requests
import asyncio
import aiohttp
import pandas as pd

URL = "https://cdn.jsdelivr.net/gh/hagezi/dns-blocklists@latest/domains/tif.txt"

def get_domains_tif():
    try:
        response = requests.get(URL, timeout=30)
        response.raise_for_status() # raises exception if nots 200
        lines = response.text.splitlines()
        domains = [l.strip() for l in lines if l and not l.startswith("#")]
        print(f"Loaded {len(domains):,} domains")
        return domains
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Error downloading blocklist: {e}")
    
def get_domains_majestic():
    return pd.read_csv("https://downloads.majestic.com/majestic_million.csv", usecols=["Domain"])["Domain"].tolist()

async def request_domain(session, domain):
    doh_url = f"http://localhost:8000/resolve?url={domain}"
    try:
        async with session.get(doh_url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
            return await resp.text() if resp.status == 200 else None
    except Exception as e:
        return None # mutting errors

async def bounded_request(domain, session, semaphore):
    async with semaphore:
        return await request_domain(session, domain)

async def requesting_full_gather(max_concurrent=450):
    # domains = get_domains_tif()
    domains = get_domains_majestic()
    domains = domains[:100000]

    connector = aiohttp.TCPConnector(
        limit=max_concurrent,
        limit_per_host=10,
        ttl_dns_cache=300,
        use_dns_cache=True
    )
    semaphore = asyncio.Semaphore(max_concurrent)

    async with aiohttp.ClientSession(connector=connector) as session:
            
        tasks = [bounded_request(domain, session, semaphore) for domain in domains]

        print(f"Starting parallel processing...")
        results = await tqdm.gather(*tasks, desc="Processing", total=len(domains))

        successful = sum(1 for r in results if isinstance(r, str) and r)
        print(f"Completed {successful:,} successful requests out of {len(domains):,}")

if __name__ == "__main__":
    asyncio.run(requesting_full_gather())